const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/import.js'), 'utf8');
function environment() {
    const button = {addEventListener(type, callback) { this[type] = callback; }};
    const input = {addEventListener(type, callback) { this[type] = callback; }, click() { this.clicked = true; }};
    const status = {};
    const writes = []; let reloads = 0;
    const context = vm.createContext({TextDecoder, Uint8Array,
        document: {addEventListener() {}, querySelector: selector => ({'[data-import-set]': button, '[data-import-file]': input, '[data-import-status]': status})[selector]},
        setupStorageKey: 'draft',
        localStorage: {setItem: (...args) => writes.push(args)},
        sessionStorage: {getItem() {}, removeItem() {}, setItem() {}},
        window: {location: {reload() { reloads++; }}},
    });
    vm.runInContext(source, context);
    return {context, button, input, status, writes, reloads: () => reloads};
}
function preset() {
    const metadata = {format: 'geraset', version: 1, pages: Object.fromEntries(['inicio', 'indicadores', 'gestao', 'configuracoes'].map(page => [page, [{key: 'field', value: '25'}]]))};
    return 'InpSignal1=1,0,1,11,1,0,9,0,25,0,0\r\n' + JSON.stringify(metadata, null, 2).split('\n').map(line => '; ' + line).join('\r\n');
}

test('reads UTF-16LE MT5 presets and UTF-8 with the same metadata and signal', () => {
    const {context} = environment();
    for (const bytes of [Buffer.from('\ufeff' + preset(), 'utf16le'), Buffer.from(preset(), 'utf8')]) {
        const parsed = context.parseSetupSet(context.decodeSetupSet(bytes));
        assert.equal(parsed.metadata.pages.indicadores[0].value, '25');
        assert.equal(parsed.native.get('InpSignal1'), '1,0,1,11,1,0,9,0,25,0,0');
    }
});

test('rejects native-only, truncated and unsupported metadata without executing comments', () => {
    const {context} = environment();
    for (const text of ['InpSignal1=abc', '; {\n; broken', preset().replace('"version": 1', '"version": 99'), preset().replace('"gestao": [', '"missing": [')]) {
        assert.throws(() => context.parseSetupSet(text));
    }
});

test('failed validation leaves the saved draft untouched and allows retry', async () => {
    const env = environment();
    env.context.prepareSetupImport = async () => { throw new Error('Invalid signal'); };
    env.context.bindSetImport();
    env.input.files = [{name: 'adx.set', size: 500, arrayBuffer: async () => Buffer.from(preset())}];
    await env.input.change();
    assert.equal(env.writes.length, 0); assert.equal(env.reloads(), 0);
    assert.match(env.status.textContent, /Invalid signal/); assert.equal(env.button.disabled, false);
    env.context.prepareSetupImport = async () => ({indicadores: [{value: '25'}]});
    await env.input.change();
    assert.equal(env.writes.length, 1); assert.equal(env.reloads(), 1);
});

test('canceling selection does not overwrite the draft', async () => {
    const env = environment(); env.context.bindSetImport();
    env.input.files = []; await env.input.change();
    assert.equal(env.writes.length, 0); assert.equal(env.reloads(), 0);
});
