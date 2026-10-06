const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../static/export.js'), 'utf8');

function environment({picker, fetchFails = false} = {}) {
    const status = {textContent: ''};
    const button = {disabled: true, addEventListener(_, callback) { this.click = callback; }};
    const stored = {name: 'Estratégia / teste', lot: '0.25', end: '25'};
    const name = {name: 'setup_name', value: 'default', checked: false};
    const magic = {name: 'setup_magic', value: '1', checked: false};
    const lot = {name: '', id: '', value: '0.01', checked: false};
    const end = {name: 'period-end', value: '10', checked: false};
    const usage = {name: 'usage', value: 'Saída', checked: true};
    const roots = new Map(['inicio', 'indicadores', 'gestao'].map(page => [page, {
        controls: page === 'inicio' ? [name, magic, lot] : [end, usage],
        querySelector(selector) {
            if (selector.startsWith('[data-page=')) return this;
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
        magicNumberFromName: () => '12345',
        Blob,
        URL: {createObjectURL: () => 'blob:test', revokeObjectURL: url => revoked.push(url)},
        setTimeout: callback => callback(),
    });
    vm.runInContext(source, context);
    return {context, button, status, stored, downloads, revoked};
}

test('exports the latest configuration and confirms only after closing the file', async () => {
    let written, options, closed = false;
    const env = environment({picker: async value => {
        options = value;
        return {name: 'chosen.set', createWritable: async () => ({
            write: async contents => { written = JSON.parse(contents); },
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
