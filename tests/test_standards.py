import importlib.util,json,tempfile,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('fetch',ROOT/'skills/check-design/scripts/fetch_standards.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
SOURCE=m.config_read(ROOT/'skills/check-design/standards-source.json')
SHA='a'*40
class Reader:
 def __init__(self):self.urls=[]
 def __call__(self,url):
  self.urls.append(url)
  if '/commits/' in url:return json.dumps({'sha':SHA}).encode()
  assert url.endswith('?ref='+SHA),url
  path=url.split('/contents/')[1].split('?')[0]
  return (ROOT/path).read_bytes()
class StandardsTests(unittest.TestCase):
 def test_complete_pin_and_resume(self):
  with tempfile.TemporaryDirectory() as t:
   reader=Reader();out=Path(t)/'run';lock,status=m.fetch(SOURCE,out,reader)
   self.assertEqual(status,'downloaded');self.assertEqual(lock['commit'],SHA)
   self.assertEqual(sum('/commits/' in u for u in reader.urls),1)
   self.assertEqual(len(reader.urls),10)
   def offline(url):raise AssertionError('resume must not use network')
   self.assertEqual(m.fetch(SOURCE,out,offline)[1],'reused_this_review')
 def test_new_review_queries_again(self):
  with tempfile.TemporaryDirectory() as t:
   r=Reader();m.fetch(SOURCE,Path(t)/'one',r);m.fetch(SOURCE,Path(t)/'two',r)
   self.assertEqual(sum('/commits/' in u for u in r.urls),2)
 def test_tampered_file_blocks_resume(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'run';m.fetch(SOURCE,out,Reader());(out/'standards/clear.md').write_text('tampered')
   with self.assertRaises(m.FetchError):m.fetch(SOURCE,out,Reader())
 def test_wrong_source_blocks_resume(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'run';m.fetch(SOURCE,out,Reader())
   with self.assertRaises(m.FetchError):m.fetch(dict(SOURCE,ref='other'),out,Reader())
 def test_network_failure_no_snapshot(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'run'
   def offline(url):raise m.FetchError('offline')
   with self.assertRaises(m.FetchError):m.fetch(SOURCE,out,offline)
   self.assertFalse(out.exists())
 def test_partial_download_no_snapshot(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'run';r=Reader()
   def failing(url):
    if '/visual.md?' in url:raise m.FetchError('offline')
    return r(url)
   with self.assertRaises(m.FetchError):m.fetch(SOURCE,out,failing)
   self.assertFalse(out.exists());self.assertEqual(list(Path(t).iterdir()),[])
 def test_hash_mismatch_no_snapshot(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'run';r=Reader()
   def modified(url):return b'bad' if '/clear.md?' in url else r(url)
   with self.assertRaises(m.FetchError):m.fetch(SOURCE,out,modified)
   self.assertFalse(out.exists())
 def test_path_and_schema_validation(self):
  manifest=json.loads((ROOT/'standards/manifest.json').read_text())
  for bad in ['../secret','standards/../secret.md','standards/program.py','standards//clear.md']:
   data=json.loads(json.dumps(manifest));data['files'][0]['path']=bad
   with self.assertRaises(m.FetchError):m.validate_manifest(data)
  with self.assertRaises(m.FetchError):m.validate_manifest(dict(manifest,schema_version=2))
 def test_manifest_complete(self):
  manifest=json.loads((ROOT/'standards/manifest.json').read_text())
  for item in m.validate_manifest(manifest):self.assertEqual(item['sha256'],hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest())
 def test_four_column_report_contract(self):
  text=(ROOT/'skills/check-design/references/report-template.md').read_text()
  for header in ['| 状态 | 维度 |','| 状态 | 检查项 |']:
   start=0
   while True:
    a=text.find(header,start)
    if a<0:break
    b=text.index('\n```',a)
    for row in text[a:b].splitlines():self.assertEqual(len(row.strip('|').split('|')),4)
    start=b
if __name__=='__main__':unittest.main()
