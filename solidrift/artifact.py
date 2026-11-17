"""Checked, source-bound reversible intervention for one recorded failure family."""
import copy
import hashlib
import json
import os
import stat
from pathlib import Path
import tempfile
import sys

from .io import InputError, MAX_REPORT_BYTES, f32, parse_report, read_input, write_obj
from .gate import check_exact
from .verify import verify


def hash_bytes(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def geometry(mesh):return {'vertices':mesh['vertices'],'faces':mesh['faces']}
def geometry_hash(mesh):return hash_bytes(canonical(geometry(mesh)))


def capture(path, limit=MAX_REPORT_BYTES):
    # Preserve the existing symlink-following policy; validate the opened
    # descriptor itself and avoid blocking on special files such as FIFOs.
    if not hasattr(os,'O_NONBLOCK'):raise InputError('nonblocking input admission is unavailable')
    fd=os.open(path,os.O_RDONLY | os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):raise InputError('input must be a regular file')
        if info.st_size>limit:raise InputError('input exceeds bounded size')
        chunks=[];total=0
        while True:
            part=os.read(fd,min(65536,limit-total+1))
            if not part:break
            total+=len(part)
            if total>limit:raise InputError('input exceeds bounded size')
            chunks.append(part)
        return b''.join(chunks)
    finally:os.close(fd)


def source_identity():
    root=Path(__file__).resolve().parent
    return {name:hash_bytes((root/name).read_bytes()) for name in ('__init__.py','cli.py','artifact.py','engine.py','guard.py','gate.py','io.py','native.py','numeric.py','reducer.py','surface.py','verify.py','replay_worker.py')}


def from_report(path):
    path=Path(path);raw=capture(path);report=parse_report(raw)
    checked=verify(path,report=report)
    if checked['status']!='repaired':raise InputError('report does not contain a completed accepted intervention')
    accepted=report['repair']['accepted'];original=list(report['baseline']['inputs'].values());after=accepted['full_repaired']
    body={'schema':'solidrift-repair-v1','report_sha256':hash_bytes(raw),
          'original_source_sha256':[item['sha256'] for item in report['sources']],
          'before_geometry_sha256':[geometry_hash(x) for x in original],
          'after_geometry_sha256':[geometry_hash(x) for x in after],
          'backend':{'version':report['baseline']['backend'],'build_hash':report['baseline']['build_hash']},
          'engine_sha256':source_identity(), 'failure_family':'FLOAT union missing second operand volume',
          'side':accepted['intervention']['side'],'changes':accepted['patch']}
    return {**body,'sha256':hash_bytes(canonical(body))}


def check_artifact(report_path, artifact_path):
    try:artifact=json.loads(capture(artifact_path, 1_000_000))
    except (json.JSONDecodeError,UnicodeError) as exc:raise InputError('invalid intervention artifact') from exc
    if canonical(artifact)!=canonical(from_report(report_path)):raise InputError('intervention differs from checked report or current code')
    return artifact


def transform(artifact, meshes, undo=False):
    if len(meshes)!=2:raise InputError('exactly two operands required')
    expected=artifact['after_geometry_sha256'] if undo else artifact['before_geometry_sha256']
    if [geometry_hash(m) for m in meshes]!=expected:raise InputError('operand geometry or topology differs from intervention precondition')
    result=copy.deepcopy(meshes);side=artifact['side']
    if type(side)!=int or side not in (0,1):raise InputError('invalid intervention side')
    seen=set()
    for change in artifact['changes']:
        i=change['vertex'];before=change['after' if undo else 'before'];after=change['before' if undo else 'after']
        if type(i)!=int or i in seen or not 0<=i<len(result[side]['vertices']):raise InputError('invalid intervention vertex')
        seen.add(i)
        if result[side]['vertices'][i]!=before:raise InputError('intervention coordinate precondition differs')
        if not isinstance(after,list) or len(after)!=3 or any(f32(x)!=x for x in after):raise InputError('intervention coordinates are not binary32')
        result[side]['vertices'][i]=list(after)
    target=artifact['before_geometry_sha256'] if undo else artifact['after_geometry_sha256']
    if [geometry_hash(m) for m in result]!=target:raise InputError('intervention result geometry differs')
    if not all(check_exact(m['vertices'],m['faces'])['valid'] for m in result):raise InputError('intervention output failed exact input guard')
    return result


def operands(paths):
    result=[]
    for index,path in enumerate(paths):
        _,mesh,_=read_input(path);mesh['name']=('A.obj','B.obj')[index];result.append(mesh)
    return result


def publish_file(path,data):
    path=Path(path);fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.pending',dir=path.parent)
    published=False
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.link(tmp,path);published=True
    finally:
        try:os.unlink(tmp)
        except OSError as exc:
            if not published:raise
            print(f'Solidrift: completed output retained; staging cleanup failed: {exc}',file=sys.stderr)


def write_pair(out, pair):
    for i,mesh in enumerate(pair):write_obj(Path(out)/('A.obj','B.obj')[i],mesh)


def result_marker(out, value):
    publish_file(Path(out)/'result.json',(json.dumps(value,indent=2,allow_nan=False)+'\n').encode())
