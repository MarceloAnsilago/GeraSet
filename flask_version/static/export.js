function indicatorUsageErrors(root) {
    const seen = new Map(), errors = [];
    for (let slot = 1; slot <= 4; slot++) {
        const type = root.querySelector(`[data-indicator-type="${slot}"]`)?.value;
        if (!type || type === 'Não usar' || type === 'Média Móvel') continue;
        const usage = root.querySelector(`[name="indicator-usage-${slot}"]:checked`)?.value;
        const key = `${type}|${usage}`;
        if (seen.has(key)) errors.push(`Indicadores ${seen.get(key)} e ${slot}: ${type} permite apenas uma Entrada e uma Saída. Altere o tipo ou a finalidade de um deles.`);
        else seen.set(key, slot);
    }
    return errors;
}

function setFileName(name) {
    const base = name.trim().replace(/\.set$/i, "")
        .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
        .replace(/[. ]+$/g, "").slice(0, 120) || "Meu setup";
    return `${/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(base) ? `_${base}` : base}.set`;
}

// Numeric values must match UniTypes.mqh and ENUM_UNI_TIMEFRAME in UniInputOptions.mqh.
const operationEnums = {
    setup_market: {Forex: 0, B3: 1},
    setup_mode: {"Day trade": 0, "Swing trade": 1},
    setup_direction: {"Compra e venda": 0, "Somente compra": 1, "Somente venda": 2},
    setup_timeframe: {
        "Tempo corrente": 0, M1: 1, M2: 2, M3: 3, M4: 4, M5: 5, M6: 6,
        M10: 10, M12: 12, M15: 15, M20: 20, M30: 30,
        H1: 16385, H2: 16386, H3: 16387, H4: 16388, H6: 16390,
        H8: 16392, H12: 16396, D1: 16408, W1: 32769, MN1: 49153,
    },
};

function operationSetLines(controls) {
    const values = Object.fromEntries(controls.map(control => [control.key, control.value]));
    const fail = message => {
        const error = new Error(message);
        error.name = "OperationValidationError";
        throw error;
    };
    const enumValue = (key, field = key) => {
        const options = operationEnums[key];
        if (!Object.prototype.hasOwnProperty.call(options, values[field])) {
            fail(`Selecione uma opção válida em ${field}.`);
        }
        return options[values[field]];
    };
    const fixed = (input, value, step = 1) => `${input}=${value}||${value}||${step}||${value}||N`;
    const range = (input, key, prefix) => {
        const value = enumValue(key);
        const a = enumValue(key, `${prefix}-start`);
        const b = enumValue(key, `${prefix}-end`);
        // The review counts inclusive options in either direction. MT5 needs ascending bounds.
        return `${input}=${value}||${Math.min(a, b)}||1||${Math.max(a, b)}||${a === b ? "N" : "Y"}`;
    };
    const lotText = String(values.setup_lot ?? "").trim().replace(",", ".");
    const lot = Number(lotText);
    if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(lotText) || !Number.isFinite(lot) || lot <= 0) {
        fail("Lote deve ser um número maior que zero.");
    }
    return [
        fixed("InpMarket", enumValue("setup_market")),
        fixed("InpTradeMode", enumValue("setup_mode")),
        fixed("InpLot", lot, 0.01),
        range("InpDirection", "setup_direction", "operation-direction"),
    ];
}

function scheduleSetLines(controls) {
    const values = Object.fromEntries(controls.map(control => [control.key, control.value]));
    const fail = message => {
        const error = new Error(message);
        error.name = "ScheduleValidationError";
        throw error;
    };
    const minutes = key => {
        const value = values[key];
        if (typeof value !== "string" || !/^(?:[01]\d|2[0-3]):[0-5][05]$/.test(value)) {
            fail("Selecione horários entre 00:00 e 23:55, em passos de 5 minutos.");
        }
        const [hour, minute] = value.split(":").map(Number);
        return hour * 60 + minute;
    };
    const start = minutes("setup_entry_start");
    const end = minutes("setup_entry_end");
    if (start === end) fail("Início e encerramento das entradas devem ser diferentes.");
    return [["InpEntryStart", start, "entry-start"], ["InpEntryEnd", end, "entry-end"]].map(([input, value, key]) => {
        const a = minutes(`schedule-${key}-start`);
        const b = minutes(`schedule-${key}-end`);
        return `${input}=${value}||${Math.min(a, b)}||5||${Math.max(a, b)}||${a === b ? "N" : "Y"}`;
    });
}

