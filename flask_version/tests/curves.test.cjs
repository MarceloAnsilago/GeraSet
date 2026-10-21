const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ctx=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/curves.js'),'utf8'),ctx);
test('balance plot uses shared time and balance axes for every pass',()=>{
    const b=ctx.balanceCurveBounds([{points:[[10,10000],[20,10100]]},{points:[[5,10000],[30,9800]]}]);
    assert.equal(b.minX,5);assert.equal(b.maxX,30);assert.ok(b.minY<9800&&b.maxY>10100);
});
test('flat and empty curves do not cause invalid plot ranges',()=>{
    assert.equal(ctx.balanceCurveBounds([]),null);
    const b=ctx.balanceCurveBounds([{points:[[10,10000],[10,10000]]}]);
    assert.ok(b.maxX>b.minX&&b.maxY>b.minY);
});
