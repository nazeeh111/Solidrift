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
  children:[],listeners:{},classList:{toggle(){}},setAttribute(){},replaceChildren(){this.children=[]},append(e){this.children.push(e)},
  addEventListener(name,fn){this.listeners[name]=fn},getBoundingClientRect(){return {width:500,height:300,left:0,top:0}},
  getContext(){return new Proxy({},{get:()=>()=>{},set:()=>true})},setPointerCapture(){}}}
 function get(id){return ids[id]??=Object.assign(element(),{id});}
 get('solidrift-data').textContent=JSON.stringify(r);
 const document={getElementById:get,querySelectorAll:()=>buttons,querySelector:s=>s==='.workbench'?workbench:buttons.find(b=>s.includes('"'+b.dataset.stage+'"')),createElement:()=>element()};
 vm.runInNewContext(source,{document,window:{addEventListener(){}},devicePixelRatio:1,console,JSON,Number,Math,Error,Set,URL,Blob,setTimeout});
 if(status==='repaired'){
  assert.equal(buttons[2].disabled,false);assert.equal(buttons[3].disabled,false);assert.equal(ids['patch-vertices'].children.length,3);
  // The comparison overlay has no operand side. Null vertex selection must
  // not match that undefined side and dereference selected.index.
  assert.doesNotThrow(()=>buttons[1].listeners.click(),'witness with reference overlay and no selected vertex');
  assert.equal(ids['triangles'].textContent,8);
  assert.doesNotThrow(()=>buttons[2].listeners.click(),'repaired native surfaces');
  assert.doesNotThrow(()=>buttons[3].listeners.click(),'restored native surfaces');
 }else{
  assert.equal(buttons[2].disabled,true,status);assert.equal(buttons[3].disabled,true,status);assert.equal(ids['patch-vertices'].children.length,0,status);
  if(['error','timeout','cancelled','running'].includes(status))assert.match(ids['receipt-title'].textContent,/Incomplete/);
  if(status==='no_failure'){
   assert.equal(ids['output-title'].textContent,'FLOAT / recorded output');
   assert.equal(ids['fault'].textContent,'No target omission');
   assert.equal(ids['third'].textContent,'—');
   assert.match(ids['case-headline'].textContent,/No target omission/);
   assert.doesNotMatch(ids['case-lead'].textContent,/full-model intervention/);
  }
 }
}
console.log('PASS: 7 status controls and witness/repair/undo rendering paths; partial accepted payload never enables repair or undo.');
