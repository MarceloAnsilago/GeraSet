// Presets are data: never execute comments or embedded content.
function decodeSetupSet(buffer) {
    const bytes = new Uint8Array(buffer);
    const encoding = bytes[0] === 0xff && bytes[1] === 0xfe ? 'utf-16le'
        : bytes[0] === 0xfe && bytes[1] === 0xff ? 'utf-16be'
        : bytes[1] === 0 ? 'utf-16le' : 'utf-8';
    return new TextDecoder(encoding, {fatal: true}).decode(bytes).replace(/^\uFEFF/, '');
}

function parseSetupSet(text) {
    const lines = text.split(/\r?\n/);
    const start = lines.findIndex(line => /^;\s*\{\s*$/.test(line));
    if (start < 0) throw new Error('Este arquivo não contém os dados do GeraSet. Use um set exportado pelo GeraSet.');
    let metadata;
    try {
        metadata = JSON.parse(lines.slice(start).filter(line => /^;/.test(line))
            .map(line => line.replace(/^;\s?/, '')).join('\n'));
    } catch { throw new Error('Os dados do GeraSet no arquivo estão incompletos ou inválidos.'); }
    if (!metadata || metadata.format !== 'geraset' || metadata.version !== 2)
        throw new Error('Formato antigo ou incompatível. Crie e exporte um novo set no GeraSet atual.');
    const pages = ['inicio', 'indicadores', 'gestao', 'configuracoes'];
    if (!metadata.pages || !pages.every(page => Array.isArray(metadata.pages[page]) &&
        metadata.pages[page].length > 0 && validSetupFields(metadata.pages[page])))
        throw new Error('O set atual deve conter todas as páginas com seus campos válidos.');
    const native = new Map();
    lines.forEach(line => {
        const match = /^(Inp\w+)=(.*)$/.exec(line);
        if (match) native.set(match[1], match[2]);
    });
    return {metadata, native};
}

function validSetupFields(fields) {
    return fields.every(field => field && typeof field.key === 'string' &&
        typeof field.value === 'string' && (field.checked === undefined || typeof field.checked === 'boolean'));
}

function legacyManagedStopGroups(native) {
    return [['trailing', 'InpTrailing'], ['moving-stop', 'InpMovingStop']].filter(([, prefix]) =>
        ['Mode', 'Trigger', 'Distance', 'Step'].every(suffix => !native.has(prefix+suffix)));
}

async function prepareSetupImport(parsed) {
    const state = {};
    const roots = new Map(await Promise.all(['inicio', 'indicadores', 'gestao', 'configuracoes'].map(async page => {
        const response = await fetch(`/${page}`);
        if (!response.ok) throw new Error('Não foi possível carregar os campos. Tente novamente.');
        const root = new DOMParser().parseFromString(await response.text(), 'text/html');
        if (!root.querySelector(`[data-page="${page}"]`)) throw new Error('Página de configuração inválida.');
        const controls = setupControls(root);
        const fields = parsed.metadata.pages[page];
        const apply = (control, index) => {
            const key = control.name || control.id || `${page}_${index}`;
            const legacyName = page === 'gestao' && /^(trailing|moving-stop)-(mode|trigger|distance|step)$/.test(key)
                ? `gestao_${index}` : null;
            const field = fields.find(entry => entry.key === key &&
                (control.type !== 'radio' || entry.value === control.value))
                || (legacyName && fields.find(entry => entry.key === legacyName));
            if (!field) return;
            if (control.type === 'checkbox' || control.type === 'radio') control.checked = Boolean(field.checked);
            else if (control.tagName !== 'SELECT' || Array.from(control.options).some(option => option.value === field.value)) {
                control.value = field.value;
            } else if (control.hasAttribute('data-condition-control') || control.hasAttribute('data-indicator-type') || control.hasAttribute('data-slot-timeframe-extra')
                || /^(trailing|moving-stop)-mode$/.test(control.name)) {
                throw new Error(`Opção inválida no arquivo: ${key}.`);
            }
        };
        // Indicator types must exist before restoring sources and their buffers.
        controls.forEach((control, index) => { if (control.hasAttribute('data-indicator-type')) apply(control, index); });
        updateCrossingOptions(root);
        controls.forEach(apply);
        if (page === 'gestao') {
            // Old exports kept these cards only in comments. Preserve their
            // effective disabled behavior, even if the old draft said enabled.
            for (const [key] of legacyManagedStopGroups(parsed.native)) {
                const mode = root.querySelector(`[name="${key}-mode"]`);
                if (mode) mode.value = 'Desativado';
            }
        }
        if (page === "indicadores" && typeof initializeSignalBankDirections === "function") initializeSignalBankDirections(root);
        if (page === 'gestao') state.pendingMirrorSell = Boolean(root.querySelector('[name="pending_mirror_sell"]')?.checked);
        state[page] = controls.map(control => ({value: control.value, checked: control.checked}));
        return [page, root];
    })));
    const tester = parsed.native.get('InpTesterAutoStart');
    if (tester !== undefined) {
        if (!['true', 'false', '1', '0'].includes(tester)) throw new Error('InpTesterAutoStart inválido.');
        state.testerAutoStart = tester === 'true' || tester === '1';
    }
    // Validate with the same rules used by export, before changing localStorage.
    const exported = parseSetupSet(decodeSetupSet(serializeSetupSet(roots, state).contents));
    validateSetupInputs(parsed.native, exported.native);
    return state;
}

function validateSetupInputs(actual, expected) {
    const legacy = new Set(legacyManagedStopGroups(actual).flatMap(([, prefix]) => {
        const keys = ['Mode', 'Trigger', 'Distance', 'Step'].map(suffix => prefix+suffix);
        // Only an entirely absent group may migrate, and only to disabled/zero.
        return keys.every(key => /^0\|\|0\|\|(?:1|0\.01)\|\|0\|\|N$/.test(expected.get(key) || '')) ? keys : [];
    }));
    for (const [key, value] of expected) {
        if (legacy.has(key)) continue;
        if (actual.get(key) !== value)
            throw new Error(`O parâmetro ${key} está ausente ou difere dos dados salvos. Crie um novo set no GeraSet atual.`);
    }
    if (actual.size !== expected.size - legacy.size)
        throw new Error('O arquivo contém parâmetros incompatíveis com o formato atual.');
}

function bindSetImport() {
    const button = document.querySelector('[data-import-set]');
    const input = document.querySelector('[data-import-file]');
    const status = document.querySelector('[data-import-status]');
    if (!button || !input || !status) return;
    const message = sessionStorage.getItem('geraset-import-message');
    if (message) { status.textContent = message; sessionStorage.removeItem('geraset-import-message'); }
    button.addEventListener('click', () => { input.value = ''; input.click(); });
    input.addEventListener('change', async () => {
        const file = input.files?.[0];
        if (!file) return;
        button.disabled = true;
        status.textContent = 'Carregando e validando set...';
        try {
            if (!/\.set$/i.test(file.name) || file.size > 5 * 1024 * 1024) throw new Error('Escolha um arquivo .set de até 5 MB.');
            const parsed = parseSetupSet(decodeSetupSet(await file.arrayBuffer()));
            const state = await prepareSetupImport(parsed);
            localStorage.setItem(setupStorageKey, JSON.stringify(state));
            const migrated = legacyManagedStopGroups(parsed.native);
            sessionStorage.setItem('geraset-import-message', `Set carregado: ${file.name}. Confira os parâmetros e as condições em Indicadores.`
                + (migrated.length ? ` Arquivo anterior à exportação de ${migrated.map(([key]) => key === 'trailing' ? 'trailing stop' : 'stop móvel').join(' e ')}: mantidos desativados; revise antes de habilitar.` : ''));
            window.location.reload();
        } catch (error) { status.textContent = `Não foi possível carregar: ${error.message}`; }
        finally { button.disabled = false; }
    });
}

document.addEventListener('DOMContentLoaded', bindSetImport);
