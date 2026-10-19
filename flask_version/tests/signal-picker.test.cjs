const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Select {
    constructor() { this.options = []; this.dataset = {}; this.listeners = {}; this.value = ''; }
    replaceChildren(...options) { this.options = options; this.value = options[0]?.value || ''; }
    setAttribute() {}
    addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
    dispatchEvent(event) { for (const listener of this.listeners[event.type] || []) listener(event); }
    after(...controls) { this.controls = controls; }
}
function fixture() {
    const source = new Select();
    const doc = {createElement: tag => tag === 'select' ? new Select() : {}, addEventListener() {},
        querySelector: () => root};
    source.ownerDocument = doc;
    source.id = 'condition-1-target';
    source.previousElementSibling = {tagName: 'LABEL', textContent: 'A'};
    const root = {querySelectorAll: () => [source]};
    const context = vm.createContext({document: doc, window: {addEventListener() {}}, Event: class {constructor(type) { this.type = type; }}});
    for (const file of ['signal.js', 'app.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '../static', file), 'utf8'), context);
    const load = type => {
        source.options = [{value: 'N.usar'}, ...Array.from(context.indicatorSignalSources(type, 1), line => ({value: line.source})), {value: 'Valor fixo'}];
    };
    return {source, context, load};
}

test('ADX picker restores DI buffers, changes lines and exposes a numeric reference', () => {
    const {source, context, load} = fixture();
    load('ADX'); source.value = 'Indicador 1: ADX +DI';
    context.bindSignalSourcePickers();
    const [group, line] = source.controls;
    assert.equal(group.value, 'Indicador 1:');
    assert.deepEqual(Array.from(line.options, option => option.textContent), ['ADX', 'DI+', 'DI\u2212']);
    assert.equal(line.value, source.value);
    line.value = 'Indicador 1: ADX \u2212DI'; line.dispatchEvent({type: 'change'});
    assert.equal(source.value, line.value);
    group.value = 'Valor fixo'; group.dispatchEvent({type: 'change'});
    assert.equal(source.value, 'Valor fixo'); assert.equal(line.hidden, true);
    source.value = 'N.usar'; source.signalPickerRefresh();
    assert.equal(group.value, 'N.usar'); assert.equal(line.hidden, true);
});

test('picker rebuilds indicator-specific lines after the indicator type changes', () => {
    const {source, context, load} = fixture();
    load('ADX'); source.value = 'N.usar'; context.bindSignalSourcePickers();
    load('RSI'); source.value = 'N.usar'; source.signalPickerRefresh();
    const [group, line] = source.controls;
    group.value = 'Indicador 1:'; group.dispatchEvent({type: 'change'});
    assert.equal(line.options.length, 4);
    assert.equal(source.value, 'Indicador 1: RSI');
    assert.equal(line.hidden, false);
    assert.ok(line.options.every(option => !option.textContent.startsWith('DI')));
});
