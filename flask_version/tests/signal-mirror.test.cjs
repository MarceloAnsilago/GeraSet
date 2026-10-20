const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({document:{addEventListener(){}}});
for (const file of ['signal.js','signal-mirror.js','import.js']) vm.runInContext(fs.readFileSync(path.join(__dirname,'../static',file),'utf8'),context);
const base={operator:'Se',target:'Indicador 1: RSI',targetCandle:'Anterior',comparison:'Menor que',reference:'Indicador 1: RSI Nível inferior',referenceCandle:'N.usar',fixed:'0',distance:'0',usage:'Entrada',normalSide:'Compra',sense:'Normal'};
test('RSI swaps inferior/superior and directional crossings without changing purpose, candle or distance',()=>{
 const result=context.mirrorBuyRule(base).rule;
 assert.equal(result.reference,'Indicador 1: RSI Nível superior');assert.equal(result.comparison,'Maior que');assert.equal(result.normalSide,'Venda');
 assert.equal(result.targetCandle,'Anterior');assert.equal(result.usage,'Entrada');assert.equal(base.reference,'Indicador 1: RSI Nível inferior');
 const crossed=context.mirrorBuyRule({...base,comparison:'Cruzar&fechar abaixo de',usage:'Saída',distance:'2'}).rule;
 assert.equal(crossed.comparison,'Cruzar&fechar acima de');assert.equal(crossed.usage,'Saída');assert.equal(crossed.distance,'2');
 assert.equal(context.mirrorBuyRule({...base,reference:'Indicador 1: RSI Nível médio'}).rule.reference,'Indicador 1: RSI Nível médio');
});
test('ADX strength stays unchanged while DI lines exchange roles, not the comparator',()=>{
 const filter=context.mirrorBuyRule({...base,target:'Indicador 3: ADX',reference:'Valor fixo',comparison:'Maior que',fixed:'20'});
 assert.equal(filter.directional,false);assert.equal(filter.rule.comparison,'Maior que');assert.equal(filter.rule.fixed,'20');
 const di=context.mirrorBuyRule({...base,target:'Indicador 3: ADX +DI',reference:'Indicador 3: ADX −DI',comparison:'Maior que'});
 assert.equal(di.rule.target,'Indicador 3: ADX −DI');assert.equal(di.rule.reference,'Indicador 3: ADX +DI');assert.equal(di.rule.comparison,'Maior que');assert.equal(di.directional,true);
});
test('fixed RSI, mixed scales and intrabar touch require explicit review and cannot export',()=>{
 for (const change of [{reference:'Valor fixo',fixed:'35'},{reference:'Indicador 2: ADX'},{comparison:'Toque',targetCandle:'Vela atual'}]) {
  const result=context.mirrorBuyRule({...base,...change}).rule;
  assert.equal(result.comparison,'N.usar');assert.ok(result.mirrorNote);assert.ok(context.signalRuleErrors(result,'N.usar').length);
 }
});
test('price/MA direction mirrors with high/low counterparts',()=>{
 const result=context.mirrorBuyRule({...base,target:'Fechamento da vela',reference:'Indicador 1: Média Móvel',referenceCandle:'Anterior'}).rule;
 assert.equal(result.comparison,'Maior que');assert.equal(result.reference,'Indicador 1: Média Móvel');
 assert.equal(context.mirrorBuyRule({...base,target:'Máxima da vela',reference:'Mínima do dia'}).rule.target,'Mínima da vela');
});
test('current native inputs must preserve exact rule positions, values and management policy',()=>{
 const expected=new Map([['InpSignal1','1,0,1,10,1,0,9,0,30,0,0'],['InpSignal6','1,1,-1,13,1,1,9,0,70,0,0'],['InpPendingMirrorSell','true']]);
 context.validateSetupInputs(new Map(expected),expected);
 const changed=new Map(expected);changed.set('InpPendingMirrorSell','false');assert.throws(()=>context.validateSetupInputs(changed,expected));
 const moved=new Map(expected);moved.set('InpSignal2',moved.get('InpSignal6'));moved.delete('InpSignal6');assert.throws(()=>context.validateSetupInputs(moved,expected));
});