function orderSetLines(controls) {
    const values = Object.fromEntries(controls.map(control => [control.key, control.value]));
    const fail = message => { const error = new Error(message); error.name = 'OrderValidationError'; throw error; };
    const choice = (key, options) => { const index = options.indexOf(values[key]); if (index < 0) fail(`Confira ${key}.`); return index; };
    const integer = (key, min = 1) => {
        const value = values[key];
        if (value === undefined || String(value).trim() === '' || !Number.isInteger(Number(value)) || Number(value) < min || Number(value) > 100000) fail('Vela e intervalo devem ser inteiros de 1 a 100000; use 0/0/0 para desativar a otimização.');
        return Number(value);
    };
    const mode = choice('order_mode', ['A mercado', 'Pendente']);
    const fixed = (name, value) => `${name}=${value}||${value}||1||${value}||N`;
    const mirror = controls.find(control => control.key === 'pending_mirror_sell')?.checked ?? false;
    const mirrorLine = `InpPendingMirrorSell=${Boolean(mirror)}`;
    if (mode === 0) return [fixed('InpOrderMode', 0), fixed('InpPendingReference', 0), fixed('InpPendingCandle', 1), mirrorLine];
    const options = ['Máxima', 'Mínima', 'Abertura', 'Fechamento'];
    const reference = choice('pending_reference', options);
    const a = choice('pending-reference-start', options), b = choice('pending-reference-end', options);
    const bar = integer('pending_bar');
    const bounds = ['start', 'step', 'end'].map(bound => values[`pending-bar-${bound}`]);
    const inactive = bounds.every(value => value !== undefined && String(value).trim() !== '' && Number(value) === 0);
    let start = bar, step = 1, end = bar;
    if (!inactive) {
        start = integer('pending-bar-start'); step = integer('pending-bar-step'); end = integer('pending-bar-end');
        if (end < start) fail('O fim da otimização da vela deve ser maior ou igual ao início.');
    }
    return [fixed('InpOrderMode', mode),
        `InpPendingReference=${reference}||${Math.min(a, b)}||1||${Math.max(a, b)}||${a === b ? 'N' : 'Y'}`,
        `InpPendingCandle=${bar}||${start}||${step}||${end}||${start === end ? 'N' : 'Y'}`, mirrorLine];
}

function targetSetLines(controls) {
    const values = Object.fromEntries(controls.map(c => [c.key, c.value]));
    const fail = message => { const error = new Error(message); error.name = 'TargetValidationError'; throw error; };
    const choice = (key, options) => {
        const index = options.indexOf(values[key]);
        if (index < 0) fail(`Confira ${key} em Alvos.`);
        return index;
    };
    const number = raw => {
        const text = String(raw ?? '').trim().replace(',', '.');
        if (!/^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/.test(text) || Number(text) > 100000000) fail('Use valores de 0 a 100000000 com até duas casas decimais em Alvos.');
        return Number(text);
    };
    const fixed = (input, value) => `${input}=${value}||${value}||1||${value}||N`;
    const numeric = (input, value, key) => {
        const bounds = ['start', 'step', 'end'].map(b => number(values[`target-${key}-${b}`]));
        let [start, step, end] = bounds;
        if (bounds.every(n => n === 0)) { start = value; step = 0.01; end = value; }
        else if (step <= 0 || end < start) fail('Confira início, passo e fim da otimização dos alvos.');
        return `${input}=${value}||${start}||${step}||${end}||${start === end ? 'N' : 'Y'}`;
    };
    const enumRange = (input, value, key, options, offset = 0) => {
        const a = choice(`target-${key}-start`, options) + offset;
        const b = choice(`target-${key}-end`, options) + offset;
        return `${input}=${value}||${Math.min(a,b)}||1||${Math.max(a,b)}||${a === b ? 'N' : 'Y'}`;
    };
    const mode = choice('target_take_mode', ['Vezes o stop', 'Distância fixa']);
    // Cached templates without the selector retain the former distance + candle behavior.
    const stopMode = values.target_stop_mode === undefined ? 0 : choice('target_stop_mode', ['Distância + candle', 'Distância fixa']);
    const candles = ['último', 'Penúltimo', 'Antepenúltimo'], sizes = ['Total com pavios', 'Corpo'];
    return [fixed('InpTargetUnit', choice('target_unit', ['Pontos', 'Porcentagem'])),
        fixed('InpStopMode', stopMode),
        numeric('InpStopLoss', number(values.target_stop), 'stop'),
        fixed('InpStopCandleMultiplier', stopMode === 1 ? 0 : number(values.target_stop_multiplier)),
        stopMode === 1 ? fixed('InpStopCandle', 1) : enumRange('InpStopCandle', choice('target_candle', candles) + 1, 'candle', candles, 1),
        stopMode === 1 ? fixed('InpStopBody', 0) : enumRange('InpStopBody', choice('target_size', sizes), 'size', sizes),
        fixed('InpTakeMode', mode),
        mode === 1 ? numeric('InpTakeProfit', number(values.target_take_distance), 'take-distance') : fixed('InpTakeProfit', 0),
        mode === 0 ? numeric('InpTakeStopMultiplier', number(values.target_take_multiplier), 'take-multiplier') : fixed('InpTakeStopMultiplier', 0)];
}

