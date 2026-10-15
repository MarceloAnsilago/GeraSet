const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/signal.js'), 'utf8'), context);

const valid = {
    operator: 'Se', target: 'Indicador 1: RSI', targetCandle: 'Anterior',
    comparison: 'Menor que', reference: 'Valor fixo', referenceCandle: 'N.usar',
    fixed: '30', distance: '0', usage: 'Entrada', sense: 'Normal', normalSide: 'Compra',
};

function card(rules, unit = 'N.usar') {
    return {
        querySelector: () => ({value: unit}),
        querySelectorAll: () => rules.map(rule => ({
            closest: () => ({querySelector: selector => {
                const index = /data-indicator-type="(\d+)"/.exec(selector)[1];
                const usage = rule.sourceUsages?.[index] || rule.usage;
                return {closest: () => ({querySelector: () => ({value: usage})})};
            }}),
            querySelector(selector) {
                const key = /name\$="-([^"]+)"/.exec(selector)[1]
                    .replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
                return {value: rule[key]};
            },
        })),
    };
}

test('RSI accepts a fixed threshold without a reference candle, including zero', () => {
    assert.equal(context.signalRuleErrors(valid, 'N.usar').length, 0);
    assert.equal(context.signalRuleErrors({...valid, fixed: '0'}, 'N.usar').length, 0);
    assert.match(context.signalSummaryLines(card([valid]))[0], /Menor que 30/);
});

test('missing candles and malformed thresholds or distances fail validation', () => {
    for (const change of [{targetCandle: 'N.usar'}, {fixed: ''}, {fixed: 'abc'}, {distance: '-1'}, {distance: ''}, {distance: 'abc'}, {distance: '2'}]) {
        assert.ok(context.signalRuleErrors({...valid, ...change}, 'N.usar').length);
    }
    assert.ok(context.signalRuleErrors({...valid, reference: 'Indicador 2: RSI'}, 'N.usar').length);
});

test('closed crossings reject the current candle but ordinary comparisons accept it', () => {
    assert.ok(context.signalRuleErrors({...valid, comparison: 'Cruzar&fechar acima de', targetCandle: 'Vela atual'}, 'N.usar').length);
    assert.equal(context.signalRuleErrors({...valid, targetCandle: 'Vela atual'}, 'N.usar').length, 0);
});

test('distance validation rejects mixed scales, oscillator points and a zero percentage base', () => {
    assert.ok(context.signalRuleErrors({...valid, reference: 'Fechamento da vela', referenceCandle: 'Anterior'}, 'N.usar').length);
    assert.ok(context.signalRuleErrors({...valid, distance: '1'}, 'Pontos').length);
    assert.ok(context.signalRuleErrors({...valid, fixed: '0', distance: '1'}, 'Porcentagem').length);
    assert.equal(context.signalRuleErrors({...valid, distance: '1'}, 'Porcentagem').length, 0);
    assert.equal(context.signalRuleErrors({...valid, target: 'Indicador 1: ADX +DI', reference: 'Indicador 1: ADX −DI', referenceCandle: 'Anterior'}, 'N.usar').length, 0);
});

test('logic groups by purpose and resulting side and displays E before Ou', () => {
    const rules = [valid, {...valid, operator: 'Ou'}, {...valid, operator: 'E'}, {...valid, usage: 'Saída'}];
    assert.equal(context.validateSignalCard(card(rules)).length, 0);
    assert.ok(context.signalSummaryLines(card(rules)).includes('Entrada / Compra: (C1) Ou (C2 E C3)'));
    assert.ok(context.validateSignalCard(card([{...valid, operator: 'E'}])).length);
    assert.ok(context.validateSignalCard(card([valid, valid])).length);
});