test('overwrite requires inline confirmation, cancel preserves sale, and ambiguous rules require valid explicit review',()=>{
 const listeners=[];
 const root={querySelectorAll:()=>[],querySelector:()=>({closest:()=>({querySelector:()=>({value:'Entrada'})})}),addEventListener:(name,fn)=>listeners.push(fn)};
 const button=()=>({handlers:{},addEventListener(name,fn){this.handlers[name]=fn;},click(){this.handlers.click();}});
 const rows=Array.from({length:10},(_,i)=>{
  const values=new Map();
  for(const key of ['operator','target','target-candle','comparison','reference','reference-candle','distance','normal-side','sense','fixed']) values.set(key,{value:key==='distance'||key==='fixed'?'0':key==='normal-side'?(i<5?'Compra':'Venda'):key==='sense'?'Normal':'N.usar'});
  const parts={'[data-mirror-note]':{value:''},'.signal-mirror-warning':{hidden:true},'[data-mirror-message]':{textContent:''},'[data-mirror-reviewed]':button()};
  const row={dataset:{signalSide:i<5?'Compra':'Venda'},closest:()=>root,querySelector:s=>parts[s]||values.get(/name\$="-([^"]+)"/.exec(s)[1])};
  parts['[data-mirror-reviewed]'].closest=()=>row;
  return row;
 });
 const controls={'[data-unit-selector]':{value:'N.usar'},'[data-mirror-source]':{value:''},'[data-mirror-status]':{textContent:''},'[data-mirror-confirm]':{hidden:true},'[data-mirror-buy]':button(),'[data-mirror-replace]':button(),'[data-mirror-cancel]':button()};
 const card={closest:()=>root,querySelector:s=>controls[s],dispatchEvent:()=>listeners.forEach(fn=>fn()),querySelectorAll:s=>s==='[data-signal-tab]'?[]:s==='[data-mirror-reviewed]'?rows.map(r=>r.querySelector(s)):s==='.condition-row'?rows:rows.filter(r=>s.includes(`"${r.dataset.signalSide}"`))};
 context.document.querySelector=()=>card;context.Event=class {};
 context.writeSignalBankRow(rows[0],{...base,reference:'Valor fixo',fixed:'35'});
 context.writeSignalBankRow(rows[5],{...base,normalSide:'Venda',comparison:'Maior que'});
 let policy={};context.setupStorageKey='test';context.readSetupState=()=>JSON.parse(JSON.stringify(policy));
 context.localStorage={setItem(key,value){policy=JSON.parse(value);}};
 context.bindSignalBanks();
 controls['[data-mirror-buy]'].click();assert.equal(controls['[data-mirror-confirm]'].hidden,false);
 controls['[data-mirror-cancel]'].click();assert.equal(context.readSignalRow(rows[5]).reference,base.reference);assert.equal(policy.pendingMirrorSell,undefined);
 controls['[data-mirror-buy]'].click();controls['[data-mirror-replace]'].click();assert.equal(policy.pendingMirrorSell,true);
 let sale=context.readSignalRow(rows[5]);assert.equal(sale.fixed,'35');assert.equal(sale.comparison,'N.usar');assert.ok(sale.mirrorNote);
 rows[5].querySelector('[data-mirror-reviewed]').click();assert.ok(context.readSignalRow(rows[5]).mirrorNote);
 rows[5].querySelector('[name$="-comparison"]').value='Maior que';
 rows[5].querySelector('[data-mirror-reviewed]').click();assert.equal(context.readSignalRow(rows[5]).mirrorNote,'');
 rows[0].querySelector('[name$="-fixed"]').value='40';listeners.forEach(fn=>fn());
 assert.match(controls['[data-mirror-status]'].textContent,/alterados após/);
});
