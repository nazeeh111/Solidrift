"""Blender-only adapter; ordinary CLI imports never import bpy."""
import bpy
import bmesh
from .gate import check_exact

MAX_OUTPUT_VERTICES = 2048
MAX_OUTPUT_TRIANGLES = 2048

class BackendError(RuntimeError):
    pass

def make(name, mesh):
    data = bpy.data.meshes.new(name)
    data.from_pydata(mesh['vertices'], [], mesh['faces'])
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    return ob

def mesh_data(mesh):
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        if len(bm.verts) > MAX_OUTPUT_VERTICES or len(bm.faces) > MAX_OUTPUT_TRIANGLES:
            raise BackendError('native output exceeds 2048 vertices/triangles')
        bm.verts.index_update(); bm.faces.index_update()
        return {'vertices': [list(v.co) for v in bm.verts],
                'faces': [[v.index for v in f.verts] for f in bm.faces],
                'volume': bm.calc_volume(signed=True)}
    finally:
        bm.free()

def union(pair, solver):
    objects, meshes = [], []
    try:
        for i, source in enumerate(pair):
            ob = make('solidrift_operand_' + str(i), source)
            objects.append(ob); meshes.append(ob.data)
            imported = mesh_data(ob.data)
            if imported['vertices'] != source['vertices'] or imported['faces'] != source['faces']:
                raise BackendError('native import changed checked vertex/triangle mapping')
            gate = check_exact(imported['vertices'], imported['faces'])
            if not gate['valid']:
                raise BackendError('native input guard failed: ' + ', '.join(gate['reasons']))
        modifier = objects[0].modifiers.new('solidrift_union', 'BOOLEAN')
        modifier.operation = 'UNION'; modifier.solver = solver; modifier.object = objects[1]
        bpy.context.view_layer.update()
        evaluated = objects[0].evaluated_get(bpy.context.evaluated_depsgraph_get())
        output = evaluated.to_mesh()
        try:
            return mesh_data(output)
        finally:
            evaluated.to_mesh_clear()
    finally:
        for ob in objects:
            bpy.data.objects.remove(ob, do_unlink=True)
        for mesh in meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
