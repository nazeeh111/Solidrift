/* Solidrift's viewer displays stored native exports; it does not run Blender. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id), cap = 10 * 1024 * 1024;
  let report, states = [], stage = 'original', selected = null;
  const camera = {yaw:.55, pitch:-.30, zoom:1}, canvases = [$('input'), $('output')];
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
  function load(r) {
    const candidate = validate(r), candidateStates = replay(candidate);
    report = candidate; states = candidateStates; selected = null; stage = 'original';
    $('error').hidden = true;
    const original = Object.values(report.baseline.inputs), points=original.flatMap(m=>m.vertices);
    const lo=[0,1,2].map(k=>Math.min(...points.map(p=>p[k]))), hi=[0,1,2].map(k=>Math.max(...points.map(p=>p[k])));
    center=lo.map((x,k)=>(x+hi[k])/2); span=Math.max(...lo.map((x,k)=>hi[k]-x),1e-9);
    text('receipt-title', ['repaired','witness','no_failure'].includes(report.status) ? 'Recorded native run' : `Incomplete native run: ${report.status || 'unknown'}`);
    text('receipt-detail', ['repaired','witness','no_failure'].includes(report.status) ? 'Actual exported geometry. Orbit either view to inspect the omission, reduction, intervention and undo.' : 'Partial evidence only. Repair and undo are disabled because this run did not finish successfully.');
    text('backend', `${report.baseline.backend || 'Blender'} · ${report.baseline.build_hash || 'build not recorded'}`);
    const n=states.length ? states.length-1 : 0; $('step').max=n; $('step').value=n;
    $('step').disabled=!n; $('trace-view').disabled=!n; text('step-count', `${n} accepted contractions`);
    const accepted=report.status==='repaired' ? report.repair?.accepted : null;
    document.querySelector('[data-stage="witness"]').disabled=!states.length;
    for (const name of ['repaired','undo']) document.querySelector(`[data-stage="${name}"]`).disabled=!accepted;
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
    text('selection','Click a witness vertex to inspect its source cluster.');
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
    document.querySelectorAll('[data-stage]').forEach(b=>{b.classList.toggle('active',b.dataset.stage===stage);b.setAttribute('aria-pressed',b.dataset.stage===stage);});
    const pair=activePair(), n=pair.reduce((s,m)=>s+m.faces.length,0), original=Object.values(report.baseline.inputs).reduce((s,m)=>s+m.faces.length,0);
    text('triangles',n); text('triangle-detail',`${pair[0].faces.length} in A + ${pair[1].faces.length} in B`);
    const end=Number($('step').value), trace=report.reduction?.accepted_steps;
    text('input-title',stage==='witness'?`Witness · state ${end}`:stage==='repaired'?'Repaired operands':stage==='undo'?'Restored operands':'Original operands');
    text('output-title',stage==='undo'?'FLOAT union · failure restored':'FLOAT union');
    text('fault',stage==='repaired'?'Comparison accepted':stage==='witness'&&end<states.length-1?'Recorded omission test':report.reduction?'Operand B omitted':'See recorded baseline');
    $('fault').style.color=stage==='repaired'?'var(--teal)':'var(--orange)';
    text('fault-detail',stage==='repaired'?'Valid exports + volume + paired surface bound':stage==='witness'&&end<states.length-1?'Native query passed in the stored trace':'Stored native output, not a browser simulation');
    text('third-label',stage==='repaired'?'FULL-MODEL PATCH':'REDUCTION');
    text('third',stage==='repaired'?`${report.repair.accepted.cluster.length} vertices`:`${original} → ${report.reduction?.operands.reduce((s,m)=>s+m.faces.length,0) ?? original}`);
    const bound=report.repair?.accepted?.full_check?.surface_correspondence?.whole_paired_surface_distance_upper_bound ?? report.repair?.accepted?.full_check?.correspondence?.distance_bound;
    text('third-detail',stage==='repaired'?(bound?`Paired surface separation ≤ ${format(bound)}`:'Paired exported surfaces checked in native run'):'Valid inputs; same declared omission family');
    const s=end?trace?.[end-1]:null;
    text('step-detail',s?`Step ${end} · operand ${s.operand===0?'A':'B'} · edge ${s.edge.join(' ↔ ')} · ${s.choice} · query ${s.native_query}`:'State 0 · original imported operands');
    text('input-note',stage==='witness'?'Drag to orbit · click a vertex for ancestry':'Drag to orbit · scroll to zoom · R to reset');
    text('output-note',stage==='witness'&&end<states.length-1?'Intermediate output surfaces were not stored. Final witness output is available at the last state.':'Orange wire shows the MANIFOLD comparison surface');
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
    const scale=Math.min(w*.82,h*.78)*camera.zoom, project=p=>{const q=transform(p);return [w/2+q[0]*scale,h/2-q[1]*scale,q[2]];};
    ctx.strokeStyle='#dbe4df';ctx.lineWidth=.6;
    for(let i=-5;i<=5;i++){const q=i/10;for(const ps of [[[-.5,-.55,q],[.5,-.55,q]],[[q,-.55,-.5],[q,-.55,.5]]]){const pts=ps.map(p=>project(p.map((x,k)=>x*span+center[k])));ctx.beginPath();ctx.moveTo(...pts[0].slice(0,2));ctx.lineTo(...pts[1].slice(0,2));ctx.stroke();}}
    if (!meshes) {ctx.fillStyle='#52666c';ctx.textAlign='center';ctx.font='12px ui-monospace,monospace';ctx.fillText('No stored output for this state',w/2,h/2);return;}
    const polygons=[];
    meshes.forEach(({mesh,color,wire,side})=>{
      if(!meshOK(mesh))return;
      const pts=mesh.vertices.map(project);
      mesh.faces.forEach(f=>{const pp=f.map(i=>pts[i]);const a=pp[0],b=pp[1],c=pp[2],u=b.map((v,k)=>v-a[k]),v=c.map((vv,k)=>vv-a[k]),nn=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],normal=Math.hypot(...nn);const light=normal?Math.abs(nn[2])/normal:0;polygons.push({pp,color,wire,depth:pp.reduce((s,p)=>s+p[2],0)/3,light});});
      if(canvas.id==='input'&&stage==='witness') pts.forEach((p,index)=>picks.push({x:p[0],y:p[1],side,index,ancestry:mesh.ancestry?.[index]}));
      const accepted=report.status==='repaired' ? report.repair?.accepted : null, ids=stage==='repaired'&&side===accepted?.intervention.side?accepted.cluster:stage==='witness'&&selected&&selected.side===side?[selected.index]:[];
      for(const id of ids){if(!pts[id])continue;const p=pts[id];ctx.beginPath();ctx.arc(p[0],p[1],4,0,Math.PI*2);ctx.strokeStyle='#d46b23';ctx.lineWidth=1.7;ctx.stroke();}
    });
    polygons.sort((a,b)=>a.depth-b.depth);
    for(const p of polygons){ctx.beginPath();p.pp.forEach((q,i)=>i?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]));ctx.closePath();if(!p.wire){ctx.globalAlpha=.21+.32*p.light;ctx.fillStyle=p.color;ctx.fill();}ctx.globalAlpha=p.wire?.58:.65;ctx.strokeStyle=p.color;ctx.lineWidth=p.wire?.7:.8;ctx.stroke();}ctx.globalAlpha=1;
    // Markers must be painted after triangles to remain visible.
    if(canvas.id==='input'&&stage==='witness'){for(const p of picks){ctx.beginPath();ctx.arc(p.x,p.y,2.2,0,Math.PI*2);ctx.fillStyle=p.side?'#2456dc':'#0b947d';ctx.fill();}}
  }
  function draw(){if(!report)return;picks=[];render($('input'),activePair().map((mesh,side)=>({mesh,side,color:side?'#2456dc':'#0b947d'})));const o=outputPair();render($('output'),o?[{mesh:o.FLOAT,color:'#2456dc',side:0},...($('reference').checked&&meshOK(o.MANIFOLD)?[{mesh:o.MANIFOLD,color:'#d46b23',wire:true}]:[])]:null);}
  for(const canvas of canvases){let drag=null;
    canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{if(!drag)return;camera.yaw+=(e.clientX-drag.x)*.008;camera.pitch=Math.max(-1.45,Math.min(1.45,camera.pitch+(e.clientY-drag.y)*.008));drag.x=e.clientX;drag.y=e.clientY;draw();});
    canvas.addEventListener('pointerup',e=>{if(drag&&canvas.id==='input'&&stage==='witness'&&Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<4){const b=canvas.getBoundingClientRect(),x=e.clientX-b.left,y=e.clientY-b.top;const hit=picks.map(p=>({...p,d:Math.hypot(p.x-x,p.y-y)})).filter(p=>p.d<12).sort((a,b)=>a.d-b.d)[0];if(hit){selected=hit;text('selection',`Operand ${hit.side?'B':'A'} v${hit.index} consumes original source indices: ${hit.ancestry?.cluster?.join(', ') ?? 'not recorded'}. Clusters track contractions; they are not exact affine coordinates after native rounding.`);draw();}}drag=null;});
    canvas.addEventListener('pointercancel',()=>{drag=null;});
    canvas.addEventListener('wheel',e=>{e.preventDefault();camera.zoom=Math.max(.3,Math.min(4,camera.zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});
    canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','r','R'].includes(e.key)){e.preventDefault();if(e.key==='ArrowLeft')camera.yaw-=.1;if(e.key==='ArrowRight')camera.yaw+=.1;if(e.key==='ArrowUp')camera.pitch-=.1;if(e.key==='ArrowDown')camera.pitch+=.1;if(e.key.toLowerCase()==='r'){camera.yaw=.55;camera.pitch=-.30;camera.zoom=1;}draw();}});
  }
  document.querySelectorAll('[data-stage]').forEach(b=>b.addEventListener('click',()=>{stage=b.dataset.stage;selected=null;update();}));
  $('step').addEventListener('input',()=>{if(stage==='witness'){selected=null;update();}else{const n=Number($('step').value),s=report?.reduction?.accepted_steps[n-1];text('step-detail',s?`Step ${n} · operand ${s.operand===0?'A':'B'} · edge ${s.edge.join(' ↔ ')} · ${s.choice}`:'State 0 · original imported operands');}});
  $('trace-view').addEventListener('click',()=>{stage='witness';selected=null;update();});
  $('reference').addEventListener('change',draw);window.addEventListener('resize',draw);
  function download(name,contents,type='application/json'){const url=URL.createObjectURL(new Blob([contents],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  $('download-json').addEventListener('click',()=>{if(report)download('solidrift-report.json',JSON.stringify(report,null,2)+'\n');});
  $('download-input').addEventListener('click',()=>{if(!report)return;activePair().forEach((m,i)=>download(`solidrift-${stage}-${i?'B':'A'}.obj`,'# Solidrift displayed geometry; native binary32 coordinates\n'+m.vertices.map(v=>'v '+v.join(' ')).join('\n')+'\n'+m.faces.map(f=>'f '+f.map(i=>i+1).join(' ')).join('\n')+'\n','text/plain'));});
  function fail(e){$('error').hidden=false;text('error',`${e.message} ${report?'The previous report remains displayed.':''}`);}
  $('file').addEventListener('change',async()=>{const f=$('file').files[0];if(!f)return;try{if(f.size>cap)throw Error('Report exceeds the 10 MiB viewer limit.');load(JSON.parse(await f.text()));}catch(e){fail(e);}finally{$('file').value='';}});
  (async()=>{try{const embedded=$('solidrift-data').textContent.trim();if(embedded!=='__SOLIDRIFT_DATA__')load(JSON.parse(embedded));else{const response=await fetch('demo/report.json');if(!response.ok)throw Error('Could not load the demo report. Open a report JSON or use the CLI offline HTML export.');const body=await response.text();if(body.length>cap)throw Error('Demo exceeds report limit.');load(JSON.parse(body));}}catch(e){fail(e);}})();
})();
