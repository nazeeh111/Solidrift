"""Trusted Blender-only full-input re-query of a checked intervention."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import bpy
from solidrift.artifact import check_artifact, geometry_hash, operands, transform
from solidrift.engine import Budget, metrics, quality
from solidrift.io import InputError
from solidrift.native import union
from solidrift.reducer import failure_signature


def main():
    request=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
    root=Path(request['out']);artifact=check_artifact(request['report'],request['artifact'])
    actual={'version':bpy.app.version_string,'build_hash':bpy.app.build_hash.decode()}
    if actual!=artifact['backend']:raise InputError('Blender runtime identity differs from recorded intervention')
    original=operands([root/'original-A.obj',root/'original-B.obj']);repaired=operands([root/'A.obj',root/'B.obj'])
    expected=transform(artifact,original)
    if [geometry_hash(x) for x in repaired]!=[geometry_hash(x) for x in expected]:raise InputError('reopened repaired geometry differs')
    budget=Budget(max_queries=16,max_seconds=60)
    before=budget.evaluate(original,'FLOAT',union,'replay')
    prior=failure_signature([metrics(m) for m in original],before)
    if not prior['matches']:raise InputError('recorded failure family did not reproduce')
    span=max(max(v[k] for m in original for v in m['vertices'])-min(v[k] for m in original for v in m['vertices']) for k in range(3))
    accepted,check=quality(repaired,union,budget,span)
    if not accepted:raise InputError('repaired full geometry did not meet comparator checks: '+check['reason'])
    undo=transform(artifact,repaired,undo=True)
    if [geometry_hash(x) for x in undo]!=artifact['before_geometry_sha256']:raise InputError('undo geometry differs')
    undone=budget.evaluate(undo,'FLOAT',union,'replay')
    restored=failure_signature([metrics(m) for m in undo],undone)
    if not restored['matches']:raise InputError('undo did not reproduce scoped failure family')
    result={'status':'native_checks_passed','artifact_sha256':artifact['sha256'],
            'report_sha256':artifact['report_sha256'],'before_geometry_sha256':artifact['before_geometry_sha256'],
            'after_geometry_sha256':artifact['after_geometry_sha256'],'runtime':actual,'native_queries':budget.queries,
            'original_failure':prior,'repaired_surface':check['surface_correspondence'],
            'repaired_float_volume':check['output']['volume'],'repaired_manifold_volume':check['reference']['volume'],
            'undo_failure':restored,'scope':'Fresh full-input FLOAT/MANIFOLD comparison and undo; not a proof of true union or general repair.'}
    with (root/'native-check.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print('SOLIDRIFT_NATIVE_REPLAY',json.dumps({'status':result['status'],'queries':budget.queries}),flush=True)

if __name__=='__main__':main()
