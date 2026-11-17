"""Bounded triangle OBJ input and immutable report output."""
import hashlib
import json
import math
import os
from pathlib import Path
import struct

MAX_INPUT_BYTES = 1024 * 1024
MAX_REPORT_BYTES = 10 * 1024 * 1024
MAX_INPUT_FACES = 256
MAX_INPUT_VERTICES = 256

class InputError(ValueError):
    pass

def f32(x):
    try:
        y = struct.unpack('<f', struct.pack('<f', x))[0]
    except (OverflowError, struct.error):
        raise InputError('coordinate overflows binary32') from None
    if not math.isfinite(y):
        raise InputError('coordinates must remain finite in binary32')
    return y

def parse_obj(data, name='operand.obj'):
    if len(data) > MAX_INPUT_BYTES:
        raise InputError('OBJ exceeds 1 MiB input limit')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        raise InputError('OBJ must be UTF-8 text') from None
    vertices, faces = [], []
    # These records are metadata only. Materials are never opened or executed.
    metadata = {'o', 'g', 's', 'usemtl', 'mtllib'}
    normals, texcoords = 0, 0
    for number, line in enumerate(text.splitlines(), 1):
        if len(line) > 8192:
            raise InputError(f'line {number}: exceeds 8192 characters')
        row = line.split('#', 1)[0].split()
        if not row:
            continue
        kind = row[0]
        try:
            if kind == 'v':
                if len(row) != 4:
                    raise InputError('vertices require exactly x y z; weights/colors unsupported')
                point = [float(x) for x in row[1:]]
                if not all(math.isfinite(x) and abs(x) <= 1e6 for x in point):
                    raise InputError('coordinate must be finite and within +/-1,000,000')
                vertices.append(point)
                if len(vertices) > MAX_INPUT_VERTICES:
                    raise InputError('at most 256 vertices per operand')
            elif kind == 'vn':
                if len(row) != 4 or not all(math.isfinite(float(x)) for x in row[1:]):
                    raise InputError('normal requires three finite coordinates')
                normals += 1
            elif kind == 'vt':
                if not 2 <= len(row) <= 4 or not all(math.isfinite(float(x)) for x in row[1:]):
                    raise InputError('texture coordinate requires one to three finite coordinates')
                texcoords += 1
            elif kind == 'f':
                if len(row) != 4:
                    raise InputError('only explicitly triangulated faces are supported')
                face = []
                for token in row[1:]:
                    fields = token.split('/')
                    if len(fields) > 3 or not fields[0]:
                        raise InputError('malformed face index')
                    counts = [len(vertices), texcoords, normals]
                    for k, field in enumerate(fields):
                        if not field:
                            if k == 1 and len(fields) == 3 and fields[2]:
                                continue
                            raise InputError('malformed face index')
                        index = int(field)
                        resolved = index - 1 if index > 0 else counts[k] + index
                        if index == 0 or not 0 <= resolved < counts[k]:
                            raise InputError('face index must refer to an already declared record')
                        if k == 0:
                            face.append(resolved)
                if len(set(face)) != 3:
                    raise InputError('face must have three distinct indices')
                faces.append(face)
                if len(faces) > MAX_INPUT_FACES:
                    raise InputError('at most 256 triangles per operand')
            elif kind in metadata:
                if len(row) < 2:
                    raise InputError('empty metadata record')
            else:
                raise InputError(f'unsupported OBJ record {kind!r}')
        except (ValueError, OverflowError) as error:
            raise InputError(f'line {number}: {error}') from None
    if not vertices or not faces:
        raise InputError('OBJ must contain vertices and triangle faces')
    converted = [[f32(x) for x in p] for p in vertices]
    deltas = [abs(x-y) for p,q in zip(vertices, converted) for x,y in zip(p,q)]
    return {'name': name, 'vertices': converted, 'faces': faces}, {
        'interpretation': 'decimal text -> Python binary64 -> Blender binary32',
        'changed_coordinate_count': sum(x != y for p,q in zip(vertices,converted) for x,y in zip(p,q)),
        'max_absolute_coordinate_delta': max(deltas),
        'vertex_and_triangle_order_preserved': True,
    }

def read_input(path):
    path = Path(path)
    if not path.is_file():
        raise InputError(f'input is not a regular file: {path}')
    with path.open('rb') as handle:
        data = handle.read(MAX_INPUT_BYTES + 1)
    mesh, conversion = parse_obj(data, path.name)
    source = {'name': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
              'conversion': conversion}
    return data, mesh, source

def json_bytes(value):
    data = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    if len(data) > MAX_REPORT_BYTES:
        raise InputError('report exceeds 10 MiB limit')
    return data

def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.partial')
    data = json_bytes(value)
    with temporary.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)

def load_report(path):
    with Path(path).open('rb') as handle:
        data = handle.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise InputError('report exceeds 10 MiB limit')
    def reject(value):
        raise InputError(f'non-finite JSON number {value}')
    result = json.loads(data, parse_constant=reject)
    if not isinstance(result, dict) or result.get('schema_version') != 1:
        raise InputError('unsupported report schema')
    return result

def write_obj(path, mesh):
    lines = ['# Solidrift exported native binary32 geometry']
    lines += ['v ' + ' '.join(repr(x) for x in p) for p in mesh['vertices']]
    lines += ['f ' + ' '.join(str(i+1) for i in f) for f in mesh['faces']]
    with Path(path).open('x', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
