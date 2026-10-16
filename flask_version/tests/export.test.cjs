const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../static/export.js'), 'utf8');

function environment({picker, fetchFails = false, signalErrors = []} = {}) {
    const status = {textContent: ''};
    const button = {disabled: true, addEventListener(_, callback) { this.click = callback; }};
    const stored = {name: 'Estratégia / teste', lot: '0.25', end: '25'};
    const name = {name: 'setup_name', value: 'default', checked: false};
    const magic = {name: 'setup_magic', value: '1', checked: false};
    const lot = {name: 'setup_lot', id: '', value: '0.01', checked: false};
    const operation = Object.entries({
        setup_market: 'Forex', setup_mode: 'Day trade', setup_timeframe: 'Tempo corrente',
        setup_direction: 'Compra e venda',
        'operation-timeframe-start': 'Tempo corrente', 'operation-timeframe-end': 'Tempo corrente',
        'operation-direction-start': 'Compra e venda', 'operation-direction-end': 'Compra e venda',
        setup_entry_start: '00:00', setup_entry_end: '23:55',
        'schedule-entry-start-start': '00:00', 'schedule-entry-start-end': '00:00',
        'schedule-entry-end-start': '23:55', 'schedule-entry-end-end': '23:55',
    }).map(([name, value]) => ({name, value, checked: false}));
    const end = {name: 'period-end', value: '10', checked: false};
    const targets = Object.entries({target_unit: 'Pontos', target_stop: '0', target_stop_multiplier: '1',
        target_candle: 'último', target_size: 'Total com pavios', target_take_mode: 'Distância fixa',
        target_take_distance: '150', target_take_multiplier: '2',
        'target-candle-start': 'último', 'target-candle-end': 'último',
        'target-size-start': 'Total com pavios', 'target-size-end': 'Total com pavios',
        ...Object.fromEntries(['stop', 'take-distance', 'take-multiplier'].flatMap(key => ['start', 'step', 'end'].map(b => [`target-${key}-${b}`, '0'])))
    }).map(([name, value]) => ({name, value, checked: false}));
    const usage = {name: 'usage', value: 'Saída', checked: true};
    const roots = new Map(['inicio', 'indicadores', 'gestao'].map(page => [page, {
        controls: page === 'inicio' ? [name, magic, lot, ...operation] : page === 'gestao' ? [end, usage, {name: 'order_mode', value: 'A mercado'}, ...targets] : [end, usage],
        querySelector(selector) {
            if (selector.startsWith('[data-page=')) return this;
            if (page === 'indicadores') {
                if (selector.startsWith('[data-indicator-type=')) return {value: 'Não usar'};
                if (selector.startsWith('[name="indicator-usage-')) return {value: 'Entrada'};
                if (selector === '[data-conditions]') return {querySelector: () => ({value: 'N.usar'}), querySelectorAll: () => []};
            }
            if (page !== 'inicio') return null;
            return selector === '[data-setup-name]' ? name : magic;
        },
    }]));
    const downloads = [];
    const revoked = [];
    const context = vm.createContext({
        document: {
            querySelector: selector => selector === '[data-export-set]' ? button : status,
            addEventListener() {},
            body: {appendChild() {}},
            createElement: () => ({click() { downloads.push(this.download); }, remove() {}}),
        },
        window: picker ? {showSaveFilePicker: picker} : {},
        fetch: async url => ({ok: !fetchFails, text: async () => url.slice(1)}),
        DOMParser: class { parseFromString(page) { return roots.get(page); } },
        restoreSetup(root, page) {
            if (page === 'inicio') { name.value = stored.name; lot.value = stored.lot; }
            else end.value = stored.end;
        },
        setupControls: root => root.controls,
        validateSignalCard: () => signalErrors,
        magicNumberFromName: () => '12345',
        Blob,
        URL: {createObjectURL: () => 'blob:test', revokeObjectURL: url => revoked.push(url)},
        setTimeout: callback => callback(),
    });
    vm.runInContext(source, context);
    return {context, button, status, stored, downloads, revoked};
}