function breakevenSetLines(controls) {
    const values = Object.fromEntries(controls.map(c => [c.key, c.value]));
    const fail = message => { const e = new Error(message); e.name = 'BreakevenValidationError'; throw e; };
    const mode = ['Desativado', 'Pontos', 'Porcentagem'].indexOf(values['breakeven-mode'] ?? 'Desativado');
    if (mode < 0) fail('Selecione o modo do breakeven.');
    const fixed = (name, value) => `${name}=${value}||${value}||0.01||${value}||N`;
    const lines = [`InpBreakevenMode=${mode}||${mode}||1||${mode}||N`];
    if (!mode) return [...lines, fixed('InpBreakevenTrigger', 0), fixed('InpBreakevenOffset', 0)];
    const number = (raw, positive = false) => {
        const text = String(raw ?? '').trim().replace(',', '.');
        if (!/^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/.test(text)) fail('Breakeven: use valores com até duas casas decimais.');
        const n = Number(text);
        if (!Number.isFinite(n) || n > 100000000 || (positive && n <= 0)) fail('Breakeven: confira os valores e o passo.');
        return n;
    };
    const trigger = number(values['breakeven-trigger'], true), offset = number(values['breakeven-offset']);
    if (offset >= trigger) fail('Breakeven: proteção deve ser menor que a ativação.');
    const ranges = [];
    for (const [input, value, key] of [['InpBreakevenTrigger', trigger, 'activate'], ['InpBreakevenOffset', offset, 'distance']]) {
        const raw = ['start', 'step', 'end'].map(b => values[`breakeven-${key}-${b}`]);
        let start = value, step = 0.01, end = value;
        if (!raw.every(v => String(v ?? '').trim() !== '' && Number(String(v).replace(',', '.')) === 0)) {
            start = number(raw[0], key === 'activate'); step = number(raw[1], true); end = number(raw[2], key === 'activate');
            if (end < start) fail('Breakeven: fim da otimização menor que o início.');
        }
        ranges.push([start, end]);
        lines.push(`${input}=${value}||${start}||${step}||${end}||${start === end ? 'N' : 'Y'}`);
    }
    if (ranges[1][1] >= ranges[0][0]) fail('Breakeven: toda proteção otimizada deve ser menor que a menor ativação.');
    return lines;
}

