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

test('current saved controls round trip without migrations or inferred timeframes', () => {
 const stored={};
 const app=vm.createContext({document:{addEventListener(){}},window:{addEventListener(){}},localStorage:{getItem:key=>stored[key]}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8'),app);
 function control(value,attributes=[]) { return {value,type:'text',tagName:'INPUT',hasAttribute:a=>attributes.includes(a),matches:s=>attributes.some(a=>s.includes(`[${a}]`))}; }
 const controls=[control('14'),control('Se',['data-condition-control']),control('H1',['data-slot-timeframe-extra']),control('M5',['data-slot-timeframe-extra'])];
 const root={querySelectorAll:s=>['[data-crossing-source]','[data-indicator-type]'].includes(s)?[]:controls};
 const state={indicadores:app.setupControls(root).map(c=>({value:c.value}))};
 stored['geraset-flask-cards-v1']=JSON.stringify(state);
 controls.forEach(c=>c.value='changed');app.restoreSetup(root,'indicadores');
 assert.deepEqual(controls.map(c=>c.value),['14','Se','H1','M5']);
 assert.equal(app.readSetupState().legacySlotTimeframe,undefined);
});
