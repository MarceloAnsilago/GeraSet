const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const c = vm.createContext({document: {addEventListener() {}}, window: {addEventListener() {}}});
for (const file of ['export.js', 'import.js', 'app.js'])
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../static', file), 'utf8'), c);
const controls = values => Object.entries(values).map(([key, value]) => ({key, value}));
function values(key, extra = {}) {
    return {[`${key}-mode`]: 'Pontos', [`${key}-trigger`]: '100', [`${key}-distance`]: '30', [`${key}-step`]: '5',
        ...Object.fromEntries(['activate', 'distance', 'step'].flatMap(field =>
            ['start', 'step', 'end'].map(bound => [`${key}-${field}-${bound}`, '0']))), ...extra};
}
const definitions = [['trailing', 'InpTrailing'], ['moving-stop', 'InpMovingStop']];
for (const [key, prefix] of definitions) {
    const lines = (extra = {}) => Array.from(c.managedStopSetLines(controls(values(key, extra)))).filter(line => line.startsWith(prefix));
    test(`${key}: emits standard native mode, activation, distance and adjustment step`, () => {
        assert.deepEqual(lines(), [`${prefix}Mode=1||1||1||1||N`, `${prefix}Trigger=100||100||0.01||100||N`,
            `${prefix}Distance=30||30||0.01||30||N`, `${prefix}Step=5||5||0.01||5||N`]);
        const percent = lines({[`${key}-mode`]: 'Porcentagem', [`${key}-trigger`]: '1,5', [`${key}-distance`]: '0,75', [`${key}-step`]: '0,1'});
        assert.deepEqual(percent, [`${prefix}Mode=2||2||1||2||N`, `${prefix}Trigger=1.5||1.5||0.01||1.5||N`,
            `${prefix}Distance=0.75||0.75||0.01||0.75||N`, `${prefix}Step=0.1||0.1||0.01||0.1||N`]);
    });
    test(`${key}: disabled clears all native values while ignoring inactive draft/ranges`, () => {
        const result = lines({[`${key}-mode`]: 'Desativado', [`${key}-trigger`]: 'bad', [`${key}-distance`]: '-3', [`${key}-step-start`]: 'bad'});
        assert.deepEqual(result, [`${prefix}Mode=0||0||1||0||N`, ...['Trigger', 'Distance', 'Step'].map(s => `${prefix}${s}=0||0||0.01||0||N`)]);
    });
    test(`${key}: validates fixed inputs and all enabled optimization intervals`, () => {
        for (const field of ['trigger', 'distance', 'step'])
            for (const value of ['0', '-1', 'NaN', 'Infinity', '', '1.001', '100000001', '1e2'])
                assert.throws(() => lines({[`${key}-${field}`]: value}), {name: 'ManagementValidationError'});
        for (const extra of [{[`${key}-mode`]: 'Indicador'},
            {[`${key}-distance-start`]: '0', [`${key}-distance-step`]: '1', [`${key}-distance-end`]: '10'},
            {[`${key}-step-start`]: '1', [`${key}-step-step`]: '0', [`${key}-step-end`]: '5'},
            {[`${key}-activate-start`]: '100', [`${key}-activate-step`]: '1', [`${key}-activate-end`]: '50'}])
            assert.throws(() => lines(extra), {name: 'ManagementValidationError'});
        assert.ok(lines({[`${key}-distance`]: '150'}).some(line => line.startsWith(`${prefix}Distance=150||`))); // Uni allows distance > activation
        const optimized = lines({[`${key}-activate-start`]: '50', [`${key}-activate-step`]: '10', [`${key}-activate-end`]: '150'});
        assert.ok(optimized.includes(`${prefix}Trigger=100||50||10||150||Y`));
    });
}

