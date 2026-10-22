const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/bridge.js'), 'utf8');

test('execution context distinguishes the symbol, base timeframe and date interval', () => {
    const c = vm.createContext({document: {addEventListener() {}}});
    vm.runInContext(source, c);
    assert.equal(c.bridgeExecutionContextText({symbol: ' WIN$ ', timeframe: 'H1', date_from: '2026-10-01', date_to: '2026-10-20'}),
        'Ativo: WIN$ · timeframe base: H1 · datas: 2026-10-01 a 2026-10-20 (fim exclusivo)');
    assert.match(c.bridgeExecutionContextText({}), /Ativo: não informado · timeframe base: não informado/);
});

test('changing next-test fields does not relabel the context of historical jobs', async () => {
    const handlers = {};
    const fields = Object.fromEntries(Object.entries({symbol: 'EURUSD', timeframe: 'M5', from: '2026-10-01', to: '2026-10-20', operation: 'backtest'})
        .map(([key, value]) => [key, {name: 'bridge-'+key, value, addEventListener() {}}]));
    const element = () => ({children: [], addEventListener() {}, appendChild(child) {this.children.push(child);},
        replaceChildren(...children) {this.children = children;}});
    const form = {querySelectorAll: () => Object.values(fields), addEventListener: (event, fn) => {handlers[event] = fn;}};
    const preview = element(), history = element();
    const parts = {'[data-bridge-form]': form, '[data-bridge-execution-context]': preview, '[data-bridge-history]': history};
    const card = {querySelector: selector => {
        const field = /^\[name="bridge-([^"]+)"\]$/.exec(selector)?.[1];
        return field ? fields[field] : (parts[selector] ||= element());
    }};
    const recorded = {id: 'previous-job', kind: 'backtest', state: 'completed',
        config: {setup_id: 'Mesmo setup', symbol: 'WIN$', timeframe: 'H1', date_from: '2026-09-01', date_to: '2026-09-30'}};
    const replies = {'/bridge/session': {csrf: 'test'}, '/bridge/status': {mt5: {ready: true}}, '/bridge/jobs': [recorded]};
    const c = vm.createContext({document: {addEventListener() {}, querySelector: () => card, createElement: element},
        localStorage: {getItem: () => null}, sessionStorage: {getItem: () => null, removeItem() {}}, window: {addEventListener() {}},
        fetch: async url => ({ok: true, headers: {get: () => 'application/json'}, json: async () => ({data: replies[url]})})});
    vm.runInContext(source, c);
    await c.bindBridge();
    assert.match(preview.textContent, /Próximo teste — Ativo: EURUSD · timeframe base: M5/);
    assert.match(history.children[0].textContent, /Ativo: WIN\$ · timeframe base: H1/);
    fields.symbol.value = 'GBPUSD'; fields.timeframe.value = 'M15'; handlers.change();
    assert.match(preview.textContent, /Ativo: GBPUSD · timeframe base: M15/);
    assert.match(history.children[0].textContent, /Ativo: WIN\$ · timeframe base: H1/);
});
