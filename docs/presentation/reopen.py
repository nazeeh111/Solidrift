"""Reopen the synthetic/public record using exact pinned current-main source."""
from pathlib import Path
import hashlib,json,sys
P=Path(__file__).resolve().parent
m=json.loads((P/'bundle-manifest.json').read_text())
for f in m['files']:
 b=(P/f['path']).read_bytes()
 if len(b)!=f['bytes'] or hashlib.sha256(b).hexdigest()!=f['sha256']:raise SystemExit('Bundle bytes differ: '+f['path'])
sys.dont_write_bytecode=True;sys.path.insert(0,str(P/'reader-source'))
from solidrift.verify import verify
out=verify(P/'case/report.json');out['bundle_files_verified']=len(m['files']);out['pinned_source']='66bf422806891121d1fed7e5f08e7fa8aa89d3df';print(json.dumps(out,indent=2))