test('both policies round-trip native values; legacy missing groups migrate only to disabled', () => {
    const original = new Map(c.managedStopSetLines(controls({...values('trailing'), ...values('moving-stop')})).map(line => line.split('=')));
    c.validateSetupInputs(original, new Map(original));
    const tampered = new Map(original); tampered.set('InpTrailingDistance', '10||10||0.01||10||N');
    assert.throws(() => c.validateSetupInputs(tampered, original));
    const empty = new Map();
    const disabled = new Map(c.managedStopSetLines([]).map(line => line.split('=')));
    c.validateSetupInputs(empty, disabled);
    assert.throws(() => c.validateSetupInputs(empty, original));
    const partial = new Map(disabled); partial.delete('InpMovingStopStep');
    assert.throws(() => c.validateSetupInputs(partial, disabled));
});

test('management summary follows current values and percentage units', () => {
    assert.equal(c.managementSummaryText('trailing', values('trailing')), 'Trailing stop: ativação 100 pontos; distância 30 pontos; passo 5 pontos');
    assert.match(c.managementSummaryText('moving-stop', values('moving-stop', {'moving-stop-mode': 'Porcentagem'})), /Stop móvel: ativação 100 %; distância 30 %; passo 5 %/);
    assert.equal(c.managementSummaryText('trailing', values('trailing', {'trailing-mode': 'Desativado'})), 'Trailing stop: Desativado');
});

test('import restores new named fields and safely migrates old unnamed management controls', async () => {
    for (const legacy of [false, true]) {
        const fields = {...values('trailing'), ...values('moving-stop', {'moving-stop-mode': 'Porcentagem'})};
        const inputs = Object.keys(fields).map(name => ({name, id: '', value: name.endsWith('-mode') ? 'Desativado' : '0',
            tagName: name.endsWith('-mode') ? 'SELECT' : 'INPUT', type: 'text',
            options: ['Desativado', 'Pontos', 'Porcentagem'].map(value => ({value})), hasAttribute: () => false}));
        const pages = ['inicio', 'indicadores', 'gestao', 'configuracoes'];
        const roots = new Map(pages.map(page => [page, {
            controls: page === 'gestao' ? inputs : [{name: 'field', value: '25', tagName: 'INPUT', hasAttribute: () => false}],
            querySelector(selector) {
                if (selector.startsWith('[data-page=')) return this;
                const name = /^\[name="([^"]+)"\]$/.exec(selector)?.[1];
                return this.controls.find(input => input.name === name) || null;
            },
        }]));
        const metadata = {format: 'geraset', version: 2, pages: Object.fromEntries(pages.map(page => [page,
            roots.get(page).controls.map((input, index) => ({key: legacy && /^(trailing|moving-stop)-(mode|trigger|distance|step)$/.test(input.name)
                ? `gestao_${index}` : input.name, value: fields[input.name] || input.value}))]))};
        const native = new Map([['InpName', 'Teste']]);
        if (!legacy) for (const line of c.managedStopSetLines(controls(fields))) native.set(...line.split('='));
        const env = vm.createContext({document: {addEventListener() {}}, TextDecoder,
            fetch: async url => ({ok: true, text: async () => url.slice(1)}),
            DOMParser: class {parseFromString(page) {return roots.get(page);}},
            setupControls: root => root.controls, updateCrossingOptions() {},
            serializeSetupSet() {
                const lines = ['InpName=Teste', ...env.managedStopSetLines(roots.get('gestao').controls.map(input => ({key: input.name, value: input.value})))];
                return {contents: Buffer.from(lines.join('\n')+'\n'+JSON.stringify(metadata, null, 2).split('\n').map(line => '; '+line).join('\n'))};
            },
        });
        const serialize = env.serializeSetupSet;
        for (const file of ['export.js', 'import.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '../static', file), 'utf8'), env);
        env.serializeSetupSet = serialize;
        const state = await env.prepareSetupImport({metadata, native});
        for (const key of ['trailing', 'moving-stop']) {
            const index = inputs.findIndex(input => input.name === key+'-mode');
            assert.equal(state.gestao[index].value, legacy ? 'Desativado' : fields[key+'-mode']);
            assert.equal(state.gestao[index+1].value, '100');
            assert.equal(state.gestao[index+2].value, '30');
            assert.equal(state.gestao[index+3].value, '5');
        }
    }
});
