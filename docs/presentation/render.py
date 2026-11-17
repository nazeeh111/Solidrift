"""Orthographic x-ray projections of the freshly exported native meshes, no invented surfaces."""
from pathlib import Path
import math,json,html,hashlib
P=Path(__file__).resolve().parent;r=json.loads((P/'case/report.json').read_text());original=list(r['baseline']['inputs'].values());witness=r['reduction']['operands'];accepted=r['repair']['accepted'];points=[v for m in original for v in m['vertices']];lo=[min(v[k] for v in points) for k in range(3)];hi=[max(v[k] for v in points) for k in range(3)];center=[(a+b)/2 for a,b in zip(lo,hi)];yaw=.55;pitch=-.30;basis=[[math.cos(yaw),0,math.sin(yaw)],[math.sin(pitch)*math.sin(yaw),math.cos(pitch),-math.sin(pitch)*math.cos(yaw)],[-math.cos(pitch)*math.sin(yaw),math.sin(pitch),math.cos(pitch)*math.cos(yaw)]]
assert all(abs(sum(a*b for a,b in zip(u,v))-(1 if i==j else 0))<1e-14 for i,u in enumerate(basis) for j,v in enumerate(basis))
INK='#edf5fa';MUTED='#b6c7d4';PAPER='#08121d';A='#5de4d0';B='#93b9ff';REF='#e6f58a';BG='#10202e'
allcoords=[]
for phone in [False,True]:
 name='witness-mobile' if phone else 'witness';W,H=(480,1710) if phone else (1200,1080);scale=3.3 if phone else 5.2;out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="{name}-title {name}-desc" font-family="Arial"><title id="{name}-title">Solidrift failure-preserving reduction on Blender 5.2.1</title><desc id="{name}-desc">Original operands have132 triangles. Two valid reduced operands have12 triangles and retain the FLOAT missing-region failure. All four geometry panels use one orthographic camera basis and equal model-unit scale. Yellow wire is the separate MANIFOLD comparator, not an ideal-union proof.</desc><rect width="100%" height="100%" fill="{PAPER}"/>']
 def text(x,y,value,size=18,color=INK,bold=False):out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(str(value))}</text>')
 text(28,38,'Solidrift / A smaller input, the same omission',15,A)
 text(28,89,'132 triangles become 12.',30 if phone else 46,bold=True)
 text(28,130,'The missing region survives.',25 if phone else 34,bold=True)
 text(28,174,'Actual native exports. Blender 5.2.1 LTS.',16 if phone else 22,MUTED)
 panels=[('Original inputs',[(original[0],A,False),(original[1],B,False)],'A + B · 132 input triangles'),('Original FLOAT result',[(r['baseline']['outputs']['FLOAT'],B,False),(r['baseline']['outputs']['MANIFOLD'],REF,True)],'Yellow wire: MANIFOLD comparator'),('Reduced witness',[(witness[0],A,False),(witness[1],B,False)],'A + B · 12 input triangles'),('Reduced FLOAT result',[(r['reduction']['final_outputs']['FLOAT'],B,False),(r['reduction']['final_outputs']['MANIFOLD'],REF,True)],'Same declared omission family')]
 for index,(title,meshes,caption) in enumerate(panels):
  x,y=(28,215+index*315) if phone else (28+(index%2)*586,220+(index//2)*320);pw,ph=(424,286) if phone else (558,292);cx,cy=x+pw/2,y+ph/2+8
  out.append(f'<rect x="{x}" y="{y}" width="{pw}" height="{ph}" fill="{BG}"/>');text(x+16,y+31,title,21 if phone else 25,bold=True);text(x+16,y+ph-16,caption,14 if phone else 16,MUTED)
  def project(v):
   q=[v[k]-center[k] for k in range(3)];return(cx+sum(a*b for a,b in zip(q,basis[0]))*scale,cy-sum(a*b for a,b in zip(q,basis[1]))*scale,sum(a*b for a,b in zip(q,basis[2])))
  polygons=[]
  for mesh,color,wire in meshes:
   projected=[project(v) for v in mesh['vertices']]
   for fi,f in enumerate(mesh['faces']):
    pp=[projected[i] for i in f];polygons.append((sum(v[2] for v in pp)/3,pp,color,wire,fi))
  for depth,pp,color,wire,fi in sorted(polygons,key=lambda z:z[0]):
   coords=' '.join(f'{v[0]:.6f},{v[1]:.6f}' for v in pp);out.append(f'<polygon points="{coords}" fill="{"none" if wire else color}" fill-opacity="{0 if wire else .24}" stroke="{color}" stroke-opacity="{.8 if wire else .45}" stroke-width="{.8 if wire else .65}"/>');allcoords.append({'figure':name,'panel':index,'face':fi,'wire':wire,'points':[[v[0],v[1]] for v in pp]})
  # A model-unit scale bar has the same length in all four panels of a composition.
  bar=10*scale;out.append(f'<path d="M{x+16} {y+ph-52}h{bar}" fill="none" stroke="{INK}" stroke-width="2"/>');text(x+16,y+ph-61,'10 model units',12,MUTED)
 y=1520 if phone else 906;text(28,y,'60 accepted contractions. Valid closed operands.',16 if phone else 23,A,True)
 text(28,y+37,'3 witness vertices → 13 original vertices.',17 if phone else 22)
 text(28,y+72,'Intervention accepted; exact input undo reproduced the failure.',12 if phone else 18,MUTED)
 text(28,y+109,'One bounded case, not a global minimum or a universal Boolean repair.',11 if phone else 17,MUTED)
 text(28,y+143,'Manifold regression operands · Apache-2.0. Abstract model units.',11 if phone else 16,MUTED)
 out.append('</svg>');svg='\n'.join(out).replace('have132','have 132').replace('have12','have 12');(P/(name+'.svg')).write_text(svg+'\n');(P/(name+'.html')).write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Solidrift native witness</title><style>body{margin:0}svg{display:block;min-width:'+str(W)+'px}.diagram-container{overflow-x:auto}</style><div class="diagram-container">'+svg+'</div></html>')
(P/'projection.json').write_text(json.dumps({'source_report_sha256':hashlib.sha256((P/'case/report.json').read_bytes()).hexdigest(),'basis_rows':basis,'basis_orthonormal':True,'center':center,'units':'Abstract model units, no physical manufacturing calibration','scale_px_per_model_unit':{'witness':5.2,'witness-mobile':3.3},'equal_scale_within_each_composition':True,'xray_transparency':'All stored triangles shown with depth-sorted translucent fill; comparison as wire; no interpolated or invented native intermediate outputs','polygons':allcoords},indent=2)+'\n')
