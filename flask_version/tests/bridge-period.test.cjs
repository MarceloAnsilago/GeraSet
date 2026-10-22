const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const context=vm.createContext({document:{addEventListener(){}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/bridge-period.js'),'utf8'),context);
const dates=(period,date)=>JSON.parse(JSON.stringify(context.bridgePeriodDates(period,date)));
test('rolling periods respect calendar months and exclusive end',()=>{
    assert.deepEqual(dates('3',new Date(2026,9,22)),{from:'2026-07-22',to:'2026-10-22'});
    assert.deepEqual(dates('1',new Date(2024,2,31)),{from:'2024-02-29',to:'2024-03-31'});
    assert.deepEqual(dates('12',new Date(2024,1,29)),{from:'2023-02-28',to:'2024-02-29'});
});
test('full history requests the supported range; custom preserves user dates',()=>{
    assert.deepEqual(dates('all',new Date(2026,9,22)),{from:'1970-01-01',to:'2026-10-22'});
    assert.equal(context.bridgePeriodDates('custom'),null);
});
