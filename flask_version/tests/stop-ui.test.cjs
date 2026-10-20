const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
function environment(document, state = {}) {
    return vm.createContext({document: {addEventListener() {}, ...document},
        window: {addEventListener() {}}, localStorage: {getItem: () => JSON.stringify(state)}});
}
test('switching stop mode hides and disables candle controls without discarding values', () => {
    let change;
    const mode = {value: 'Distância fixa', addEventListener(_, fn) { change = fn; }};
    const fields = [{value: '2.5'}, {value: 'Penúltimo'}];
    const group = {classList: {toggle(_, value) { group.hidden = value; }}, querySelectorAll: () => fields};
    const context = environment({querySelector: selector => selector === '[data-stop-mode]' ? mode : null,
        querySelectorAll: selector => selector === '[data-stop-candle]' ? [group] : []});
    vm.runInContext(source, context);
    context.bindRulesVisibility();
    assert.equal(group.hidden, true);
    assert.ok(fields.every(f => f.disabled));
    mode.value = 'Distância + candle'; change();
    assert.equal(group.hidden, false);
    assert.ok(fields.every(f => !f.disabled));
    assert.deepEqual(fields.map(f => f.value), ['2.5', 'Penúltimo']);
});
test('new stop mode appends after existing saved controls and restores legacy positions', () => {
    const field = (value, extra = false) => ({value, tagName: 'INPUT', type: 'text',
        hasAttribute: attr => extra && attr === 'data-stop-mode-extra',
        matches: selector => extra && selector.includes('[data-stop-mode-extra]')});
    const stop = field('changed'), take = field('changed'), mode = field('Distância + candle', true);
    const root = {querySelectorAll: selector => ['[data-crossing-source]', '[data-indicator-type]'].includes(selector) ? [] : [mode, stop, take]};
    const state = {gestao: [{value: '80'}, {value: '160'}], optimizationZeroVersion: {gestao: 1}};
    const context = environment({}, state);
    vm.runInContext(source, context);
    context.restoreSetup(root, 'gestao');
    assert.deepEqual(Array.from(context.setupControls(root), c => c.value), ['80', '160', 'Distância + candle']);
    state.gestao.push({value: 'Distância fixa'});
    context.restoreSetup(root, 'gestao');
    assert.equal(mode.value, 'Distância fixa');
});
test('review and optimization ignore candle fields in fixed stop mode', () => {
    const mode = {value: 'Distância fixa'};
    const card = {dataset: {}, matches: () => false, querySelector: selector => selector === '[data-stop-mode]' ? mode : null};
    const control = {closest: selector => selector === '[data-stop-candle]' ? {} : null};
    const context = environment({}); vm.runInContext(source, context);
    assert.equal(context.relevantReviewControl(control, card), false);
    mode.value = 'Distância + candle';
    assert.equal(context.relevantReviewControl(control, card), true);
});


test('visualization checkboxes restore the current settings page independently', () => {
    const field = name => ({name, value: 'on', checked: true, type: 'checkbox', tagName: 'INPUT',
        hasAttribute: () => false, matches: () => false});
    const histogram = field('show_signal_histograms'), panel = field('show_mt5_panel');
    const root = {querySelectorAll: selector => ['[data-crossing-source]', '[data-indicator-type]'].includes(selector) ? [] : [histogram, panel]};
    const state = {};
    const context = environment({}, state); vm.runInContext(source, context);
    context.restoreSetup(root, 'configuracoes');
    assert.equal(histogram.checked, true);
    assert.equal(panel.checked, true);
    state.configuracoes = [{value: 'on', checked: true}, {value: 'on', checked: false}];
    context.restoreSetup(root, 'configuracoes');
    assert.equal(histogram.checked, true);
    assert.equal(panel.checked, false);
});
