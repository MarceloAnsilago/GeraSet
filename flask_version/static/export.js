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
    // Older cached inicio templates had three unnamed controls. These are their
    // original storage positions; prefer explicit names whenever present.
    for (const [name, legacyKey] of Object.entries({
        setup_market: "inicio_2", setup_mode: "inicio_3", setup_lot: "inicio_5",
    })) {
        if (!(name in values) && legacyKey in values) values[name] = values[legacyKey];
    }
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
        range("InpStrategyTimeframe", "setup_timeframe", "operation-timeframe"),
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

function serializeSetupSet(roots) {
    const pages = {};
    let name = "Meu setup";
    let magic = "";
    for (const [page, root] of roots) {
        restoreSetup(root, page);
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
    const metadata = JSON.stringify({format: "geraset", version: 1, name, pages}, null, 2);
    const text = [
        "; GeraSet -> UniEA: identificacao, mercado e operacao, horarios",
        `InpName=${name}`,
        `InpMagic=${magic}||${magic}||1||2147483647||N`,
        ...operationSetLines(pages.inicio || []),
        ...scheduleSetLines(pages.inicio || []),
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
        const entries = await Promise.all(["inicio", "indicadores", "gestao"].map(async page => {
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
