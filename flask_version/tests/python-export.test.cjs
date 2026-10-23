const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,'../static/python-export.js'),'utf8');
function environment({equivalent = true, failure} = {}) {
    const calls = [], downloads = [], status = {};
    const button = {disabled:false, addEventListener(_,fn){this.click=fn;}};
    const oldButton = {disabled:false};
    const roots = new Map(['inicio','indicadores','gestao','configuracoes'].map(page => [page,{querySelector:()=>({})}]));
    const bytes = Uint8Array.from([255,254,65,0]);
    const context = vm.createContext({Uint8Array, btoa:value=>Buffer.from(value,'binary').toString('base64'),
        document:{addEventListener(){},querySelector:selector=>({'[data-python-export]':button,'[data-python-export-status]':status,'[data-export-set]':oldButton})[selector]},
        DOMParser:class {parseFromString(page){return roots.get(page);}},
        serializeSetupSet:()=>({filename:'Teste.set',contents:bytes}), downloadSetupSet:file=>downloads.push(file),
        fetch:async (url,options={})=>{
            calls.push({url,options});
            if(url===failure)throw new Error('Serviço indisponível');
            if(!url.startsWith('/strategies'))return {ok:true,text:async()=>url.slice(1)};
            if(url.endsWith('/session'))return {ok:true,json:async()=>({data:{csrf:'csrf-token'}})};
            if(url.endsWith('/compare'))return {ok:true,json:async()=>({data:{equivalent,differences:equivalent?[]:[{input:'InpLot'}],
                configuration:{strategy:{schema_version:'1.0',name:'Teste'},warnings:[{message:'Não validado financeiramente.'}]},export_options:{tester_auto_start:false}}})};
            return {ok:true,arrayBuffer:async()=>bytes.buffer};
        },
    });
    vm.runInContext(source,context);
    context.bindPythonExport();
    return {calls,downloads,status,button,oldButton};
}

test('Python export compares before download and keeps the original action independent',async()=>{
    const env=environment();await env.button.click();
    assert.equal(env.downloads.length,1);
    assert.equal(env.downloads[0].filename,'Teste.set');
    const compareIndex=env.calls.findIndex(call=>call.url==='/strategies/compare');
    const exportIndex=env.calls.findIndex(call=>call.url==='/strategies/export');
    assert.ok(compareIndex<exportIndex);
    const request=env.calls[exportIndex].options;
    assert.equal(request.headers['X-GeraSet-Strategy-CSRF'],'csrf-token');
    const body=JSON.parse(request.body);
    assert.equal(body.strategy.schema_version,'1.0');
    assert.ok(body.legacy_set_base64);
    assert.match(env.status.textContent,/equivalentes/);
    assert.equal(env.oldButton.disabled,false);
    assert.equal(env.button.disabled,false);
});

test('mismatched native parameters block the new export without falling back silently',async()=>{
    const env=environment({equivalent:false});await env.button.click();
    assert.equal(env.downloads.length,0);
    assert.ok(!env.calls.some(call=>call.url==='/strategies/export'));
    assert.match(env.status.textContent,/InpLot/);
    assert.equal(env.oldButton.disabled,false);
});

test('Python unavailable does not disable or replace the legacy exporter',async()=>{
    const env=environment({failure:'/strategies/compare'});await env.button.click();
    assert.equal(env.downloads.length,0);
    assert.match(env.status.textContent,/indisponível/);
    assert.equal(env.oldButton.disabled,false);
    assert.equal(env.button.disabled,false);
});