function indicatorSignalSetLines(root) {
    if (!root) throw new Error("Página de indicadores ausente.");
    const lines = [], types = [];
    const fail = message => { const e = new Error(message); e.name = "SignalValidationError"; throw e; };
    const usageErrors = indicatorUsageErrors(root);
    if (usageErrors.length) fail(usageErrors.join(" "));
    const read = id => root.querySelector(`[id="${id}"]`)?.value;
    const number = (value, min, max, decimal = false) => {
        if (value === undefined || String(value).trim() === "" || !(decimal ? Number.isFinite(Number(value)) : Number.isInteger(Number(value))) || Number(value) < min || Number(value) > max) fail("Confira os parâmetros e intervalos dos indicadores.");
        return Number(value);
    };
    const choices = (value, options) => { const n = options.indexOf(value); if (n < 0) fail("Opção de indicador inválida."); return n; };
    const numeric = (input, slot, kind, index, title, min, max, decimal = false) => {
        const value = number(read(`param-${slot}-${kind}-${index}`), min, max, decimal);
        const bounds = [1, 2, 3].map(i => read(`opt-${slot}-${kind}-${i}-${title}`));
        const inactive = bounds.every(v => Number(v) === 0 && String(v).trim() !== "");
        let start = value, step = 1, end = value;
        if (!inactive) {
            start = number(bounds[0], min, max, decimal); step = number(bounds[1], decimal ? 0.01 : 1, 200000, decimal); end = number(bounds[2], min, max, decimal);
            if (end < start) fail("O fim da otimização do indicador deve ser maior ou igual ao início.");
        }
        lines.push(`${input}=${value}||${start}||${step}||${end}||${!inactive && start !== end ? "Y" : "N"}`);
    };
    const combo = (input, slot, kind, index, title, options, offset = 0) => {
        const value = choices(read(`combo-${slot}-${kind}-${index}`), options) + offset;
        const bounds = ['start', 'end'].map(bound => choices(root.querySelector(`[name="opt-combo-${slot}-${kind}-${title}-${bound}"]`)?.value, options) + offset);
        lines.push(`${input}=${value}||${Math.min(...bounds)}||1||${Math.max(...bounds)}||${bounds[0] === bounds[1] ? "N" : "Y"}`);
    };
    for (let i = 1; i <= 4; i++) {
        const type = root.querySelector(`[data-indicator-type="${i}"]`)?.value;
        const n = choices(type, ['Não usar', 'Média Móvel', 'RSI', 'ADX']) - 1;
        types.push(type);
        const usage = root.querySelector(`[name="indicator-usage-${i}"]:checked`)?.value;
        const exit = choices(usage, ['Entrada', 'Saída']);
        const frameOptions = Object.keys(operationEnums.setup_timeframe);
        const frame = root.querySelector(`[name="indicator-timeframe-${i}"]`)?.value || 'Tempo corrente';
        const bounds = ['start', 'end'].map(bound => root.querySelector(`[name="indicator-timeframe-${i}-${bound}"]`)?.value || frame);
        const tf = choices(frame, frameOptions), startFrame = choices(bounds[0], frameOptions), endFrame = choices(bounds[1], frameOptions);
        lines.push(`InpIndicator${i}Timeframe=${tf}||${n < 0 ? tf : Math.min(startFrame, endFrame)}||1||${n < 0 ? tf : Math.max(startFrame, endFrame)}||${n >= 0 && startFrame !== endFrame ? 'Y' : 'N'}`);
        const instance = exit ? 'Exit' : 'Entry';
        lines.push(`InpIndicator${i}Type=${n}||${n}||1||${n}||N`, `InpIndicator${i}Exit=${exit}||${exit}||1||${exit}||N`);
        const prices = ['Close', 'Open', 'High', 'Low', 'Median', 'Typical', 'Weighted'];
        if (n === 0) {
            numeric(`InpIndicator${i}MaPeriod`, i, type, 1, 'Período', 1, 100000);
            numeric(`InpIndicator${i}MaShift`, i, type, 2, 'Shift', -100000, 100000);
            combo(`InpIndicator${i}MaPrice`, i, type, 1, 'Preço aplicado', prices, 1);
            combo(`InpIndicator${i}MaMethod`, i, type, 2, 'Método', ['SMA', 'EMA', 'SMMA', 'LWMA']);
        } else if (n === 1) {
            numeric(`InpRsi${instance}Period`, i, type, 1, 'Período', 1, 100000);
            combo(`InpRsi${instance}Price`, i, type, 1, 'Preço aplicado', prices, 1);
            numeric(`InpRsi${instance}Lower`, i, type, 2, 'Sobrevenda', 0, 100, true);
            numeric(`InpRsi${instance}Upper`, i, type, 3, 'Sobrecompra', 0, 100, true);
            numeric(`InpRsi${instance}Middle`, i, type, 4, 'Nível médio', 0, 100, true);
            if (!(Number(read(`param-${i}-RSI-2`)) < Number(read(`param-${i}-RSI-4`)) && Number(read(`param-${i}-RSI-4`)) < Number(read(`param-${i}-RSI-3`)))) fail('RSI: use nível inferior < médio < superior.');
        } else if (n === 2) numeric(`InpAdx${instance}Period`, i, type, 1, 'Período', 1, 100000);
    }
    const priceSources = ['Fechamento da vela', 'Abertura da vela', 'Máxima da vela', 'Mínima da vela', 'Abertura do dia', 'Máxima do dia', 'Mínima do dia', 'Máxima do dia anterior', 'Mínima do dia anterior', 'Valor fixo'];
    const source = label => {
        if (priceSources.includes(label)) return priceSources.indexOf(label);
        for (let i = 0; i < types.length; i++) {
            if (types[i] === 'Não usar') continue;
            const definition = indicatorSignalSources(types[i], i + 1).find(line => line.source === label);
            if (definition) return definition.wire;
        }
        fail("Buffer não encontrado nos indicadores selecionados.");
    };
    const card = root.querySelector('[data-conditions]');
    const rows = Array.from(card.querySelectorAll('.condition-row'));
    const unit = choices(card.querySelector('[data-unit-selector]').value, ['N.usar', 'Pontos', 'Porcentagem']);
    const candles = ['Vela atual', 'Anterior', 'Penúltima', 'Antepenúltima'];
    const comparisons = ['Maior que', 'Menor que', 'Maior ou igual que', 'Menor ou igual que', 'Igual que', 'Diferente de', 'Toque', 'Cruzar p/ cima de', 'Cruzar p/ baixo de', 'Cruzar&fechar acima de', 'Cruzar&fechar abaixo de'];
    for (let i = 0; i < 10; i++) {
        const rule = rows[i] ? readSignalRow(rows[i]) : null;
        let payload = '';
        if (rule && signalRowActive(rule)) {
            const errors = signalRuleErrors(rule, card.querySelector('[data-unit-selector]').value);
            if (errors.length) fail(errors.join(' '));
            payload = [choices(rule.operator, ['Se', 'E', 'Ou']) + 1, choices(rule.usage, ['Entrada', 'Saída']), signalResultSide(rule) === 'Compra' ? 1 : -1,
                source(rule.target), signalConstantSource(rule.target) ? 0 : choices(rule.targetCandle, candles), choices(rule.comparison, comparisons), source(rule.reference),
                signalConstantSource(rule.reference) ? 0 : choices(rule.referenceCandle, candles), rule.reference === 'Valor fixo' ? Number(rule.fixed) : 0, Number(rule.distance), unit].join(',');
            if (/[eE]/.test(payload)) fail("Use valores decimais sem notação exponencial nas condições.");
        }
        lines.push(`InpSignal${i + 1}=${payload}`);
    }
    return lines;
}

