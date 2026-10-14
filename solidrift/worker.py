"""Single isolated Blender worker. Entry point is intentionally not user code."""
import json
from pathlib import Path
import sys
import traceback

# --python executes a file rather than a module; import this distribution only.
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bpy
from solidrift.engine import analyze, Budget
from solidrift.io import read_input, atomic_json
from solidrift.native import union

def main():
    args=sys.argv[sys.argv.index('--')+1:]
    request_path=Path(args[0]);request=json.loads(request_path.read_text())
    out=request_path.parent
    budget=Budget(request['max_queries'],request['max_seconds'])
    pair=[]
    for name in ('A.obj','B.obj'):
        _,mesh,_=read_input(out/'originals'/name);mesh['name']=name;pair.append(mesh)
    identity={'backend':bpy.app.version_string,'build_hash':bpy.app.build_hash.decode(),
              'solvers':['FLOAT','MANIFOLD']}
    latest={}
    def publish(report):
        latest.clear();latest.update(report)
        report['sources']=request['sources'];report['budget']=budget.evidence()
        atomic_json(out/'report.json',report)
        for name in ('baseline','reduction','repair'):
            if report.get(name) is not None:
                atomic_json(out/(name+'.json'),report[name])
        print('SOLIDRIFT_STAGE',report['status'],budget.queries,flush=True)
    try:
        analyze(pair,union,identity,budget,publish)
    except Exception as error:
        latest.update(schema_version=1,status='error',reason=f'{type(error).__name__}: {error}',
                      sources=request['sources'],budget=budget.evidence())
        atomic_json(out/'report.json',latest)
        traceback.print_exc()
        raise

if __name__=='__main__':main()