test('normal and inverted signals distinguish entry from exit without reversing the comparison', () => {
    for (const [normalSide, sense, result, entry, exit] of [
        ['Compra', 'Normal', 'Compra', 'Abrir compra', 'Fechar vendas'],
        ['Compra', 'Inverter', 'Venda', 'Abrir venda', 'Fechar compras'],
        ['Venda', 'Normal', 'Venda', 'Abrir venda', 'Fechar compras'],
        ['Venda', 'Inverter', 'Compra', 'Abrir compra', 'Fechar vendas'],
    ]) {
        const rule = {...valid, normalSide, sense};
        assert.equal(context.signalResultSide(rule), result);
        assert.equal(context.signalAction(rule), entry);
        assert.equal(context.signalAction({...rule, usage: 'Saída'}), exit);
        assert.ok(context.signalSummaryLines(card([rule]))[0].includes(entry));
        assert.equal(rule.comparison, 'Menor que');
    }
    assert.ok(context.signalRuleErrors({...valid, normalSide: ''}, 'N.usar').length);
    assert.ok(context.signalRuleErrors({...valid, sense: 'other'}, 'N.usar').length);
    assert.equal(context.validateSignalCard(card([valid, {...valid, normalSide: 'Venda'}])).length, 0);
    assert.equal(context.validateSignalCard(card([valid, {...valid, normalSide: 'Venda', sense: 'Inverter', operator: 'E'}])).length, 0);
});

test('empty rows remain inactive despite purpose and sense defaults', () => {
    const inactive = {...valid, operator: 'N.usar', target: 'N.usar', targetCandle: 'N.usar', comparison: 'N.usar', reference: 'N.usar'};
    assert.equal(context.signalRowActive(inactive), false);
    assert.equal(context.validateSignalCard(card([inactive])).length, 0);
    assert.equal(context.signalSummaryLines(card([inactive])).length, 0);
});

test('purpose is inherited from indicators and mixed purposes block export', () => {
    const exit = {...valid, usage: 'Saída'};
    assert.match(context.signalSummaryLines(card([exit]))[0], /Saída/);
    const mixed = {...valid, reference: 'Indicador 2: RSI', referenceCandle: 'Anterior', sourceUsages: {'1': 'Entrada', '2': 'Saída'}};
    assert.match(context.validateSignalCard(card([mixed])).join(' '), /finalidades diferentes/);
    const prices = {...valid, target: 'Fechamento da vela', usage: 'Saída'};
    assert.match(context.signalSummaryLines(card([prices]))[0], /Entrada/);
});

