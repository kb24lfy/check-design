#!/usr/bin/env python3
"""Read/post positioned Figma comments. Stdlib only; never accept tokens in argv."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib import error, request

ALLOWED = {
    "CLEAR 法则": {"不符合"},
    "设计检查清单": {"不符合"},
    "PRD 与 UI 一致性": {"明确不一致", "设计覆盖缺项"},
}


class ApiError(Exception):
    def __init__(self, code, retry_after=None):
        self.code, self.retry_after = code, retry_after


class CredentialMissing(Exception):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def credential():
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token and sys.platform == "darwin":
        # Only this explicitly documented entry; no searching other credentials.
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s",
             "check-design.figma", "-a", "personal-access-token", "-w"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
    if not token:
        raise CredentialMissing()
    return token


class Api:
    def __init__(self, token):
        self.token = token
        self.opener = request.build_opener(NoRedirect())

    def call(self, method, key, body=None):
        payload = json.dumps(body, ensure_ascii=False).encode() if body else None
        req = request.Request(
            "https://api.figma.com/v1/files/" + key + "/comments",
            data=payload, method=method,
            headers={"X-Figma-Token": self.token, "Content-Type": "application/json"},
        )
        try:
            with self.opener.open(req, timeout=30) as response:
                return json.load(response)
        except error.HTTPError as exc:
            wait = exc.headers.get("Retry-After", "")
            raise ApiError(exc.code, int(wait) if wait.isdigit() else None) from None
        except (error.URLError, TimeoutError, OSError, ValueError):
            raise ApiError("transport_or_invalid_response") from None

    def comments(self, key):
        data = self.call("GET", key)
        if not isinstance(data, dict) or not isinstance(data.get("comments"), list):
            raise ApiError("invalid_comment_list")
        if any(not isinstance(c, dict) for c in data["comments"]):
            raise ApiError("invalid_comment_list")
        return data["comments"]


def file_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9]+", value):
        raise ValueError("file_key 必须是已核实的文件或分支 key，不是 URL。")
    return value


def vector(value):
    return (isinstance(value, dict) and set(value) == {"x", "y"}
            and all(type(n) in (int, float) and math.isfinite(n) for n in value.values()))


def validate(issue):
    if not isinstance(issue, dict):
        raise ValueError("问题输入必须为 JSON 对象。")
    file_key(issue.get("file_key"))
    if (not isinstance(issue.get("section"), str)
            or not isinstance(issue.get("status"), str)
            or issue["status"] not in ALLOWED.get(issue["section"], set())):
        raise ValueError("该检查状态不允许发布评论。")
    if not isinstance(issue.get("message"), str) or not issue["message"].strip():
        raise ValueError("评论正文不能为空。")
    meta = issue.get("client_meta")
    frame = (isinstance(meta, dict) and set(meta) == {"node_id", "node_offset"}
             and isinstance(meta["node_id"], str)
             and re.fullmatch(r"\d+:\d+", meta["node_id"])
             and vector(meta["node_offset"]))
    if not vector(meta) and not frame:
        raise ValueError("client_meta 必须为画布坐标 {x,y} 或已核实 Frame 的 {node_id,node_offset:{x,y}}。")
    if frame and any(v < 0 for v in meta["node_offset"].values()):
        raise ValueError("Frame 内定位偏移不能为负数。")
    return issue


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".figma-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def same_position(a, b):
    if vector(a) and vector(b):
        return all(abs(a[k] - b[k]) <= 0.01 for k in ("x", "y"))
    return (isinstance(a, dict) and isinstance(b, dict)
            and bool(a.get("node_id")) and a.get("node_id") == b.get("node_id")
            and vector(a.get("node_offset")) and vector(b.get("node_offset"))
            and same_position(a["node_offset"], b["node_offset"]))


def matches(comment, issue):
    return (not comment.get("parent_id") and comment.get("message") == issue["message"]
            and same_position(comment.get("client_meta"), issue["client_meta"])
            and bool(comment.get("id")))


def result_for(comment, status):
    # The REST response has no documented permalink field; don't invent one.
    return {"status": status, "comment_id": comment["id"],
            "order_id": comment.get("order_id"), "client_meta": comment.get("client_meta")}


def publish(issue, journal_path, api):
    """Single writer per journal. Uncertain attempts are reconciled, never reposted."""
    journal_path = Path(journal_path)
    journal = read_json(journal_path) if journal_path.exists() else {}
    if not isinstance(journal, dict):
        raise ValueError("发布记录格式错误，停止发送。")
    digest = hashlib.sha256(json.dumps(
        [issue["file_key"], issue["message"], issue["client_meta"]],
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    previous = journal.get(digest, {})
    if not isinstance(previous, dict):
        raise ValueError("发布记录格式错误，停止发送。")
    if previous.get("retry_at", 0) > time.time():
        return {"status": "rate_limited", "retry_at": previous["retry_at"]}
    existing = api.comments(issue["file_key"])
    for c in existing:
        if (c.get("id") == previous.get("comment_id") and matches(c, issue)):
            return result_for(c, "already_recorded")
        if not c.get("resolved_at") and matches(c, issue):
            result = result_for(c, "reused")
            journal[digest] = result
            save_json(journal_path, journal)
            return result
    if previous.get("status") in {"attempting", "uncertain", "published", "reused", "recovered"}:
        return {"status": "uncertain", "reason": "此前已有发送记录但未能核实；停止重发，需人工核对。"}
    journal[digest] = {"status": "attempting", "file_key": issue["file_key"],
                       "client_meta": issue["client_meta"]}
    save_json(journal_path, journal)  # Durable before the external mutation.
    try:
        posted = api.call("POST", issue["file_key"],
                          {"message": issue["message"], "client_meta": issue["client_meta"]})
        if not isinstance(posted, dict) or not matches(posted, issue):
            raise ApiError("invalid_post_response")
        if posted.get("file_key") not in (None, issue["file_key"]):
            raise ApiError("unexpected_file")
        result = result_for(posted, "published")
    except ApiError as exc:
        if exc.code == 429:
            result = {"status": "rate_limited", "http_status": 429,
                      "retry_at": time.time() + (exc.retry_after or 60)}
        elif exc.code in (400, 401, 403, 404):
            result = {"status": "rejected", "http_status": exc.code}
        else:
            result = {"status": "uncertain", "reason": "发送结果不明确，未自动重发。"}
            try:
                found = next((c for c in api.comments(issue["file_key"])
                              if matches(c, issue)), None)
                if found:
                    result = result_for(found, "recovered")
            except ApiError:
                pass
    journal[digest] = result
    save_json(journal_path, journal)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--file-key", required=True)
    listing.add_argument("--output", required=True)
    post = commands.add_parser("post")
    post.add_argument("--issue", required=True)
    post.add_argument("--journal", required=True)
    post.add_argument("--publish", action="store_true", help="Omit for local validation only")
    args = parser.parse_args()
    try:
        if args.command == "list":
            comments = Api(credential()).comments(file_key(args.file_key))
            save_json(args.output, {"comments": comments})
            result = {"status": "read", "count": len(comments), "output": args.output}
        else:
            issue = validate(read_json(args.issue))
            if not args.publish:
                result = {"status": "dry_run", "section": issue["section"],
                          "finding_status": issue["status"], "file_key": issue["file_key"],
                          "client_meta": issue["client_meta"]}
            else:
                result = publish(issue, args.journal, Api(credential()))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] in {"read", "dry_run", "published", "reused", "recovered", "already_recorded"} else 2
    except CredentialMissing:
        print(json.dumps({"status": "blocked", "reason": "未配置 API 凭据：请通过本地安全配置提供 FIGMA_ACCESS_TOKEN 或指定的 macOS 钥匙串项目，不要在聊天发送 Token。"}, ensure_ascii=False))
    except ApiError as exc:
        print(json.dumps({"status": "blocked", "http_status": exc.code,
                          "retry_after": exc.retry_after}, ensure_ascii=False))
    except (OSError, ValueError, subprocess.SubprocessError):
        # Don't print remote bodies, headers, argv, file contents or credential exceptions.
        print(json.dumps({"status": "blocked", "reason": "检查输入文件、凭据配置及本地读写权限；未完成发布。"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    sys.exit(main())
