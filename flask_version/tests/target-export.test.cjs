const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({document: {addEventListener() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/export.js'), 'utf8'), context);
function lines(overrides = {}) {
    const values = {target_unit: 'Pontos', target_stop: '20', target_stop_multiplier: '1.5',
        target_candle: 'Penúltimo', target_size: 'Corpo', target_take_mode: 'Distância fixa',
        target_take_distance: '150,25', target_take_multiplier: '2',
        'target-candle-start': 'último', 'target-candle-end': 'último',
        'target-size-start': 'Total com pavios', 'target-size-end': 'Total com pavios',
        ...Object.fromEntries(['stop', 'take-distance', 'take-multiplier'].flatMap(key => ['start', 'step', 'end'].map(b => [`target-${key}-${b}`, '0']))), ...overrides};
    return Array.from(context.targetSetLines(Object.entries(values).map(([key, value]) => ({key, value}))));
}
test('fixed take exports mode, unit and distance independently of the stop multiplier', () => {
    const result = lines();
    assert.ok(result.includes('InpTakeMode=1||1||1||1||N'));
    assert.ok(result.includes('InpTakeProfit=150.25||150.25||0.01||150.25||N'));
    assert.ok(result.includes('InpTakeStopMultiplier=0||0||1||0||N'));
    assert.ok(result.includes('InpStopCandleMultiplier=1.5||1.5||1||1.5||N'));
    assert.ok(result.some(s => s.startsWith('InpStopCandle=2||')));
    assert.ok(result.some(s => s.startsWith('InpStopBody=1||')));
});
test('fixed take zero stays fixed and ignores hidden multiplier values and ranges', () => {
    const result = lines({target_take_distance: '0', target_take_multiplier: 'bad', 'target-take-multiplier-step': 'bad'});
    assert.ok(result.includes('InpTakeMode=1||1||1||1||N'));
    assert.ok(result.includes('InpTakeProfit=0||0||0.01||0||N'));
});
test('percentage distance and optimization preserve the fixed current value', () => {
    const result = lines({target_unit: 'Porcentagem', target_take_distance: '2',
        'target-take-distance-start': '0', 'target-take-distance-step': '0.5', 'target-take-distance-end': '3'});
    assert.ok(result.includes('InpTargetUnit=1||1||1||1||N'));
    assert.ok(result.includes('InpTakeProfit=2||0||0.5||3||Y'));
});
test('stop multiple mode ignores hidden fixed distance and exports its own range', () => {
    const result = lines({target_take_mode: 'Vezes o stop', target_take_distance: 'bad',
        'target-take-distance-step': 'bad', 'target-take-multiplier-start': '1',
        'target-take-multiplier-step': '0.5', 'target-take-multiplier-end': '3'});
    assert.ok(result.includes('InpTakeMode=0||0||1||0||N'));
    assert.ok(result.includes('InpTakeProfit=0||0||1||0||N'));
    assert.ok(result.includes('InpTakeStopMultiplier=2||1||0.5||3||Y'));
});
test('invalid active distances, modes and ranges block export', () => {
    for (const values of [{target_take_distance: '-1'}, {target_take_distance: ''}, {target_take_distance: 'Infinity'},
        {target_take_mode: ''}, {'target-take-distance-end': '10'},
        {'target-take-distance-start': '10', 'target-take-distance-step': '1', 'target-take-distance-end': '2'}])
        assert.throws(() => lines(values), {name: 'TargetValidationError'});
});

test('stop multiples cannot export a disabled stop in fixed values or optimization', () => {
    for (const extra of [
        {target_stop: '0'},
        {target_stop: '10', 'target-stop-start': '0', 'target-stop-step': '5', 'target-stop-end': '20'},
    ]) assert.throws(() => lines({target_stop_mode: 'Distância fixa', target_take_mode: 'Vezes o stop', ...extra}), {name: 'TargetValidationError'});
    assert.doesNotThrow(() => lines({target_stop_mode: 'Distância fixa', target_take_mode: 'Vezes o stop', target_stop: '0', target_take_multiplier: '0'}));
});

test('fixed stop exports distance and clears all inactive candle parameters and ranges', () => {
    const result = lines({target_stop_mode: 'Distância fixa', target_stop: '80',
        target_stop_multiplier: 'bad', target_candle: 'bad', target_size: 'bad',
        'target-candle-start': 'bad', 'target-size-end': 'bad'});
    for (const expected of ['InpStopMode=1||1||1||1||N', 'InpStopLoss=80||80||0.01||80||N',
        'InpStopCandleMultiplier=0||0||1||0||N', 'InpStopCandle=1||1||1||1||N', 'InpStopBody=0||0||1||0||N'])
        assert.ok(result.includes(expected), expected);
});
test('fixed stop zero, percent and optimized ranges are exported independently of candle settings', () => {
    assert.ok(lines({target_stop_mode: 'Distância fixa', target_stop: '0'}).includes('InpStopLoss=0||0||0.01||0||N'));
    const result = lines({target_stop_mode: 'Distância fixa', target_unit: 'Porcentagem', target_stop: '2',
        'target-stop-start': '1', 'target-stop-step': '0.5', 'target-stop-end': '3'});
    assert.ok(result.includes('InpStopLoss=2||1||0.5||3||Y'));
    assert.ok(result.includes('InpTargetUnit=1||1||1||1||N'));
    assert.throws(() => lines({target_stop_mode: 'invalid'}), {name: 'TargetValidationError'});
});
test('legacy and explicit combined stops retain candle contribution', () => {
    for (const values of [{}, {target_stop_mode: 'Distância + candle'}]) {
        const result = lines(values);
        assert.ok(result.includes('InpStopMode=0||0||1||0||N'));
        assert.ok(result.includes('InpStopCandleMultiplier=1.5||1.5||1||1.5||N'));
    }
});
