const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({document: {addEventListener() {}}});
for (const file of ['signal.js', 'export.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '../static', file), 'utf8'), context);
context.readSignalRow = row => row;

function fixture(rules = [], types = ['Média Móvel', 'RSI', 'ADX', 'Média Móvel']) {
    const fields = new Map();
    for (let slot = 1; slot <= 4; slot++) {
        const kind = types[slot - 1];
        fields.set(`[data-indicator-type="${slot}"]`, kind);
        fields.set(`[name="indicator-usage-${slot}"]:checked`, slot === 2 ? 'Saída' : 'Entrada');
        for (const [index, title, value] of (kind === 'RSI' ? [[1, 'Período', 14], [2, 'Sobrevenda', 30], [3, 'Sobrecompra', 70], [4, 'Nível médio', 50]] : [[1, 'Período', 14], [2, 'Shift', 0]])) {
            fields.set(`[id="param-${slot}-${kind}-${index}"]`, String(value));
            for (let i = 1; i <= 3; i++) fields.set(`[id="opt-${slot}-${kind}-${i}-${title}"]`, '0');
        }
        for (const [index, title, value] of [[1, 'Preço aplicado', 'Close'], [2, 'Método', 'EMA']]) {
            fields.set(`[id="combo-${slot}-${kind}-${index}"]`, value);
            for (const bound of ['start', 'end']) fields.set(`[name="opt-combo-${slot}-${kind}-${title}-${bound}"]`, value);
        }
    }
    return {fields, querySelector(selector) {
        if (selector === '[data-conditions]') return {querySelector: () => ({value: 'N.usar'}), querySelectorAll: () => rules};
        return fields.has(selector) ? {value: fields.get(selector)} : null;
    }};
}
const rule = {operator: 'Se', usage: 'Entrada', normalSide: 'Compra', sense: 'Normal', target: 'Indicador 1: Média Móvel', targetCandle: 'Vela atual', comparison: 'Toque', reference: 'Fechamento da vela', referenceCandle: 'Vela atual', fixed: '0', distance: '0'};

test('exports independent indicator parameters and entry/exit condition payloads', () => {
    const root = fixture([rule, {...rule, usage: 'Saída', target: 'Indicador 2: RSI', reference: 'Valor fixo', fixed: '70', sense: 'Inverter'}]);
    const lines = Array.from(context.indicatorSignalSetLines(root));
    assert.ok(lines.includes('InpIndicator2Exit=1||1||1||1||N'));
    assert.ok(lines.includes('InpIndicator2RsiPeriod=14||14||1||14||N'));
    assert.ok(lines.includes('InpIndicator3AdxPeriod=14||14||1||14||N'));
    assert.ok(lines.includes('InpSignal1=1,0,1,10,0,6,0,0,0,0,0'));
    assert.ok(lines.includes('InpSignal2=1,1,-1,13,0,6,9,0,70,0,0'));
    assert.ok(lines.includes('InpSignal5='));
});

test('all ADX buffers and closed candle offsets have stable wire values', () => {
    for (const [suffix, buffer] of [['', 0], [' +DI', 1], [' −DI', 2]]) {
        const lines = context.indicatorSignalSetLines(fixture([{...rule, target: `Indicador 3: ADX${suffix}`, targetCandle: 'Antepenúltima', reference: 'Valor fixo', fixed: '25'}]));
        assert.ok(lines.includes(`InpSignal1=1,0,1,${16 + buffer},3,6,9,0,25,0,0`));
    }
});

test('exports indicator optimization and rejects unavailable sources', () => {
    const root = fixture();
    for (const [i, value] of [[1, '10'], [2, '2'], [3, '20']]) root.fields.set(`[id="opt-2-RSI-${i}-Período"]`, value);
    assert.ok(context.indicatorSignalSetLines(root).includes('InpIndicator2RsiPeriod=14||10||2||20||Y'));
    assert.throws(() => context.indicatorSignalSetLines(fixture([{...rule, target: 'Indicador 1: ADX'}])), {name: 'SignalValidationError'});
});


test('RSI levels export as constants in both A and reference, preserving closed candles', () => {
    for (const [index, level] of ['superior', 'médio', 'inferior'].entries()) {
        const label = `Indicador 2: RSI Nível ${level}`;
        const rsi = {...rule, usage: 'Saída', target: 'Indicador 2: RSI', targetCandle: 'Anterior', comparison: 'Cruzar&fechar acima de', reference: label, referenceCandle: 'N.usar'};
        assert.ok(context.indicatorSignalSetLines(fixture([rsi])).includes(`InpSignal1=1,1,1,13,1,9,${25 + index},0,0,0,0`));
        assert.ok(context.indicatorSignalSetLines(fixture([{...rsi, target: label, targetCandle: 'N.usar', reference: 'Indicador 2: RSI', referenceCandle: 'Anterior'}])).includes(`InpSignal1=1,1,1,${25 + index},0,9,13,1,0,0,0`));
    }
});

test('RSI configurable decimal levels and optimization are exported and validated', () => {
    const root = fixture();
    root.fields.set('[id="param-2-RSI-3"]', '75.5');
    for (const [i, value] of [[1, '70'], [2, '0.5'], [3, '80']]) root.fields.set(`[id="opt-2-RSI-${i}-Sobrecompra"]`, value);
    const lines = context.indicatorSignalSetLines(root);
    assert.ok(lines.includes('InpIndicator2RsiUpper=75.5||70||0.5||80||Y'));
    assert.ok(lines.includes('InpIndicator2RsiMiddle=50||50||1||50||N'));
    assert.ok(lines.includes('InpIndicator2RsiLower=30||30||1||30||N'));
    root.fields.set('[id="param-2-RSI-4"]', '80');
    assert.throws(() => context.indicatorSignalSetLines(root), {name: 'SignalValidationError'});
});


test('only MA may repeat with the same purpose; other types allow one entry and one exit', () => {
    assert.doesNotThrow(() => context.indicatorSignalSetLines(fixture([], Array(4).fill('Média Móvel'))));
    for (const type of ['RSI', 'ADX']) {
        const root = fixture([], [type, type, 'Não usar', 'Não usar']);
        assert.doesNotThrow(() => context.indicatorSignalSetLines(root));
        for (const usage of ['Entrada', 'Saída']) {
            root.fields.set('[name="indicator-usage-1"]:checked', usage);
            root.fields.set('[name="indicator-usage-2"]:checked', usage);
            assert.throws(() => context.indicatorSignalSetLines(root), {name: 'SignalValidationError'});
            assert.match(context.indicatorUsageErrors(root)[0], /Indicadores 1 e 2/);
        }
        assert.throws(() => context.indicatorSignalSetLines(fixture([], [type, type, type, 'Não usar'])), {name: 'SignalValidationError'});
    }
});
