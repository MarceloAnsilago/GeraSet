const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const dom={addEventListener(){},createElement(tag){return {tag,children:[],setAttribute(key,value){this[key]=value;},append(...items){this.children.push(...items);},appendChild(item){this.children.push(item);}};}};
const ctx=vm.createContext({document:dom});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/bridge.js'),'utf8'),ctx);
test('shows MT5 percentage, elapsed time and expected combinations',()=>{
    const view=ctx.renderBridgeProgress({state:'running',elapsed_seconds:1810,percent:14,total_passes:10000});
    assert.equal(view.children[1].value,14);
    assert.match(view.children[0].textContent,/30min 10s.*14%/);
    assert.match(view.children[3].textContent,/10\.000/);
});
test('unknown progress is indeterminate, zero is determinate, failure preserves last percent',()=>{
    const view=data=>ctx.renderBridgeProgress({state:'running',...data});
    assert.equal('value' in view({percent:null}).children[1],false);
    assert.equal(view({percent:0}).children[1].value,0);
    const failed=view({state:'failed',percent:14});
    assert.equal(failed.children[1].value,14);
    assert.match(failed.children[2].textContent,/encerrada em 14%/);
    assert.equal(view({state:'failed',percent:null}).children[1].value,0);
    assert.equal(view({state:'completed',percent:14}).children[1].value,100);
    assert.equal('value' in view({percent:150}).children[1],false);
});