test('new fields preserve old saved control positions and survive another save and restore', () => {
    const stored = {};
    const appContext = vm.createContext({
        document: {addEventListener() {}}, window: {addEventListener() {}},
        localStorage: {getItem: key => stored[key], setItem: (key, value) => { stored[key] = value; }},
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8'), appContext);
    function control(value, attributes = []) {
        return {
            value, type: 'text', tagName: 'INPUT', checked: false,
            hasAttribute: attribute => attributes.includes(attribute),
            matches(selector) {
                if (selector === '.tab-panel-optimize input[type="number"]') return false;
                if (selector.startsWith('[data-conditions]')) return false;
                return attributes.some(attribute => selector.includes(`[${attribute}]`));
            },
        };
    }
    const original = [control('14'), control('Se', ['data-condition-control']), control('30', ['data-condition-control'])];
    const extras = [control('Entrada', ['data-condition-control', 'data-signal-extra']), control('Compra e venda', ['data-condition-control', 'data-signal-extra']), control('0', ['data-condition-control', 'data-signal-extra'])];
    const root = {querySelectorAll: selector => ['[data-crossing-source]', '[data-indicator-type]'].includes(selector) ? [] : [original[0], original[1], ...extras, original[2]]};
    const state = {indicadores: original.map(item => ({value: item.value, checked: false})), optimizationZeroVersion: {indicadores: 1}, signalDefaultsVersion: 1};
    stored['geraset-flask-cards-v1'] = JSON.stringify(state);
    original.forEach(item => { item.value = 'changed'; });
    appContext.restoreSetup(root, 'indicadores');
    assert.deepEqual(original.map(item => item.value), ['14', 'Se', '30']);
    assert.deepEqual(extras.map(item => item.value), ['Entrada', 'Compra e venda', '0']);
    extras[0].value = 'Saída';
    extras[1].value = 'Somente venda';
    extras[2].value = '25';
    state.indicadores = appContext.setupControls(root).map(item => ({value: item.value, checked: false}));
    stored['geraset-flask-cards-v1'] = JSON.stringify(state);
    extras.forEach(item => { item.value = 'changed'; });
    appContext.restoreSetup(root, 'indicadores');
    assert.deepEqual(extras.map(item => item.value), ['Saída', 'Somente venda', '25']);

    const retained = Array.from({length: 5}, () => [
        control('Compra e venda', ['data-condition-control', 'data-signal-extra']),
        control('0', ['data-condition-control', 'data-signal-extra']),
    ]).flat();
    const migratedRoot = {querySelectorAll: selector => ['[data-crossing-source]', '[data-indicator-type]'].includes(selector) ? [] : [...original, ...retained]};
    state.indicadores = [...original.map(item => ({value: item.value})),
        ...Array.from({length: 5}, (_, index) => [
            {value: 'Saída'}, {value: 'Somente venda'}, {value: String(index + 10)},
        ]).flat()];
    stored['geraset-flask-cards-v1'] = JSON.stringify(state);
    appContext.restoreSetup(migratedRoot, 'indicadores');
    assert.deepEqual(retained.map(item => item.value), ['Somente venda', '10', 'Somente venda', '11', 'Somente venda', '12', 'Somente venda', '13', 'Somente venda', '14']);

    // New side fields append after every existing field; 15 extras are no longer
    // mistaken for the legacy layout that contained a usage field per row.
    const sides = Array.from({length: 5}, () => control('', ['data-condition-control', 'data-signal-extra', 'data-signal-normal-side']));
    const nextRoot = {querySelectorAll: selector => ['[data-crossing-source]', '[data-indicator-type]'].includes(selector) ? [] : [...sides, ...original, ...retained]};
    state.indicadores = [...original, ...retained].map(item => ({value: item.value}));
    stored['geraset-flask-cards-v1'] = JSON.stringify(state);
    appContext.restoreSetup(nextRoot, 'indicadores');
    assert.deepEqual(sides.map(item => item.value), ['', '', '', '', '']);
    sides.forEach((item, i) => { item.value = i % 2 ? 'Venda' : 'Compra'; });
    state.indicadores = appContext.setupControls(nextRoot).map(item => ({value: item.value}));
    state.signalNormalSideVersion = 1;
    stored['geraset-flask-cards-v1'] = JSON.stringify(state);
    sides.forEach(item => { item.value = ''; });
    appContext.restoreSetup(nextRoot, 'indicadores');
    assert.deepEqual(sides.map(item => item.value), ['Compra', 'Venda', 'Compra', 'Venda', 'Compra']);
    assert.equal(retained[1].value, '10');
    const levels = Array.from({length: 16}, () => control('50', ['data-rsi-level-extra']));
    const levelRoot = {querySelectorAll: selector => ['[data-crossing-source]', '[data-indicator-type]'].includes(selector) ? [] : [...levels, ...sides, ...original, ...retained]};
    appContext.restoreSetup(levelRoot, 'indicadores');
    assert.deepEqual(sides.map(item => item.value), ['Compra', 'Venda', 'Compra', 'Venda', 'Compra']);
    assert.ok(levels.every(item => item.value === '50'));
    levels[0].value = '55';
    state.indicadores = appContext.setupControls(levelRoot).map(item => ({value: item.value}));
    stored['geraset-flask-cards-v1'] = JSON.stringify(state);
    levels[0].value = '0';
    appContext.restoreSetup(levelRoot, 'indicadores');
    assert.equal(levels[0].value, '55');

});
