const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({document: {addEventListener() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/export.js'), 'utf8'), context);
function lines(overrides = {}) {
    const values = {order_mode: 'Pendente', pending_reference: 'Fechamento', pending_bar: '3',
        'pending-reference-start': 'Máxima', 'pending-reference-end': 'Máxima',
        'pending-bar-start': '0', 'pending-bar-step': '0', 'pending-bar-end': '0', ...overrides};
    return Array.from(context.orderSetLines(Object.entries(values).map(([key, value]) => ({key, value}))));
}
test('order exports fixed values independently of optimization bounds', () => {
    assert.deepEqual(lines(), ['InpOrderMode=1||1||1||1||N', 'InpPendingReference=3||0||1||0||N', 'InpPendingCandle=3||3||1||3||N']);
    const result = lines({'pending-reference-start': 'Fechamento', 'pending-reference-end': 'Mínima', 'pending-bar-start': '1', 'pending-bar-step': '2', 'pending-bar-end': '9'});
    assert.ok(result.includes('InpPendingReference=3||1||1||3||Y'));
    assert.ok(result.includes('InpPendingCandle=3||1||2||9||Y'));
});
test('all OHLC references preserve Uni numeric values', () => {
    ['Máxima', 'Mínima', 'Abertura', 'Fechamento'].forEach((value, index) => assert.ok(lines({pending_reference: value})[1].startsWith(`InpPendingReference=${index}||`)));
});
test('market orders disable hidden pending optimization and ignore invalid hidden fields', () => {
    assert.deepEqual(lines({order_mode: 'A mercado', pending_bar: 'bad', 'pending-bar-step': 'bad'}), ['InpOrderMode=0||0||1||0||N', 'InpPendingReference=0||0||1||0||N', 'InpPendingCandle=1||1||1||1||N']);
});
test('invalid pending settings fail instead of silently using native defaults', () => {
    for (const values of [{order_mode: ''}, {pending_reference: 'Distância'}, {pending_bar: '0'}, {pending_bar: '1.5'}, {pending_bar: '100001'}, {'pending-bar-start': '1'}, {'pending-bar-start': '4', 'pending-bar-step': '1', 'pending-bar-end': '2'}])
        assert.throws(() => lines(values), {name: 'OrderValidationError'});
    assert.throws(() => context.orderSetLines([]), {name: 'OrderValidationError'});
});
test('cached templates retain their original unnamed order fields', () => {
    const result = context.orderSetLines([{key: 'gestao_0', value: 'A mercado'}]);
    assert.equal(result[0], 'InpOrderMode=0||0||1||0||N');
});