function serializeSetupSet(roots, state = typeof readSetupState === "function" ? readSetupState() : {}) {
    const pages = {};
    let name = "Meu setup";
    let magic = "";
    for (const [page, root] of roots) {
        restoreSetup(root, page, state);
        const signalErrors = validateSignalCard(root.querySelector("[data-conditions]"));
        if (signalErrors.length) {
            const error = new Error(signalErrors.join(" "));
            error.name = "SignalValidationError";
            throw error;
        }
        const nameControl = root.querySelector("[data-setup-name]");
        if (nameControl) {
            name = nameControl.value.trim();
            magic = magicNumberFromName(name);
            if (!name || name.length > 48 || /[\u0000-\u001f\u007f|]/.test(name) ||
                !/^[0-9]+$/.test(magic) || Number(magic) < 1 || Number(magic) > 2147483647) {
                const error = new Error("Use um nome de 1 a 48 caracteres, sem controles ou |, e Magic de 1 a 2147483647.");
                error.name = "IdentityValidationError";
                throw error;
            }
            root.querySelector("[data-setup-magic]").value = magic;
        }
        // Keep every control in storage order, including optimization ranges and
        // inactive options, so no configuration is lost during export.
        pages[page] = setupControls(root).map((control, index) => ({
            key: control.name || control.id || `${page}_${index}`,
            value: control.value,
            checked: control.checked,
        }));
    }
    if (!magic) throw new Error("Identificação do setup ausente.");
    // Preserve the full draft as comments; only mapped inputs are applied by MT5.
    const metadata = JSON.stringify({format: "geraset", version: 2, name, pages}, null, 2);
    const text = [
        "; GeraSet -> UniEA: identificacao, mercado e operacao, horarios",
        `InpName=${name}`,
        `InpMagic=${magic}||${magic}||1||2147483647||N`,
        ...operationSetLines(pages.inicio || []),
        ...scheduleSetLines(pages.inicio || []),
        ...orderSetLines(pages.gestao || []),
        ...targetSetLines(pages.gestao || []),
        ...breakevenSetLines(pages.gestao || []),
        ...indicatorSignalSetLines(roots.get('indicadores')),
        `InpExibirHistogramas=${pages.configuracoes?.find(control => control.key === 'show_signal_histograms')?.checked ?? true}`,
        'InpHistogramasBarras=300',
        `InpExibirPainel=${pages.configuracoes?.find(control => control.key === 'show_mt5_panel')?.checked ?? true}`,

        ...(typeof state.testerAutoStart === "boolean"
            ? [`InpTesterAutoStart=${state.testerAutoStart}`] : []),
        ...metadata.split("\n").map(line => `; ${line}`),
        "",
    ].join("\r\n");
    // Explicit UTF-16LE with BOM preserves accents in native Windows MT5 presets.
    const contents = new Uint8Array(2 + text.length * 2);
    contents[0] = 0xff;
    contents[1] = 0xfe;
    for (let i = 0; i < text.length; i++) {
        contents[2 + i * 2] = text.charCodeAt(i) & 0xff;
        contents[3 + i * 2] = text.charCodeAt(i) >>> 8;
    }
    return {filename: setFileName(name), contents};
}

