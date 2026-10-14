// Execute the real viewer against a small synthetic report to test failed-run
// authority. These DOM stubs test controls/labels, not rendering or mesh validity.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../solidrift/web/app.js'),'utf8');
const mesh={name:'test',vertices:[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],faces:[[0,2,1],[0,1,3],[0,3,2],[1,2,3]],ancestry:[0,1,2,3].map(i=>({cluster:[i],weights:{[i]:1}}))};
const report={schema_version:1,baseline:{inputs:{A:mesh,B:mesh},outputs:{FLOAT:mesh,MANIFOLD:mesh}},reduction:{original_operands:[mesh,mesh],operands:[mesh,mesh],accepted_steps:[],final_outputs:{FLOAT:mesh,MANIFOLD:mesh}},repair:{accepted:{full_repaired:[mesh,mesh],undo_inputs:[mesh,mesh],full_check:{output_geometry:mesh,reference_geometry:mesh},intervention:{side:0,vertices:[0,1,2],delta:[0,0,0]},cluster:[0,1,2]}}};
for(const status of ['repaired','error','timeout','cancelled','running','witness','no_failure']){
 const r=structuredClone(report);r.status=status;
 const ids={},buttons=['original','witness','repaired','undo'].map(s=>element(s));
 function element(stage){return {dataset:{stage},textContent:'',hidden:false,disabled:false,style:{},value:'0',checked:true,
  children:[],listeners:{},classList:{toggle(){}},setAttribute(){},replaceChildren(){this.children=[]},append(e){this.children.push(e)},
  addEventListener(name,fn){this.listeners[name]=fn},getBoundingClientRect(){return {width:500,height:300,left:0,top:0}},
  getContext(){return new Proxy({},{get:()=>()=>{},set:()=>true})},setPointerCapture(){}}}
 function get(id){return ids[id]??=Object.assign(element(),{id});}
 get('solidrift-data').textContent=JSON.stringify(r);
 const document={getElementById:get,querySelectorAll:()=>buttons,querySelector:s=>buttons.find(b=>s.includes('"'+b.dataset.stage+'"')),createElement:()=>element()};
 vm.runInNewContext(source,{document,window:{addEventListener(){}},devicePixelRatio:1,console,JSON,Number,Math,Error,Set,URL,Blob,setTimeout});
 if(status==='repaired'){
  assert.equal(buttons[2].disabled,false);assert.equal(buttons[3].disabled,false);assert.equal(ids['patch-vertices'].children.length,3);
 }else{
  assert.equal(buttons[2].disabled,true,status);assert.equal(buttons[3].disabled,true,status);assert.equal(ids['patch-vertices'].children.length,0,status);
  if(['error','timeout','cancelled','running'].includes(status))assert.match(ids['receipt-title'].textContent,/Incomplete/);
 }
}
console.log('PASS: 7 completed/partial status controls; partial accepted payload never enables repair or undo.');
