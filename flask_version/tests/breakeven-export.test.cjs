const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const c=vm.createContext({document:{addEventListener(){}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/export.js'),'utf8'),c);
function lines(extra={}) {
 const values={'breakeven-mode':'Pontos','breakeven-trigger':'100','breakeven-offset':'20',...Object.fromEntries(['activate','distance'].flatMap(k=>['start','step','end'].map(b=>[`breakeven-${k}-${b}`,'0']))),...extra};
 return Array.from(c.breakevenSetLines(Object.entries(values).map(([key,value])=>({key,value}))));
}
test('BE exports native mode, trigger and protection, preserving decimal units',()=>{
 assert.deepEqual(lines(),['InpBreakevenMode=1||1||1||1||N','InpBreakevenTrigger=100||100||0.01||100||N','InpBreakevenOffset=20||20||0.01||20||N']);
 assert.equal(lines({'breakeven-mode':'Porcentagem','breakeven-trigger':'1,5','breakeven-offset':'0'})[1],'InpBreakevenTrigger=1.5||1.5||0.01||1.5||N');
});
test('disabled BE clears native values and ignores inactive invalid fields',()=>{
 assert.deepEqual(lines({'breakeven-mode':'Desativado','breakeven-trigger':'bad'}),['InpBreakevenMode=0||0||1||0||N','InpBreakevenTrigger=0||0||0.01||0||N','InpBreakevenOffset=0||0||0.01||0||N']);
});
test('BE validates values and all optimization combinations',()=>{
 for(const extra of [{'breakeven-trigger':'0'},{'breakeven-offset':'100'},{'breakeven-offset':'-1'},{'breakeven-trigger':'1.123'},{'breakeven-mode':'bad'},{'breakeven-activate-start':'10','breakeven-activate-step':'1','breakeven-activate-end':'30'}]) assert.throws(()=>lines(extra),{name:'BreakevenValidationError'});
 const result=lines({'breakeven-activate-start':'50','breakeven-activate-step':'10','breakeven-activate-end':'100'});
 assert.equal(result[1],'InpBreakevenTrigger=100||50||10||100||Y');
});
