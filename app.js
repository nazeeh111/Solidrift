/* Solidrift's viewer displays stored native exports; it does not run Blender. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id), cap = 10 * 1024 * 1024;
  let report, states = [], stage = 'original', selected = null;
  const camera = {yaw:.55, pitch:-.30, zoom:1}, canvases = [$('input'), $('output')];
  // Keep inputs before the observed output at every width, including focus order.
  let center = [0,0,0], span = 1, picks = [];
  const clone = value => JSON.parse(JSON.stringify(value));
  const meshOK = m => m && Array.isArray(m.vertices) && m.vertices.length > 0 && m.vertices.length <= 5000 &&
    m.vertices.every(v => Array.isArray(v) && v.length === 3 && v.every(Number.isFinite)) &&
    Array.isArray(m.faces) && m.faces.length > 0 && m.faces.length <= 10000 &&
    m.faces.every(f => Array.isArray(f) && f.length === 3 && f.every(i => Number.isInteger(i) && i >= 0 && i < m.vertices.length));
  function validate(r) {
    if (!r || r.schema_version !== 1 || !r.baseline || !r.baseline.inputs || !r.baseline.outputs) throw Error('Expected a Solidrift schema 1 report with native baseline geometry.');
    const inputs = Object.values(r.baseline.inputs);
    if (inputs.length !== 2 || !inputs.every(meshOK) || !meshOK(r.baseline.outputs.FLOAT)) throw Error('Invalid or oversized baseline meshes.');
    if (r.reduction) {
      if (!Array.isArray(r.reduction.original_operands) || !Array.isArray(r.reduction.operands) || r.reduction.operands.length !== 2 || !r.reduction.operands.every(meshOK)) throw Error('Invalid reduction geometry.');
      if (!Array.isArray(r.reduction.accepted_steps) || r.reduction.accepted_steps.length > 1000) throw Error('Invalid reduction trace.');
    }
    const a = r.repair?.accepted;
    if (a && (!Array.isArray(a.full_repaired) || a.full_repaired.length !== 2 || !a.full_repaired.every(meshOK) || !meshOK(a.full_check?.output_geometry) || !meshOK(a.full_check?.reference_geometry))) throw Error('Invalid repair geometry.');
    if (a && (!Array.isArray(a.undo_inputs) || a.undo_inputs.length !== 2 || !a.undo_inputs.every(meshOK) || !meshOK(a.undo_signature?.geometry))) throw Error('Invalid undo geometry.');
    if (a && (![0,1].includes(a.intervention?.side) || !Array.isArray(a.intervention.delta) || a.intervention.delta.length !== 3 || !a.intervention.delta.every(Number.isFinite) || !Array.isArray(a.cluster) || !a.cluster.every(i=>Number.isInteger(i) && i>=0 && i<inputs[a.intervention.side].vertices.length))) throw Error('Invalid patch metadata.');
    return r;
  }
  function replay(r) {
    if (!r.reduction) return [];
    let pair = clone(r.reduction.original_operands);
    if (pair.length !== 2 || !pair.every(meshOK)) throw Error('Invalid original reduction operands.');
    const values = [clone(pair)];
    for (const s of r.reduction.accepted_steps) {
      if (![0,1].includes(s.operand) || !Array.isArray(s.edge) || s.edge.length !== 2 || !Array.isArray(s.vertex_after)) throw Error('Malformed accepted step.');
      const m = pair[s.operand], [u,v] = [...s.edge].sort((a,b)=>a-b);
      if (!Number.isInteger(u) || !Number.isInteger(v) || u < 0 || v <= u || v >= m.vertices.length) throw Error('Trace edge out of range.');
      m.vertices[u] = [...s.vertex_after]; m.vertices.splice(v,1);
      m.faces = m.faces.filter(f => !(f.includes(u) && f.includes(v))).map(f => f.map(i => (i === v ? u : i)).map(i => i > v ? i-1 : i));
      if (m.ancestry) {
        const left=m.ancestry[u],right=m.ancestry[v];
        if (!left?.cluster || !right?.cluster) throw Error('Malformed ancestry.');
        m.ancestry[u] = {cluster:[...new Set([...left.cluster,...right.cluster])].sort((a,b)=>a-b)};
        m.ancestry.splice(v,1);
      }
      if (!pair.every(meshOK)) throw Error('Trace creates invalid indices or coordinates.');
      values.push(clone(pair));
    }
    for (let side=0;side<2;side++) {
      const actual = values.at(-1)[side], stored = r.reduction.operands[side];
      if (JSON.stringify(actual.vertices) !== JSON.stringify(stored.vertices) || JSON.stringify(actual.faces) !== JSON.stringify(stored.faces)) throw Error('Trace does not reconstruct the stored witness.');
      actual.ancestry = clone(stored.ancestry);
    }
    return values;
  }
  function text(id,value) { $(id).textContent = value ?? ''; }
  function format(value) { return Number.isFinite(value) ? value.toPrecision(5) : 'unavailable'; }
  function completedReduction() { return ['repaired','witness'].includes(report?.status) && states.length > 0; }
  function load(r) {
    const candidate = validate(r), candidateStates = replay(candidate);
    report = candidate; states = candidateStates; selected = null; stage = 'original';
    $('error').hidden = true;
    const original = Object.values(report.baseline.inputs), points=original.flatMap(m=>m.vertices);
    const originalTriangles=original.reduce((sum,m)=>sum+m.faces.length,0);
    const witnessTriangles=report.reduction?.operands?.reduce((sum,m)=>sum+m.faces.length,0);
    const failureRecorded=completedReduction();
    const hasRepair=report.status==='repaired' && !!report.repair?.accepted;
    text('case-eyebrow',failureRecorded?'RECORDED CASE / MISSING SOLID':report.status==='no_failure'?'RECORDED CASE / NO TARGET OMISSION':'RECORDED CASE / INCOMPLETE RUN');
    text('case-headline',failureRecorded?'The failure survives the cut.':report.status==='no_failure'?'No target omission found.':'Inspect the partial evidence.');
    text('case-orientation',failureRecorded?'A union should combine both solids. In this recorded run, Blender’s FLOAT solver returns A and drops B.':'A union should combine both input solids. Compare the inputs with the solver’s recorded output.');
    text('case-ratio',failureRecorded && witnessTriangles<originalTriangles ? `${originalTriangles} → ${witnessTriangles} TRI` : `${originalTriangles} TRI`);
    text('case-lead',failureRecorded
      ? `${witnessTriangles<originalTriangles?`${originalTriangles} input triangles become a ${witnessTriangles}-triangle witness: a smaller input that keeps the same failure.`:`The recorded witness has ${witnessTriangles} triangles and retains the failure.`} Open Witness to inspect it.${hasRepair?' Repair and Undo show the tested geometry change and its reversal.':''}`
      :report.status==='no_failure'?'The recorded baseline did not show this detector’s omission family. Inspect the inputs and native outputs; no witness or repair is claimed.'
      :'The native run did not finish with a supported result. Inspect the stored baseline and status; no witness or repair is claimed.');
    const lo=[0,1,2].map(k=>Math.min(...points.map(p=>p[k]))), hi=[0,1,2].map(k=>Math.max(...points.map(p=>p[k])));
    center=lo.map((x,k)=>(x+hi[k])/2); span=Math.max(...lo.map((x,k)=>hi[k]-x),1e-9);
    text('receipt-title', ['repaired','witness','no_failure'].includes(report.status) ? 'Recorded native run' : `Incomplete native run: ${report.status || 'unknown'}`);
    text('receipt-detail', ['repaired','witness','no_failure'].includes(report.status) ? 'Actual exported geometry. Orbit either view to inspect the omission, reduction, intervention and undo.' : 'Partial evidence only. Repair and undo are disabled because this run did not finish successfully.');
    text('backend', `${report.baseline.backend || 'Blender'} · ${report.baseline.build_hash || 'build not recorded'}`);
    const n=states.length ? states.length-1 : 0; $('step').max=n; $('step').value=n;
    $('step').disabled=!n; $('trace-view').disabled=!n; text('step-count', `${n} ${failureRecorded||report.status==='no_failure'?'accepted':'stored'} contractions`);
    const accepted=report.status==='repaired' ? report.repair?.accepted : null;
    const witnessButton=document.querySelector('button[data-stage="witness"]');
    witnessButton.disabled=!states.length;
    witnessButton.lastChild.textContent=failureRecorded||!states.length?' Witness':' Partial';
    for (const name of ['repaired','undo']) document.querySelector(`button[data-stage="${name}"]`).disabled=!accepted;
    $('patch-vertices').replaceChildren();
    if (accepted) {
      const d=accepted.intervention.delta, count=accepted.cluster.length;
      text('patch-description', `${accepted.intervention.vertices?.length ?? 1} witness vertices lead to ${count} original vertices in operand ${accepted.intervention.side === 0 ? 'A' : 'B'}. The same boundary translation is tested again on the full model. Faces stay unchanged.`);
      for (const v of accepted.cluster) { const el=document.createElement('span'); el.textContent=`v${v}`; $('patch-vertices').append(el); }
      text('patch-bound', `Translation [${d.map(format).join(', ')}] in model units. Stored before/after coordinates support exact input undo. This changes the geometry, rather than fixing the solver.`);
    } else {
      text('patch-description', 'No accepted full-model patch in this report. A rejected or unsupported repair is never displayed as a success.'); text('patch-bound','');
    }
    $('evidence-link').hidden = !report.demo;
    text('selection',failureRecorded||!states.length?'Choose Witness to inspect a vertex and its source cluster.':'Choose Partial to inspect a stored vertex and its source cluster.');
    camera.yaw=.55; camera.pitch=-.30; camera.zoom=1; update();
  }
  function activePair() {
    if (stage==='witness') return states[Number($('step').value)];
    if (stage==='repaired') return report.repair.accepted.full_repaired;
    if (stage==='undo') return report.repair.accepted.undo_inputs;
    return Object.values(report.baseline.inputs);
  }
  function outputPair() {
    if (stage==='witness') return Number($('step').value)===states.length-1 ? report.reduction.final_outputs : null;
    if (stage==='repaired') {const c=report.repair.accepted.full_check;return {FLOAT:c.output_geometry,MANIFOLD:c.reference_geometry};}
    if (stage==='undo') return {FLOAT:report.repair.accepted.undo_signature.geometry,MANIFOLD:report.baseline.outputs.MANIFOLD};
    return report.baseline.outputs;
  }
  function update() {
    if (!report) return;
    document.querySelector('.workbench').dataset.stage=stage;
    document.querySelectorAll('button[data-stage]').forEach(b=>{b.classList.toggle('active',b.dataset.stage===stage);b.setAttribute('aria-pressed',b.dataset.stage===stage);});
    const pair=activePair(), n=pair.reduce((s,m)=>s+m.faces.length,0), original=Object.values(report.baseline.inputs).reduce((s,m)=>s+m.faces.length,0);
    text('triangles',n); text('triangle-detail',`${pair[0].faces.length} in A + ${pair[1].faces.length} in B`);
    const end=Number($('step').value), trace=report.reduction?.accepted_steps, complete=completedReduction();
    const partial=!complete && report.status!=='no_failure';
    text('input-title',stage==='witness'?`${complete?'Witness':'Stored'} inputs · state ${end}`:stage==='repaired'?'Repaired input solids':stage==='undo'?'Restored input solids':partial?'Recorded input solids / A + B':'Input solids / A + B');
    text('output-title',stage==='undo'?'Observed / B missing again':stage==='repaired'?'Observed / comparison accepted':stage==='witness'&&(end<states.length-1||!outputPair())?'Native output / not stored':stage==='witness'?complete?'Observed / same missing solid':'Native output / partial record':report.status==='no_failure'?'FLOAT / recorded output':complete?'Observed / B missing (FLOAT)':'FLOAT / partial baseline output');
    text('fault',stage==='repaired'?'Comparison accepted':partial?'Incomplete native run':stage==='witness'&&end<states.length-1?'Recorded omission test':report.status==='no_failure'?'No target omission':complete?'Operand B omitted':'Incomplete native run');
    $('fault').style.color=stage==='repaired'||report.status==='no_failure'?'var(--teal)':complete?'var(--failure)':'var(--muted)';
    text('fault-detail',stage==='repaired'?'Valid exports + volume + paired surface bound':partial?'Stored native geometry; completion not established.':stage==='witness'&&end<states.length-1?'Native query passed in the stored trace':'Stored native output, not a browser simulation');
    text('third-label',stage==='repaired'?'FULL-MODEL PATCH':partial?'STORED INPUT COUNTS':'REDUCTION');
    text('third',stage==='repaired'?`${report.repair.accepted.cluster.length} vertices`:report.reduction&&report.status!=='no_failure'?`${original} → ${report.reduction.operands.reduce((s,m)=>s+m.faces.length,0)}`:'—');
    const bound=report.repair?.accepted?.full_check?.surface_correspondence?.whole_paired_surface_distance_upper_bound ?? report.repair?.accepted?.full_check?.correspondence?.distance_bound;
    text('third-detail',stage==='repaired'?(bound?`Paired surface separation ≤ ${format(bound)}`:'Paired exported surfaces checked in native run'):partial?'Recorded geometry only; no completed reduction is claimed.':complete?'Valid inputs; same declared omission family':'No failure-preserving reduction in this report');
    const s=end?trace?.[end-1]:null;
    text('step-detail',s?`Step ${end} · operand ${s.operand===0?'A':'B'} · edge ${s.edge.join(' ↔ ')} · ${s.choice} · query ${s.native_query}`:'State 0 · original imported operands');
    text('input-note',stage==='witness'?'Click a vertex or use the ancestry controls below':'Drag to orbit · scroll to zoom · R to reset');
    text('output-note',stage==='witness'&&end<states.length-1?complete?'Intermediate output surfaces were not stored. Final witness output is available at the last state.':'Intermediate output surfaces were not stored. Any recorded final output is shown at the last state.':'Pale wire shows the MANIFOLD comparison surface; inspect the input operands in the other view.');
    $('vertex-inspector').hidden=stage!=='witness';
    if(stage==='witness')inspectVertex(selected?.side ?? 0,selected?.index ?? 0);
    else {text('selection',complete||!states.length?'Choose Witness to inspect a vertex and its source cluster.':'Choose Partial to inspect a stored vertex and its source cluster.');draw();}
  }
  function inspectVertex(side,index) {
    if(stage!=='witness')return;
    const mesh=activePair()[side];
    $('vertex-side').value=String(side);
    $('vertex-index').max=String(mesh.vertices.length-1);
    text('vertex-range',`0–${mesh.vertices.length-1} in operand ${side?'B':'A'}`);
    if(!Number.isInteger(index)||index<0||index>=mesh.vertices.length){
      selected=null;
      $('vertex-index').setAttribute('aria-invalid','true');
      text('selection',`Enter a whole vertex index from 0 to ${mesh.vertices.length-1}.`);
      draw();return;
    }
    $('vertex-index').setAttribute('aria-invalid','false');
    $('vertex-index').value=String(index);
    selected={side,index};
    const cluster=mesh.ancestry?.[index]?.cluster;
    text('selection',`Operand ${side?'B':'A'} v${index} consumes original source indices: ${cluster?.join(', ') ?? 'not recorded'}. Clusters track contractions; they are not exact affine coordinates after native rounding.`);
    draw();
  }
  function transform(p) {
    let [x,y,z]=p.map((v,k)=>(v-center[k])/span);
    const c=Math.cos(camera.yaw),s=Math.sin(camera.yaw),d=Math.cos(camera.pitch),t=Math.sin(camera.pitch);
    const xx=c*x+s*z, zz=-s*x+c*z;
    return [xx, d*y-t*zz, t*y+d*zz];
  }
  function render(canvas,meshes) {
    const box=canvas.getBoundingClientRect(),w=box.width,h=box.height,dpr=Math.min(devicePixelRatio||1,2);
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
    const scale=Math.min(w*.96,h*.94)*camera.zoom, project=p=>{const q=transform(p);return [w/2+q[0]*scale,h/2-q[1]*scale,q[2]];};
    ctx.strokeStyle='#263a4b';ctx.lineWidth=.6;
    for(let i=-5;i<=5;i++){const q=i/10;for(const ps of [[[-.5,-.55,q],[.5,-.55,q]],[[q,-.55,-.5],[q,-.55,.5]]]){const pts=ps.map(p=>project(p.map((x,k)=>x*span+center[k])));ctx.beginPath();ctx.moveTo(...pts[0].slice(0,2));ctx.lineTo(...pts[1].slice(0,2));ctx.stroke();}}
    if (!meshes) {ctx.fillStyle='#a6b9c7';ctx.textAlign='center';ctx.font='12px ui-monospace,monospace';ctx.fillText('No stored output for this state',w/2,h/2);return;}
    const polygons=[],rings=[];
    meshes.forEach(({mesh,color,wire,side})=>{
      if(!meshOK(mesh))return;
      const pts=mesh.vertices.map(project);
      mesh.faces.forEach(f=>{const pp=f.map(i=>pts[i]);const a=pp[0],b=pp[1],c=pp[2],u=b.map((v,k)=>v-a[k]),v=c.map((vv,k)=>vv-a[k]),nn=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],normal=Math.hypot(...nn);const light=normal?Math.abs(nn[2])/normal:0;polygons.push({pp,color,wire,depth:pp.reduce((s,p)=>s+p[2],0)/3,light});});
      if(canvas.id==='input'&&stage==='witness') pts.forEach((p,index)=>picks.push({x:p[0],y:p[1],side,index,ancestry:mesh.ancestry?.[index]}));
      const accepted=report.status==='repaired' ? report.repair?.accepted : null;
      const ids=canvas.id==='input' && stage==='repaired' && side===accepted?.intervention.side ? accepted.cluster
        :canvas.id==='input' && stage==='witness' && selected && selected.side===side ? [selected.index] : [];
      for(const id of ids){if(pts[id])rings.push(pts[id]);}
    });
    polygons.sort((a,b)=>a.depth-b.depth);
    for(const p of polygons){ctx.beginPath();p.pp.forEach((q,i)=>i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]));ctx.closePath();if(!p.wire){ctx.globalAlpha=.21+.32*p.light;ctx.fillStyle=p.color;ctx.fill();}ctx.globalAlpha=p.wire?.58:.65;ctx.strokeStyle=p.color;ctx.lineWidth=p.wire?.7:.8;ctx.stroke();}ctx.globalAlpha=1;
    // Markers belong to input vertices and must be painted after triangles.
    for(const p of rings){ctx.beginPath();ctx.arc(p[0],p[1],4.5,0,Math.PI*2);ctx.strokeStyle='#e6f58a';ctx.lineWidth=1.8;ctx.stroke();}
    if(canvas.id==='input'&&stage==='witness'){for(const p of picks){ctx.beginPath();ctx.arc(p.x,p.y,2.2,0,Math.PI*2);ctx.fillStyle=p.side?'#93b9ff':'#5de4d0';ctx.fill();}}
  }
  function draw(){if(!report)return;picks=[];render($('input'),activePair().map((mesh,side)=>({mesh,side,color:side?'#93b9ff':'#5de4d0'})));const o=outputPair();render($('output'),o?[{mesh:o.FLOAT,color:'#93b9ff',side:0},...($('reference').checked&&meshOK(o.MANIFOLD)?[{mesh:o.MANIFOLD,color:'#e6f58a',wire:true}]:[])]:null);}
  for(const canvas of canvases){let drag=null;
    canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{if(!drag)return;camera.yaw+=(e.clientX-drag.x)*.008;camera.pitch=Math.max(-1.45,Math.min(1.45,camera.pitch+(e.clientY-drag.y)*.008));drag.x=e.clientX;drag.y=e.clientY;draw();});
    canvas.addEventListener('pointerup',e=>{if(drag&&canvas.id==='input'&&stage==='witness'&&Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<4){const b=canvas.getBoundingClientRect(),x=e.clientX-b.left,y=e.clientY-b.top;const hit=picks.map(p=>({...p,d:Math.hypot(p.x-x,p.y-y)})).filter(p=>p.d<12).sort((a,b)=>a.d-b.d)[0];if(hit)inspectVertex(hit.side,hit.index);}drag=null;});
    canvas.addEventListener('pointercancel',()=>{drag=null;});
    canvas.addEventListener('wheel',e=>{e.preventDefault();camera.zoom=Math.max(.3,Math.min(4,camera.zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});
    canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','r','R'].includes(e.key)){e.preventDefault();if(e.key==='ArrowLeft')camera.yaw-=.1;if(e.key==='ArrowRight')camera.yaw+=.1;if(e.key==='ArrowUp')camera.pitch-=.1;if(e.key==='ArrowDown')camera.pitch+=.1;if(e.key.toLowerCase()==='r'){camera.yaw=.55;camera.pitch=-.30;camera.zoom=1;}draw();}});
  }
  document.querySelectorAll('button[data-stage]').forEach(b=>b.addEventListener('click',()=>{stage=b.dataset.stage;selected=null;update();}));
  $('step').addEventListener('input',()=>{if(stage==='witness'){selected=null;update();}else{const n=Number($('step').value),s=report?.reduction?.accepted_steps[n-1];text('step-detail',s?`Step ${n} · operand ${s.operand===0?'A':'B'} · edge ${s.edge.join(' ↔ ')} · ${s.choice}`:'State 0 · original imported operands');}});
  $('trace-view').addEventListener('click',()=>{stage='witness';selected=null;update();});
  $('reference').addEventListener('change',draw);window.addEventListener('resize',draw);
  $('vertex-side').addEventListener('change',()=>inspectVertex(Number($('vertex-side').value),0));
  $('vertex-index').addEventListener('input',()=>inspectVertex(Number($('vertex-side').value),$('vertex-index').value===''?NaN:Number($('vertex-index').value)));
  function download(name,contents,type='application/json'){const url=URL.createObjectURL(new Blob([contents],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  $('download-json').addEventListener('click',()=>{if(report)download('solidrift-report.json',JSON.stringify(report,null,2)+'\n');});
  $('download-input').addEventListener('click',()=>{if(!report)return;activePair().forEach((m,i)=>download(`solidrift-${stage}-${i?'B':'A'}.obj`,'# Solidrift displayed geometry; native binary32 coordinates\n'+m.vertices.map(v=>'v '+v.join(' ')).join('\n')+'\n'+m.faces.map(f=>'f '+f.map(i=>i+1).join(' ')).join('\n')+'\n','text/plain'));});
  function fail(e){$('error').hidden=false;text('error',`${e.message} ${report?'The previous report remains displayed.':''}`);}
  $('file').addEventListener('change',async()=>{const f=$('file').files[0];if(!f)return;try{if(f.size>cap)throw Error('Report exceeds the 10 MiB viewer limit.');load(JSON.parse(await f.text()));}catch(e){fail(e);}finally{$('file').value='';}});
  (async()=>{try{const embedded=$('solidrift-data').textContent.trim();if(embedded!=='__SOLIDRIFT_DATA__')load(JSON.parse(embedded));else{const response=await fetch('demo/report.json');if(!response.ok)throw Error('Could not load the demo report. Open a report JSON or use the CLI offline HTML export.');const body=await response.text();if(body.length>cap)throw Error('Demo exceeds report limit.');load(JSON.parse(body));}}catch(e){fail(e);}})();
})();