test('exports the latest configuration and confirms only after closing the file', async () => {
    let written, preset, options, closed = false;
    const env = environment({picker: async value => {
        options = value;
        return {name: 'chosen.set', createWritable: async () => ({
            write: async contents => {
                const bytes = Buffer.from(contents);
                assert.equal(bytes.readUInt16LE(0), 0xfeff);
                preset = bytes.subarray(2).toString('utf16le');
                const comments = preset.split('\r\n').filter(line => line.startsWith('; ')).slice(1);
                written = JSON.parse(comments.map(line => line.slice(2)).join('\n'));
            },
            close: async () => {
                assert.equal(env.status.textContent, 'Salvando set...');
                closed = true;
            },
        })};
    }});
    await env.context.bindSetExport();
    env.stored.lot = '0.50';
    env.stored.end = '50';
    await env.button.click();
    assert.equal(options.suggestedName, 'Estratégia _ teste.set');
    assert.equal(written.format, 'geraset');
    assert.deepEqual(preset.split('\r\n').filter(line => line && !line.startsWith(';')), [
        'InpName=Estratégia / teste', 'InpMagic=12345||12345||1||2147483647||N',
        'InpMarket=0||0||1||0||N', 'InpTradeMode=0||0||1||0||N',
        'InpStrategyTimeframe=0||0||1||0||N', 'InpLot=0.5||0.5||0.01||0.5||N',
        'InpDirection=0||0||1||0||N',
        'InpEntryStart=0||0||5||0||N', 'InpEntryEnd=1435||1435||5||1435||N',
        'InpOrderMode=0||0||1||0||N', 'InpPendingReference=0||0||1||0||N', 'InpPendingCandle=1||1||1||1||N',
        'InpTargetUnit=0||0||1||0||N', 'InpStopMode=0||0||1||0||N', 'InpStopLoss=0||0||0.01||0||N', 'InpStopCandleMultiplier=1||1||1||1||N',
        'InpStopCandle=1||1||1||1||N', 'InpStopBody=0||0||1||0||N', 'InpTakeMode=1||1||1||1||N',
        'InpTakeProfit=150||150||0.01||150||N', 'InpTakeStopMultiplier=0||0||1||0||N',
        'InpBreakevenMode=0||0||1||0||N', 'InpBreakevenTrigger=0||0||0.01||0||N', 'InpBreakevenOffset=0||0||0.01||0||N',
        ...[1, 2, 3, 4].flatMap(i => [`InpIndicator${i}Type=-1||-1||1||-1||N`, `InpIndicator${i}Exit=0||0||1||0||N`]),
        ...[1, 2, 3, 4, 5].map(i => `InpSignal${i}=`),
    ]);
    assert.equal(written.pages.inicio[1].value, '12345');
    assert.equal(written.pages.inicio[2].value, '0.50');
    assert.equal(written.pages.indicadores[0].value, '50');
    assert.equal(written.pages.indicadores[1].checked, true);
    assert.equal(Object.keys(written.pages).length, 3);
    assert.equal(closed, true);
    assert.equal(env.status.textContent, 'Set salvo: chosen.set');
    assert.equal(env.button.disabled, false);
});

test('canceling does not download a replacement or report success', async () => {
    const env = environment({picker: async () => { throw {name: 'AbortError'}; }});
    await env.context.bindSetExport();
    await env.button.click();
    assert.equal(env.status.textContent, 'Exportação cancelada.');
    assert.equal(env.downloads.length, 0);
    assert.equal(env.button.disabled, false);
});

test('write failure aborts the stream and allows retry', async () => {
    let aborted = false;
    const env = environment({picker: async () => ({createWritable: async () => ({
        write: async () => { throw new Error('disk full'); },
        close: async () => assert.fail('must not close after failed write'),
        abort: async () => { aborted = true; },
    })})});
    await env.context.bindSetExport();
    await env.button.click();
    assert.equal(aborted, true);
    assert.match(env.status.textContent, /Não foi possível salvar/);
    assert.equal(env.button.disabled, false);
});

test('unsupported browsers download the file and release the blob', async () => {
    const env = environment();
    await env.context.bindSetExport();
    await env.button.click();
    assert.deepEqual(env.downloads, ['Estratégia _ teste.set']);
    assert.deepEqual(env.revoked, ['blob:test']);
    assert.match(env.status.textContent, /Download iniciado/);
});

test('page loading failure cannot export incomplete configuration', async () => {
    const env = environment({fetchFails: true});
    await env.context.bindSetExport();
    await env.button.click();
    assert.equal(env.downloads.length, 0);
    assert.match(env.status.textContent, /Não foi possível carregar/);
    assert.equal(env.button.disabled, false);
});

test('filenames remove invalid characters, reserved names and duplicate extension', () => {
    const {context} = environment();
    assert.equal(context.setFileName('CON'), '_CON.set');
    assert.equal(context.setFileName('teste.set'), 'teste.set');
    assert.equal(context.setFileName('  '), 'Meu setup.set');
    assert.equal(context.setFileName('a:b?.'), 'a_b_.set');
});

test('invalid signals block both the save picker and downloads and allow retry', async () => {
    for (const supportsPicker of [true, false]) {
        let opened = false;
        const signalErrors = ['Condição 1: selecione o candle de A.'];
        const env = environment({signalErrors, picker: supportsPicker ? async () => { opened = true; } : undefined});
        await env.context.bindSetExport();
        await env.button.click();
        assert.equal(opened, false);
        assert.equal(env.downloads.length, 0);
        assert.match(env.status.textContent, /Corrija o Sinal.*Condição 1/);
        assert.equal(env.button.disabled, false);
        signalErrors.length = 0;
        if (!supportsPicker) {
            await env.button.click();
            assert.equal(env.downloads.length, 1);
        }
    }
});

