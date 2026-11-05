#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
p=root/'standards/manifest.json'
old=json.loads(p.read_text()) if p.exists() else {'version':'1.0.0'}
files=sorted(x for x in (root/'standards').rglob('*') if x.is_file() and x!=p and x.suffix in {'.md','.json','.png'})
manifest={'schema_version':1,'version':old['version'],'source_read_date':'2026-11-05','files':[{'path':x.relative_to(root).as_posix(),'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in files]}
p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Updated manifest:',len(files),'files')
