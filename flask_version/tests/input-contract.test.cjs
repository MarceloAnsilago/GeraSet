const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const contract = JSON.parse(fs.readFileSync(path.join(__dirname, '../../mt5_bridge/contracts/uni_inputs.json'), 'utf8'));
const c = vm.createContext({document: {addEventListener() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/export.js'), 'utf8'), c);
const controls = values => Object.entries(values).map(([key, value]) => ({key, value}));
function assertEnum(line, key, expected) {
    assert.equal(line.split('=')[0], key);
    const value = Number(line.split('=')[1].split('||')[0]);
    assert.equal(value, expected);
    assert.ok(Object.values(contract[key].enum_values).includes(value));
}

test('operation mappings preserve the MQL enum values', () => {
    const enums = vm.runInContext('operationEnums', c);
    const mapping = {setup_market: 'InpMarket', setup_mode: 'InpTradeMode', setup_direction: 'InpDirection'};
    for (const [field, key] of Object.entries(mapping)) {
        assert.deepEqual(Object.values(enums[field]), Object.values(contract[key].enum_values));
    }
    const result = Array.from(c.operationSetLines(controls({setup_market: 'B3', setup_mode: 'Swing trade',
        setup_lot: '1', setup_direction: 'Somente venda',
        'operation-direction-start': 'Compra e venda', 'operation-direction-end': 'Somente venda'})));
    for (const [key, value] of [['InpMarket', 1], ['InpTradeMode', 1], ['InpDirection', 2]])
        assertEnum(result.find(line => line.startsWith(key+'=')), key, value);
});

test('OHLC references preserve all enum values rather than their labels', () => {
    for (const [index, label] of ['Máxima', 'Mínima', 'Abertura', 'Fechamento'].entries()) {
        const lines = c.orderSetLines(controls({order_mode: 'Pendente', pending_reference: label, pending_bar: '1',
            'pending-reference-start': label, 'pending-reference-end': label,
            'pending-bar-start': '0', 'pending-bar-step': '0', 'pending-bar-end': '0'}));
        assertEnum(lines[0], 'InpOrderMode', 1);
        assertEnum(lines[1], 'InpPendingReference', index);
        assert.equal(contract.InpPendingCandle.default, 1);
    }
});

test('management units and disabled defaults match Uni', () => {
    for (const [mode, label] of ['Desativado', 'Pontos', 'Porcentagem'].entries()) {
        const lines = c.breakevenSetLines(controls({'breakeven-mode': label, 'breakeven-trigger': '100',
            'breakeven-offset': '20', ...Object.fromEntries(['activate', 'distance'].flatMap(k =>
                ['start', 'step', 'end'].map(b => [`breakeven-${k}-${b}`, '0'])))}));
        assertEnum(lines[0], 'InpBreakevenMode', mode);
    }
    assert.equal(contract.InpBreakevenMode.default, 0);
    assert.equal(contract.InpBreakevenTrigger.unit, 'InpBreakevenMode: points or percent_of_entry_price');
    assert.equal(contract.InpEntryStart.unit, 'server_minutes_since_midnight');
    assert.equal(contract.InpEntryStart.multiple_of, 5);
    // Only indicator slots use contiguous indexes. They are not MT5 PERIOD_* codes.
    assert.equal(contract.InpIndicator1Timeframe.enum_values.UNI_SLOT_H1, 12);
    assert.equal(contract.InpIndicator1Timeframe.default, 0);
    assert.equal(contract.InpRsiEntryPrice.enum_values.UNI_PRICE_CLOSE, 1);
    assert.equal(contract.InpIndicator1MaMethod.enum_values.UNI_MA_EMA, 1);
    assert.equal(contract.InpTakeMode.default, -1); // native legacy inference
    assert.equal(contract.InpTakeMode.enum_values.UNI_TAKE_STOP, 0); // explicit GeraSet choice
});