test('invalid identity blocks export before opening a file', async () => {
    for (const name of ['', 'a'.repeat(49), 'teste\nInpMagic=42', 'teste|outro']) {
        let opened = false;
        const env = environment({picker: async () => { opened = true; }});
        env.stored.name = name;
        await env.context.bindSetExport();
        await env.button.click();
        assert.equal(opened, false);
        assert.match(env.status.textContent, /Corrija a identificação/);
    }
});

test('Magic generation stays in the Uni range and preserves numeric names', () => {
    const app = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
    const context = vm.createContext({TextEncoder});
    vm.runInContext(app.slice(app.indexOf('function magicNumberFromName'), app.indexOf('function bindMagicNumber')), context);
    for (const name of ['Meu setup', 'Estratégia / teste', 'ação 🚀', 'Setup 999']) {
        const magic = Number(context.magicNumberFromName(name));
        assert.ok(Number.isInteger(magic) && magic >= 1 && magic <= 2147483647);
        assert.equal(context.magicNumberFromName(name), context.magicNumberFromName('  ' + name + '  '));
    }
    assert.equal(context.magicNumberFromName('00042'), '42');
    assert.equal(context.magicNumberFromName('2147483647'), '2147483647');
});

function operationControls(overrides = {}) {
    return Object.entries({
        setup_market: 'B3', setup_mode: 'Swing trade', setup_timeframe: 'H4',
        setup_lot: '2,50', setup_direction: 'Somente venda',
        'operation-timeframe-start': 'M30', 'operation-timeframe-end': 'H4',
        'operation-direction-start': 'Compra e venda', 'operation-direction-end': 'Somente venda',
        ...overrides,
    }).map(([key, value]) => ({key, value}));
}

test('operation exports fixed values separately from enabled optimization bounds', () => {
    const {context} = environment();
    assert.deepEqual(Array.from(context.operationSetLines(operationControls())), [
        'InpMarket=1||1||1||1||N', 'InpTradeMode=1||1||1||1||N',
        'InpStrategyTimeframe=16388||30||1||16388||Y', 'InpLot=2.5||2.5||0.01||2.5||N',
        'InpDirection=2||0||1||2||Y',
    ]);
    const reversed = context.operationSetLines(operationControls({
        'operation-timeframe-start': 'MN1', 'operation-timeframe-end': 'Tempo corrente',
        'operation-direction-start': 'Somente venda', 'operation-direction-end': 'Somente compra',
    }));
    assert.equal(reversed[2], 'InpStrategyTimeframe=16388||0||1||49153||Y');
    assert.equal(reversed[4], 'InpDirection=2||1||1||2||Y');
    const fixed = context.operationSetLines(operationControls({
        'operation-timeframe-start': 'M5', 'operation-timeframe-end': 'M5',
    }));
    assert.equal(fixed[2], 'InpStrategyTimeframe=16388||5||1||5||N');
});

test('operation rejects missing fields, unknown enums and invalid volume', () => {
    const {context} = environment();
    for (const overrides of [
        {setup_market: 'other'}, {setup_mode: ''}, {setup_timeframe: 'H5'},
        {setup_direction: 'both'}, {'operation-timeframe-end': 'H5'},
        {'operation-direction-start': ''}, ...['', '0', '-1', 'Infinity', '1||2', '1.2.3'].map(setup_lot => ({setup_lot})),
    ]) {
        assert.throws(() => context.operationSetLines(operationControls(overrides)), {name: 'OperationValidationError'});
    }
    assert.throws(() => context.operationSetLines([]), {name: 'OperationValidationError'});
});

test('cached legacy templates export unnamed market, mode and lot controls', () => {
    const {context} = environment();
    const controls = operationControls();
    const legacyKeys = {setup_market: 'inicio_2', setup_mode: 'inicio_3', setup_lot: 'inicio_5'};
    const legacy = controls.map(control => ({...control, key: legacyKeys[control.key] || control.key}));
    assert.deepEqual(Array.from(context.operationSetLines(legacy)), Array.from(context.operationSetLines(controls)));
    // Stale unnamed fields must not override explicit fields or hide invalid values.
    assert.throws(() => context.operationSetLines([...legacy, {key: 'setup_lot', value: '0'}]), {name: 'OperationValidationError'});
});

test('invalid operation prevents writing and reports the card to fix', async () => {
    let opened = false;
    const env = environment({picker: async () => { opened = true; }});
    env.stored.lot = '0';
    await env.context.bindSetExport();
    await env.button.click();
    assert.equal(opened, false);
    assert.match(env.status.textContent, /Corrija Mercado e operação/);
});