async function writeSetupSet(handle, contents) {
    const writable = await handle.createWritable();
    try {
        await writable.write(contents);
        await writable.close();
    } catch (error) {
        try { await writable.abort(); } catch { /* Preserve the original error. */ }
        throw error;
    }
}

function downloadSetupSet(file) {
    const url = URL.createObjectURL(new Blob([file.contents], {type: "application/octet-stream"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = file.filename;
    document.body.appendChild(link);
    try { link.click(); }
    finally {
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
    }
}

async function bindSetExport() {
    const button = document.querySelector("[data-export-set]");
    const status = document.querySelector("[data-export-status]");
    if (!button || !status) return;
    let roots;
    const supportsPicker = typeof window.showSaveFilePicker === "function";
    const readyMessage = supportsPicker
        ? "Escolha a pasta e o nome do arquivo ao exportar."
        : "A exportação usa o download do navegador. Para escolher a pasta, ative a opção de perguntar onde salvar os downloads.";

    async function loadPages() {
        const entries = await Promise.all(["inicio", "indicadores", "gestao", "configuracoes"].map(async page => {
            const response = await fetch(`/${page}`);
            if (!response.ok) throw new Error("Falha ao carregar o set");
            const root = new DOMParser().parseFromString(await response.text(), "text/html");
            if (!root.querySelector(`[data-page="${page}"]`)) throw new Error("Página inválida");
            return [page, root];
        }));
        return new Map(entries);
    }

    button.addEventListener("click", async () => {
        button.disabled = true;
        if (!roots) {
            try {
                status.textContent = "Preparando exportação...";
                roots = await loadPages();
                status.textContent = readyMessage;
                button.textContent = "Exportar set";
            } catch {
                status.textContent = "Não foi possível carregar o set. Clique para tentar novamente.";
            } finally { button.disabled = false; }
            return;
        }
        try {
            const file = serializeSetupSet(roots);
            if (supportsPicker) {
                // Open directly from the click; awaiting a fetch first would
                // lose the user activation required by the browser.
                const handle = await window.showSaveFilePicker({
                    id: "geraset-export",
                    suggestedName: file.filename,
                    types: [{description: "Set do GeraSet", accept: {"application/octet-stream": [".set"]}}],
                    excludeAcceptAllOption: true,
                });
                status.textContent = "Salvando set...";
                await writeSetupSet(handle, file.contents);
                status.textContent = `Set salvo: ${handle.name || file.filename}`;
            } else {
                downloadSetupSet(file);
                status.textContent = `Download iniciado: ${file.filename}. O local segue a configuração do navegador.`;
            }
        } catch (error) {
            status.textContent = error.name === "IdentityValidationError"
                ? `Corrija a identificação: ${error.message}`
                : error.name === "OperationValidationError"
                ? `Corrija Mercado e operação: ${error.message}`
                : error.name === "ScheduleValidationError"
                ? `Corrija Horários: ${error.message}`
                : error.name === "OrderValidationError"
                ? `Corrija Ordem em Gestão: ${error.message}`
                : error.name === "TargetValidationError"
                ? `Corrija Alvos em Gestão: ${error.message}`
                : error.name === "SignalValidationError"
                ? `Corrija o Sinal em Indicadores antes de exportar: ${error.message}`
                : error.name === "AbortError"
                ? "Exportação cancelada."
                : "Não foi possível salvar o set. Tente novamente e confira a permissão da pasta escolhida.";
        } finally { button.disabled = false; }
    });

    try {
        roots = await loadPages();
        status.textContent = readyMessage;
    } catch {
        button.textContent = "Tentar novamente";
        status.textContent = "Não foi possível carregar o set. Clique para tentar novamente.";
    } finally { button.disabled = false; }
}

document.addEventListener("DOMContentLoaded", bindSetExport);
