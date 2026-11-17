"""Offline CLI; uses only Python's standard library and an explicit Blender path."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from . import __version__
from .io import InputError, atomic_json, json_bytes, load_report, read_input, write_obj

FIXTURES = Path(__file__).resolve().parent/'fixtures'

def stop_process(process):
    if process.poll() is not None:return
    try:
        if os.name=='posix':os.killpg(process.pid,signal.SIGTERM)
        else:process.terminate()
    except ProcessLookupError:
        process.wait();return
    try:process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            if os.name=='posix':os.killpg(process.pid,signal.SIGKILL)
            else:process.kill()
        except ProcessLookupError:pass
        process.wait(timeout=3)

def failed_report(out,sources,status,reason):
    path=out/'report.json'
    report=load_report(path) if path.exists() else {'schema_version':1,'baseline':None,'reduction':None,'repair':None}
    if report.get('reason'):report['worker_reason']=report['reason']
    report.update(status=status,reason=reason,sources=sources)
    # A partial stored accepted result must not survive a failed/cancelled run
    # as an unqualified top-level success.
    atomic_json(path,report)

def exports(out,report):
    target=out/'meshes';target.mkdir()
    manifest={}
    def save(name,mesh):
        if mesh and mesh.get('vertices') and mesh.get('faces'):
            write_obj(target/name,mesh);manifest[name]='meshes/'+name
    baseline=report.get('baseline')
    if baseline:
        for i,m in enumerate(baseline['inputs'].values()):save('original-'+('A','B')[i]+'.obj',m)
        for name,m in baseline['outputs'].items():save('baseline-'+name+'.obj',m)
    reduction=report.get('reduction')
    if reduction:
        for i,m in enumerate(reduction['operands']):save('witness-'+('A','B')[i]+'.obj',m)
        for name,m in reduction['final_outputs'].items():save('witness-'+name+'.obj',m)
    repair=report.get('repair')
    if repair and repair.get('accepted'):
        a=repair['accepted']
        for stage in ('full_repaired','witness_repaired','undo_inputs'):
            for i,m in enumerate(a[stage]):save(stage+'-'+('A','B')[i]+'.obj',m)
        for stage in ('full_check','witness_check'):
            save(stage+'-FLOAT.obj',a[stage]['output_geometry'])
            save(stage+'-MANIFOLD.obj',a[stage]['reference_geometry'])
        atomic_json(out/'patch.json',{'schema_version':1,'side':a['intervention']['side'],
                    'changes':a['patch'],'coordinate_space':'native binary32 imported coordinates',
                    'undo':'Restore stored before values only when every current coordinate equals its stored after value.'})
    report['exports']=manifest;atomic_json(out/'report.json',report)

def run(args):
    blender=Path(args.blender).expanduser().resolve()
    if not blender.is_file() or not os.access(blender,os.X_OK):
        raise InputError('--blender must be an executable file')
    if not 16<=args.max_queries<=1500 or not 0<args.max_seconds<=120:
        raise InputError('--max-queries must be 16..1500; --max-seconds must be >0 and <=120')
    inputs=(FIXTURES/'Offset3.obj',FIXTURES/'Offset4.obj') if args.command=='demo' else (args.a,args.b)
    items=[read_input(p) for p in inputs]
    out=Path(args.out).expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise InputError('--out must be a new directory; existing data is never overwritten')
    out.mkdir()
    (out/'originals').mkdir()
    sources=[]
    for i,(data,mesh,source) in enumerate(items):
        name=('A.obj','B.obj')[i]
        with (out/'originals'/name).open('xb') as handle:handle.write(data)
        source['stored_path']='originals/'+name;sources.append(source)
    if args.command=='demo':
        sources[0]['provenance']=sources[1]['provenance']={
            'repository':'https://github.com/elalish/manifold',
            'commit':'761661c15bacb6c8459d682c715de84591d51774',
            'paths':['test/models/Offset3.obj','test/models/Offset4.obj'],
            'license':'Apache-2.0; included in originals/FIXTURE_LICENSE'}
        (out/'originals'/'FIXTURE_LICENSE').write_bytes((FIXTURES/'LICENSE').read_bytes())
    request={'sources':sources,'max_queries':args.max_queries,'max_seconds':max(.1,args.max_seconds-2)}
    atomic_json(out/'request.json',request)
    command=[str(blender),'--background','--factory-startup','--disable-autoexec',
             '--python-exit-code','1','--python',str(Path(__file__).resolve().parent/'worker.py'),
             '--',str(out/'request.json')]
    started=time.monotonic()
    with (out/'worker.log').open('xb') as log:
        try:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=(os.name=='posix'))
        except OSError as error:
            failed_report(out,sources,'error',f'Worker could not start: {error}')
            raise
        try:
            process.wait(timeout=args.max_seconds)
        except subprocess.TimeoutExpired:
            stop_process(process);failed_report(out,sources,'timeout','Worker exceeded requested wall time and was terminated.')
            print(f'Timed out. Preserved originals and partial evidence: {out / "report.json"}',file=sys.stderr)
            return 3
        except KeyboardInterrupt:
            stop_process(process);failed_report(out,sources,'cancelled','User cancelled; worker process group terminated.')
            print(f'Cancelled. Preserved originals: {out}',file=sys.stderr);return 130
    if process.returncode!=0:
        failed_report(out,sources,'error',f'Blender worker exited {process.returncode}; see worker.log and stage evidence.')
        print(f'Analysis failed: {out / "report.json"}',file=sys.stderr);return 2
    report=load_report(out/'report.json')
    report['wall_seconds']=time.monotonic()-started
    report['hard_wall_limit_seconds']=args.max_seconds
    if report.get('status') in ('error','refused','running'):
        print(f'{report.get("status")}: {report.get("reason","incomplete worker")}. Report: {out / "report.json"}',file=sys.stderr)
        return 2
    try:
        exports(out,report)
        view(argparse.Namespace(report=str(out/'report.json'),out=str(out/'report.html')))
    except KeyboardInterrupt:
        failed_report(out,sources,'cancelled','Export cancelled after the native worker completed; originals and partial evidence retained.')
        return 130
    except Exception as error:
        failed_report(out,sources,'error',f'Export failed after native analysis: {type(error).__name__}: {error}')
        raise
    print(json.dumps({'status':report['status'],'report':str(out/'report.json'),
                      'native_queries':report['budget']['native_backend_queries'],
                      'wall_seconds':report['wall_seconds']}))
    return 0

def view(args):
    report=load_report(args.report)
    target=Path(args.out)
    if target.exists() or target.is_symlink():raise InputError('--out must be a new HTML file')
    root=Path(__file__).resolve().parent/'web'
    if not root.is_dir():root=Path(__file__).resolve().parent.parent/'web'
    template=(root/'index.html').read_text()
    # Script JSON and asset content are inertly escaped at closing-script
    # boundaries; arbitrary source names cannot break out into HTML.
    data=json.dumps(report,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=template.replace('__SOLIDRIFT_DATA__',data)
    style=(root/'style.css').read_text();script=(root/'app.js').read_text().replace('</script','<\\/script')
    template=template.replace('<link rel="stylesheet" href="style.css">','<style>'+style+'</style>')
    template=template.replace('<script src="app.js"></script>','<script>'+script+'</script>')
    with target.open('x',encoding='utf-8') as handle:handle.write(template)
    print(str(target.absolute()));return 0

def main(argv=None):
    parser=argparse.ArgumentParser(description='Shrink a real Boolean failure, lift a reversible repair, export the evidence.')
    parser.add_argument('--version',action='version',version=__version__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('analyze','demo'):
        p=sub.add_parser(name)
        if name=='analyze':p.add_argument('a');p.add_argument('b')
        p.add_argument('--blender',required=True);p.add_argument('--out',required=True)
        p.add_argument('--max-queries',type=int,default=1500);p.add_argument('--max-seconds',type=float,default=120)
    p=sub.add_parser('view');p.add_argument('report');p.add_argument('--out',required=True)
    p=sub.add_parser('verify');p.add_argument('report')
    args=parser.parse_args(argv)
    try:
        if args.command=='view':return view(args)
        if args.command=='verify':
            from .verify import verify
            print(json.dumps(verify(args.report)));return 0
        return run(args)
    except (InputError,OSError,ValueError,KeyError,TypeError,IndexError) as error:
        print(f'Solidrift refused: {error}',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
