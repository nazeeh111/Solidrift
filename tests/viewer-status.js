// Execute the real viewer against a small synthetic report to test failed-run
// authority. These DOM stubs test controls/labels, not rendering or mesh validity.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../solidrift/web/app.js'),'utf8');
const mesh={name:'test',vertices:[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],faces:[[0,2,1],[0,1,3],[0,3,2],[1,2,3]],ancestry:[0,1,2,3].map(i=>({cluster:[i],weights:{[i]:1}}))};
const report={schema_version:1,baseline:{inputs:{A:mesh,B:mesh},outputs:{FLOAT:mesh,MANIFOLD:mesh}},reduction:{original_operands:[mesh,mesh],operands:[mesh,mesh],accepted_steps:[],final_outputs:{FLOAT:mesh,MANIFOLD:mesh}},repair:{accepted:{full_repaired:[mesh,mesh],undo_inputs:[mesh,mesh],undo_signature:{geometry:mesh},full_check:{output_geometry:mesh,reference_geometry:mesh},intervention:{side:0,vertices:[0,1,2],delta:[0,0,0]},cluster:[0,1,2]}}};
for(const status of ['repaired','error','timeout','cancelled','running','witness','no_failure']){
 const r=structuredClone(report);r.status=status;
 if(status==='no_failure'){delete r.reduction;delete r.repair;}
 const ids={},buttons=['original','witness','repaired','undo'].map(s=>element(s)),workbench=element();
 function element(stage){return {dataset:{stage},textContent:'',hidden:false,disabled:false,style:{},value:'0',checked:true,
  children:[],lastChild:{textContent:' Witness'},listeners:{},classList:{toggle(){}},setAttribute(){},replaceChildren(){this.children=[]},append(e){this.children.push(e)},
  addEventListener(name,fn){this.listeners[name]=fn},getBoundingClientRect(){return {width:500,height:300,left:0,top:0}},
  getContext(){return new Proxy({},{get:()=>()=>{},set:()=>true})},setPointerCapture(){}}}
 function get(id){return ids[id]??=Object.assign(element(),{id});}
 get('solidrift-data').textContent=JSON.stringify(r);
 const document={getElementById:get,querySelectorAll:()=>buttons,querySelector:s=>s==='.workbench'?workbench:buttons.find(b=>s.includes('"'+b.dataset.stage+'"')),createElement:()=>element()};
 vm.runInNewContext(source,{document,window:{addEventListener(){}},devicePixelRatio:1,console,JSON,Number,Math,Error,Set,URL,Blob,setTimeout});
 if(['repaired','witness'].includes(status)){
  assert.match(ids['case-orientation'].textContent,/union should combine both solids.*returns A and drops B/);
  assert.equal(buttons[1].lastChild.textContent.trim(),'Witness');
  assert.match(ids['case-lead'].textContent,/recorded witness/);
  assert.doesNotMatch(ids['case-lead'].textContent,/did not finish/);
  assert.equal(ids['output-title'].textContent,'Observed / B missing (FLOAT)');
  assert.equal(ids.fault.textContent,'Operand B omitted');
  assert.equal(ids['third-detail'].textContent,'Valid inputs; same declared omission family');
 }
 else assert.doesNotMatch(ids['case-orientation'].textContent,/drops B/);
 if(status==='repaired'){
  assert.equal(buttons[2].disabled,false);assert.equal(buttons[3].disabled,false);assert.equal(ids['patch-vertices'].children.length,3);
  assert.equal(ids['vertex-inspector'].hidden,true);
  assert.doesNotThrow(()=>buttons[1].listeners.click(),'witness with reference overlay and no selected vertex');
  assert.equal(ids['vertex-inspector'].hidden,false);
  assert.match(ids.selection.textContent,/Operand A v0 consumes original source indices: 0/);
  ids['vertex-side'].value='1';ids['vertex-side'].listeners.change();
  ids['vertex-index'].value='3';ids['vertex-index'].listeners.input();
  assert.match(ids.selection.textContent,/Operand B v3 consumes original source indices: 3/);
  assert.equal(ids['vertex-index'].max,'3');
  ids['vertex-index'].value='99';ids['vertex-index'].listeners.input();
  assert.match(ids.selection.textContent,/Enter a whole vertex index from 0 to 3/);
  ids['vertex-index'].value='';ids['vertex-index'].listeners.input();
  assert.match(ids.selection.textContent,/Enter a whole vertex index/);
  ids['vertex-index'].value='2';ids['vertex-index'].listeners.input();
  assert.match(ids.selection.textContent,/Operand B v2 consumes original source indices: 2/);
  ids.step.listeners.input();
  assert.match(ids.selection.textContent,/Operand A v0/);
  assert.equal(ids['triangles'].textContent,8);
  assert.doesNotThrow(()=>buttons[2].listeners.click(),'repaired native surfaces');
  assert.equal(ids['vertex-inspector'].hidden,true);
  assert.match(ids.selection.textContent,/Choose Witness/);
  assert.doesNotThrow(()=>buttons[3].listeners.click(),'restored native surfaces');
 }else{
  assert.equal(buttons[2].disabled,true,status);assert.equal(buttons[3].disabled,true,status);assert.equal(ids['patch-vertices'].children.length,0,status);
  if(['error','timeout','cancelled','running'].includes(status)){
   assert.match(ids['receipt-title'].textContent,/Incomplete/);
   assert.match(ids['case-lead'].textContent,/no witness or repair is claimed/);
   assert.equal(buttons[1].disabled,false,'partial stored geometry remains inspectable');
   assert.equal(buttons[1].lastChild.textContent.trim(),'Partial');
   assert.match(ids.selection.textContent,/Choose Partial/);
   assert.equal(ids['input-title'].textContent,'Recorded input solids / A + B');
   assert.equal(ids['output-title'].textContent,'FLOAT / partial baseline output');
   assert.equal(ids.fault.textContent,'Incomplete native run');
   assert.equal(ids.fault.style.color,'var(--muted)');
   assert.equal(ids['third-label'].textContent,'STORED INPUT COUNTS');
   assert.equal(ids.third.textContent,'8 → 8');
   assert.equal(ids['step-count'].textContent,'0 stored contractions');
   assert.match(ids['third-detail'].textContent,/no completed reduction is claimed/);
   assert.doesNotThrow(()=>buttons[1].listeners.click());
   assert.equal(ids['vertex-inspector'].hidden,false);
   assert.equal(ids['input-title'].textContent,'Stored inputs · state 0');
   assert.equal(ids['output-title'].textContent,'Native output / partial record');
   assert.equal(ids.fault.textContent,'Incomplete native run');
   assert.match(ids.selection.textContent,/Operand A v0 consumes original source indices: 0/);
   assert.equal(buttons[2].disabled,true);assert.equal(buttons[3].disabled,true);
  }
  if(status==='no_failure'){
   assert.equal(ids['output-title'].textContent,'FLOAT / recorded output');
   assert.equal(ids['fault'].textContent,'No target omission');
   assert.equal(ids['third'].textContent,'—');
   assert.match(ids['case-headline'].textContent,/No target omission/);
   assert.doesNotMatch(ids['case-lead'].textContent,/full-model intervention/);
  }
 }
}
console.log('PASS: 7 status controls, bounded keyboard ancestry and completed/partial geometry labels; partial stored geometry stays inspectable without enabling repair or undo.');
