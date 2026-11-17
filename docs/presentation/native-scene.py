"""Build or reopen the recorded mesh scene, and repeat four decisive native queries.
Run only inside Blender, with --factory-startup --disable-autoexec.
"""
from pathlib import Path
import sys,json,math,hashlib
import bpy
from mathutils import Vector
P=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:];source=Path(args[0]).resolve();out=Path(args[1]).resolve();mode=args[2] if len(args)>2 else 'build';sys.path.insert(0,str(source))
from solidrift.native import union
from solidrift.reducer import failure_signature
from solidrift.engine import metrics
from solidrift.surface import correspondence
r=json.loads((P/'case/report.json').read_text());a=r['repair']['accepted'];original=list(r['baseline']['inputs'].values())
def canonical(m):
 triangles=[]
 for face in m['faces']:
  p=[tuple(m['vertices'][i]) for i in face];triangles.append(min(tuple(p[j:]+p[:j]) for j in range(3)))
 return sorted(triangles)
def decisive():
 checks=[]
 for name,pair in [('original',original),('witness',r['reduction']['operands']),('repair',a['full_repaired']),('undo',a['undo_inputs'])]:
  result=union(pair,'FLOAT');ref=r['baseline']['outputs']['FLOAT'] if name=='original' else r['reduction']['final_outputs']['FLOAT'] if name=='witness' else a['full_check']['output_geometry'] if name=='repair' else a['undo_signature']['geometry'];same=canonical(result)==canonical(ref);assert same,name
  checks.append({'stage':name,'FLOAT_recomputed_geometry_matches_record':same,'comparison':'coordinate-exact oriented triangle multiset','failure_matches':failure_signature([metrics(m) for m in pair],result)['matches']})
 assert [q['failure_matches'] for q in checks]==[True,True,False,True];return checks
if mode=='build':
 if out.exists():raise RuntimeError('Output must be a new directory')
 out.mkdir();bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='NONE';scene['Solidrift_scope']='One recorded Blender FLOAT omission; coordinates are abstract model units, not a manufactured part.'
 mats={}
 for n,c in [('A',(0.20,.75,.65,1)),('B',(.30,.52,.93,1)),('FLOAT',(.30,.52,.93,1)),('MANIFOLD',(.85,.94,.45,1))]:
  m=bpy.data.materials.new(n);m.diffuse_color=c;mats[n]=m
 meshes=[]
 for row,(label,pair,outputs) in enumerate([('Original',original,r['baseline']['outputs']),('Witness',r['reduction']['operands'],r['reduction']['final_outputs'])]):
  for col,records in enumerate([[('A',pair[0]),('B',pair[1])],[('FLOAT',outputs['FLOAT'])],[('MANIFOLD',outputs['MANIFOLD'])]]):
   for role,m in records:
    name=label+'_'+role;data=bpy.data.meshes.new(name);data.from_pydata(m['vertices'],[],m['faces']);data.update();ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=(col*90,row*-100,0);ob.data.materials.append(mats[role]);ob['recorded_mesh_sha256']=hashlib.sha256(json.dumps({'vertices':m['vertices'],'faces':m['faces']},sort_keys=True).encode()).hexdigest();ob['display_offset_only']=list(ob.location);meshes.append(ob)
 # Native render is an inspection sheet; only object display translations separate its panels.
 bpy.context.view_layer.update();scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=True;scene.display.shading.show_object_outline=True;scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('SolidriftWorld');scene.world.color=(.025,.045,.07)
 camera_data=bpy.data.cameras.new('Inspection');camera=bpy.data.objects.new('Inspection',camera_data);scene.collection.objects.link(camera);target=Vector((90,-20,0));camera.location=target+Vector((140,-210,160));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=330;scene.camera=camera;scene.render.resolution_x=1200;scene.render.resolution_y=760;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out/'native-inspection.png');bpy.ops.render.render(write_still=True)
 # Full model coordinates stay in mesh data. OBJ export is explicit raw geometry, not the panel locations.
 from solidrift.io import write_obj
 write_obj(out/'witness-A.obj',r['reduction']['operands'][0]);write_obj(out/'witness-B.obj',r['reduction']['operands'][1]);bpy.ops.wm.save_as_mainfile(filepath=str(out/'inspection.blend'))
else:
 bpy.ops.wm.open_mainfile(filepath=str(out/'inspection.blend'));meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==8
 for ob in meshes:
  label,role=ob.name.split('_');pair=original if label=='Original' else r['reduction']['operands'];outputs=r['baseline']['outputs'] if label=='Original' else r['reduction']['final_outputs'];ref=pair[0 if role=='A' else 1] if role in ('A','B') else outputs[role]
  assert [list(v.co) for v in ob.data.vertices]==ref['vertices'] and [list(f.vertices) for f in ob.data.polygons]==ref['faces'],ob.name
 from solidrift.io import read_input
 for i,n in enumerate(['witness-A.obj','witness-B.obj']):
  _,m,_=read_input(out/n);ref=r['reduction']['operands'][i];assert m['vertices']==ref['vertices'] and m['faces']==ref['faces']
checks=decisive();record={'blender':bpy.app.version_string,'build_hash':bpy.app.build_hash.decode(),'mesh_objects':len(meshes),'native_queries':4,'checks':checks,'input_undo_exact':a['undo_inputs']==r['reduction']['original_operands'],'units':'abstract model units; scene display offsets recorded per object','scope':'Exact retained geometry repeat on this build; no universal union correctness or global minimality'};(out/('reopened.json' if mode=='reopen' else 'native.json')).write_text(json.dumps(record,indent=2)+'\n');print('RESULT '+json.dumps(record))
