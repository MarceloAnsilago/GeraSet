const setupStorageKey = "geraset-flask-cards-v1";

function readSetupState() {
    try { return JSON.parse(localStorage.getItem(setupStorageKey)) || {}; }
    catch { return {}; }
}

function setupControls(root) {
    const controls = Array.from(root.querySelectorAll(".card input:not(.tab-radio), .card select"));
    // Append new condition controls to preserve existing positional saved setups.
    return [...controls.filter(control => !control.hasAttribute("data-condition-control")),
        ...controls.filter(control => control.hasAttribute("data-condition-control"))];
}

function restoreSetup(root, page) {
    let saved = readSetupState()[page] || [];
    if (page === "indicadores" && saved.length >= setupControls(root).length + 36) {
        // Previous indicator cards had one signal and two optimization bounds per kind.
        const removed = new Set([8, 13, 16, 30, 31, 43, 44, 51, 52]);
        saved = saved.filter((_, index) => index >= 212 || !removed.has(index % 53));
    }
    if (page === "indicadores" && saved.length === setupControls(root).length + 4) {
        const legacyCount = setupControls(root).filter(control => !control.hasAttribute("data-condition-control")).length;
        saved.splice(legacyCount, 4);
    }
    setupControls(root).forEach((control, index) => {
        if (control.hasAttribute("data-crossing-source")) updateCrossingOptions(root);
        const value = saved[index];
        if (!value) return;
        if (control.type === "radio" || control.type === "checkbox") control.checked = value.checked;
        else if (control.tagName !== "SELECT" || Array.from(control.options).some(option => option.value === value.value)) {
            control.value = value.value;
        }
    });
    updateCrossingOptions(root);
}

function updateCrossingOptions(root) {
    const indicators = Array.from(root.querySelectorAll("[data-indicator-type]"))
        .filter(select => select.value !== "Não usar")
        .map(select => `Indicador ${select.dataset.indicatorType}: ${select.value}`);
    root.querySelectorAll("[data-crossing-source]").forEach(select => {
        const selected = select.value;
        Array.from(select.options).filter(option => option.dataset.indicatorOption).forEach(option => option.remove());
        indicators.forEach(value => {
            const option = select.ownerDocument.createElement("option");
            option.value = value;
            option.textContent = value;
            option.dataset.indicatorOption = "true";
            select.appendChild(option);
        });
        select.value = Array.from(select.options).some(option => option.value === selected) ? selected : select.options[0].value;
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector('[data-page="indicadores"]');
    if (!root) return;
    root.addEventListener("change", event => {
        if (event.target.matches("[data-indicator-type]")) updateCrossingOptions(root);
    });
});

// Restore before visibility, summaries and generated values are initialized.
document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-page]");
    if (root) restoreSetup(root, root.dataset.page);
});

function magicNumberFromName(name) {
    const text = name.trim();
    if (!text) return "";
    if (/^[0-9]+$/.test(text)) return text;

    let crc = 0xffffffff;
    for (const byte of new TextEncoder().encode(text)) {
        crc ^= byte;
        for (let bit = 0; bit < 8; bit++) {
            crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
        }
    }
    return String((crc ^ 0xffffffff) >>> 0);
}

function bindMagicNumber() {
    const name = document.querySelector("[data-setup-name]");
    const magic = document.querySelector("[data-setup-magic]");
    if (!name || !magic) return;
    const update = () => { magic.value = magicNumberFromName(name.value); };
    name.addEventListener("input", update);
    update();
}

document.addEventListener("DOMContentLoaded", bindMagicNumber);

function setVisible(elements, visible) {
    elements.forEach((element) => {
        element.classList.toggle("is-hidden", !visible);
    });
}

function bindRulesVisibility() {
    const orderSelect = document.querySelector("[data-rule-order]");
    const pendingFields = Array.from(document.querySelectorAll("[data-pending-fields]"));

    if (orderSelect) {
        const updateOrder = () => {
            setVisible(pendingFields, orderSelect.value === "Pendente");
        };
        orderSelect.addEventListener("change", updateOrder);
        updateOrder();
    }

    const candleCondition = document.querySelector("[data-candle-condition]");
    const candleCommon = Array.from(document.querySelectorAll("[data-candle-common]"));
    const candleSize = Array.from(document.querySelectorAll("[data-candle-size]"));
    const candleWicks = Array.from(document.querySelectorAll("[data-candle-wicks]"));

    if (candleCondition) {
        const updateCandleFilter = () => {
            const condition = candleCondition.value;
            setVisible(candleCommon, condition !== "Desativado");
            setVisible(candleSize, condition === "Candles");
            setVisible(candleWicks, condition === "Pavios");
        };
        candleCondition.addEventListener("change", updateCandleFilter);
        updateCandleFilter();
    }

    const takeMode = document.querySelector("[data-take-mode]");
    const takeMultiplier = Array.from(document.querySelectorAll("[data-take-multiplier]"));
    const takeDistance = Array.from(document.querySelectorAll("[data-take-distance]"));

    if (takeMode) {
        const updateTakeProfit = () => {
            const usesMultiplier = takeMode.value === "Vezes o stop";
            setVisible(takeMultiplier, usesMultiplier);
            setVisible(takeDistance, !usesMultiplier);
            [...takeMultiplier, ...takeDistance].forEach((group) => {
                const hidden = group.classList.contains("is-hidden");
                group.querySelectorAll("input, select").forEach((control) => {
                    control.disabled = hidden;
                });
            });
        };
        takeMode.addEventListener("change", updateTakeProfit);
        updateTakeProfit();
    }
}

document.addEventListener("DOMContentLoaded", bindRulesVisibility);

function updateIndicatorSummary(select, fields, summary) {
    const values = summary.querySelector("[data-indicator-summary-values]");
    values.replaceChildren();
    const addLine = (text) => {
        const line = document.createElement("p");
        line.textContent = text;
        values.appendChild(line);
    };
    if (select.value === "Não usar") {
        addLine("Sem parâmetros ativos.");
        return;
    }
    const usage = select.closest(".indicator-card").querySelector("[data-indicator-usage] input:checked");
    addLine(`Usar como: ${usage.value === "Saída" ? "Saída" : "Entrada"}`);
    fields.querySelectorAll(".tab-panel-params [data-indicator-kind]").forEach((group) => {
        if (group.dataset.indicatorKind !== select.value) return;
        group.querySelectorAll("[data-param-label]").forEach((control) => {
            const value = control.tagName === "SELECT"
                ? control.selectedOptions[0].textContent
                : control.value;
            addLine(`${control.dataset.paramLabel}: ${value === "" ? "—" : value}`);
        });
    });
}

function bindIndicatorsVisibility() {
    document.querySelectorAll("[data-indicator-type]").forEach((select) => {
        const fields = select.closest(".indicator-card").querySelector("[data-indicator-fields]");
        const summary = document.querySelector(`[data-indicator-summary="${select.dataset.indicatorType}"]`);
        const update = () => {
            const active = select.value !== "Não usar";
            setVisible([fields], active);
            fields.querySelectorAll("[data-indicator-kind]").forEach((group) => {
                const selected = group.dataset.indicatorKind === select.value;
                setVisible([group], selected);
                group.querySelectorAll("input, select").forEach((control) => {
                    control.disabled = !selected;
                });
            });
            summary.querySelector(".summary-status").textContent = active ? "Ativo" : "Inativo";
            summary.querySelector("[data-indicator-summary-type]").textContent = select.selectedOptions[0].textContent;
            updateIndicatorSummary(select, fields, summary);
        };
        select.addEventListener("change", update);
        select.closest(".indicator-card").querySelector("[data-indicator-usage]")
            .addEventListener("change", () => updateIndicatorSummary(select, fields, summary));
        const parameters = fields.querySelector(".tab-panel-params");
        parameters.addEventListener("input", () => updateIndicatorSummary(select, fields, summary));
        parameters.addEventListener("change", () => updateIndicatorSummary(select, fields, summary));
        update();
    });
}

document.addEventListener("DOMContentLoaded", bindIndicatorsVisibility);

function bindUnitLabels() {
    document.querySelectorAll("[data-unit-selector]").forEach((select) => {
        const card = select.closest(".card");
        const update = () => {
            const percentage = select.value === "Porcentagem";
            const suffix = percentage ? "(% porcentagem)" : "(pontos)";
            card.querySelectorAll("[data-unit-label]").forEach((label) => {
                label.textContent = `${label.dataset.unitLabel} ${suffix}`;
            });
            const help = card.querySelector("[data-unit-help]");
            if (help) help.textContent = percentage ? "Valores em porcentagem." : "Valores em pontos.";
        };
        select.addEventListener("change", update);
        update();
    });
}

document.addEventListener("DOMContentLoaded", bindUnitLabels);

function bindRulesSummary() {
    const rules = document.querySelector("[data-rules-parameters]");
    const summary = document.querySelector("[data-rules-summary]");
    if (!rules || !summary) return;
    const outputs = summary.querySelectorAll("[data-indicator-summary-values]");
    const cards = rules.querySelectorAll(".rules-card");
    const update = () => {
        outputs.forEach((output) => output.replaceChildren());
        cards.forEach((card, index) => {
            card.querySelectorAll("input:not(.tab-radio), select").forEach((control) => {
                if (control.closest(".tab-panel-optimize, .is-hidden")) return;
                const label = control.previousElementSibling;
                if (!label || label.tagName !== "LABEL") return;
                const title = label.textContent.trim();
                const value = control.tagName === "SELECT"
                    ? control.selectedOptions[0].textContent
                    : control.value || "—";
                const baseTitle = label.dataset.unitLabel || title;
                const take = index === 2 && ["Take Profit", "Vezes o stop", "Distância fixa"].includes(baseTitle);
                const output = outputs[take ? 3 : index];
                const line = document.createElement("p");
                line.textContent = `${title}: ${value}`;
                output.appendChild(line);
            });
        });
    };
    rules.addEventListener("input", update);
    rules.addEventListener("change", update);
    update();
}

document.addEventListener("DOMContentLoaded", bindRulesSummary);

function relevantReviewControl(control, card) {
    if (control.type === "radio" && !control.checked) return false;
    const kind = control.closest("[data-indicator-kind]");
    const indicator = card.querySelector("[data-indicator-type]");
    if (kind && kind.dataset.indicatorKind !== indicator.value) return false;
    if (control.closest("[data-pending-fields]") && card.querySelector("[data-rule-order]").value !== "Pendente") return false;
    const condition = card.querySelector("[data-candle-condition]");
    if (condition) {
        if (control.closest("[data-candle-common]") && condition.value === "Desativado") return false;
        if (control.closest("[data-candle-size]") && condition.value !== "Candles") return false;
        if (control.closest("[data-candle-wicks]") && condition.value !== "Pavios") return false;
    }
    const take = card.querySelector("[data-take-mode]");
    if (take) {
        if (control.closest("[data-take-multiplier]") && take.value !== "Vezes o stop") return false;
        if (control.closest("[data-take-distance]") && take.value === "Vezes o stop") return false;
    }
    return true;
}

function reviewLine(control, card) {
    const row = control.closest(".optimize-row");
    const label = control.previousElementSibling;
    let title = control.dataset.paramLabel || (label?.tagName === "LABEL" ? label.textContent.trim() : "");
    if (control.type === "radio") title = "Usar como";
    if (row) {
        const name = row.querySelector(".optimize-name");
        const controls = Array.from(row.querySelectorAll("input, select"));
        const labels = row.querySelectorAll("label");
        title = `${name.textContent.trim()} — ${labels[controls.indexOf(control)]?.textContent.trim() || ""}`;
    }
    const unitLabel = row?.querySelector("[data-unit-label]") || (label?.hasAttribute("data-unit-label") ? label : null);
    if (unitLabel) {
        const unit = card.querySelector("[data-unit-selector]");
        title = row ? `${unitLabel.dataset.unitLabel} — ${row.querySelectorAll("label")[Array.from(row.querySelectorAll("input, select")).indexOf(control)].textContent.trim()}` : (control.dataset.paramLabel || unitLabel.dataset.unitLabel);
        title += unit?.value === "Porcentagem" ? " (% porcentagem)" : " (pontos)";
    }
    return {title, value: control.tagName === "SELECT" ? control.selectedOptions[0]?.textContent : control.value};
}

async function renderSetupReview() {
    const parameters = document.querySelector("[data-review-params]");
    const optimize = document.querySelector("[data-review-optimize]");
    if (!parameters || !optimize) return;
    try {
        for (const page of ["inicio", "indicadores", "gestao"]) {
            const response = await fetch(`/${page}`);
            if (!response.ok) throw new Error("Falha ao carregar os cards");
            const root = new DOMParser().parseFromString(await response.text(), "text/html");
            restoreSetup(root, page);
            const name = root.querySelector("[data-setup-name]");
            if (name) {
                root.querySelector("[data-setup-magic]").value = magicNumberFromName(name.value);
                document.querySelector("[data-review-setup-name]").textContent = name.value;
            }
            root.querySelectorAll(".card").forEach((card) => {
                const heading = card.querySelector("h2");
                if (!heading || !card.querySelector("input, select")) return;
                for (const [panel, optimization] of [[parameters, false], [optimize, true]]) {
                    const section = document.createElement("section");
                    section.className = "card";
                    const title = document.createElement("h2");
                    title.textContent = heading.textContent;
                    section.appendChild(title);
                    const controls = Array.from(card.querySelectorAll("input:not(.tab-radio), select"));
                    controls.filter(control => {
                        const isOptimization = Boolean(control.closest(".tab-panel-optimize"));
                        // Show fixed context (type, usage, mode, unit) alongside optimization ranges.
                        const fixedContext = !control.closest(".tabs") || control.matches("[data-unit-selector], [data-take-mode]");
                        return (isOptimization === optimization || (optimization && fixedContext)) && relevantReviewControl(control, card);
                    }).forEach(control => {
                        const entry = reviewLine(control, card);
                        if (!entry.title) return;
                        const line = document.createElement("p");
                        const label = document.createElement("strong");
                        label.textContent = `${entry.title}: `;
                        line.append(label, document.createTextNode(entry.value || "—"));
                        section.appendChild(line);
                    });
                    if (section.children.length > 1) panel.appendChild(section);
                }
            });
        }
    } catch {
        parameters.textContent = "Não foi possível carregar a revisão. Atualize a página para tentar novamente.";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-page]");
    if (!root) return;
    if (["inicio", "indicadores", "gestao"].includes(root.dataset.page)) {
        const save = () => {
            const state = readSetupState();
            state[root.dataset.page] = setupControls(root).map(control => ({value: control.value, checked: control.checked}));
            localStorage.setItem(setupStorageKey, JSON.stringify(state));
        };
        root.addEventListener("input", save);
        root.addEventListener("change", save);
        save();
    }
    renderSetupReview();
});

function optimizationRowCount(row) {
    const controls = Array.from(row.querySelectorAll("input, select"));
    if (controls.length === 2 && controls.every(control => control.tagName === "SELECT")) {
        return BigInt(Math.abs(controls[1].selectedIndex - controls[0].selectedIndex) + 1);
    }
    if (controls.length === 3) {
        const [start, step, end] = controls.map(control => Number(control.value));
        if (!controls.every(control => control.value.trim()) || ![start, step, end].every(Number.isFinite) || step <= 0 || end < start) return 0n;
        const intervals = (end - start) / step;
        if (!Number.isSafeInteger(Math.floor(intervals))) return 0n;
        return BigInt(Math.floor(intervals + 1e-9) + 1);
    }
    return 1n;
}

function pagePassageCount(root) {
    let count = 1n;
    root.querySelectorAll(".tab-panel-optimize .optimize-row").forEach(row => {
        const card = row.closest(".card");
        const control = row.querySelector("input, select");
        if (!control || !relevantReviewControl(control, card)) return;
        const mode = card.querySelector("[data-unit-selector]");
        if (mode?.value === "Desativado") return;
        count *= optimizationRowCount(row);
    });
    return count;
}

async function bindPassageCounter() {
    const counter = document.querySelector("[data-passage-counter]");
    const current = document.querySelector("[data-page]");
    if (!counter || !current) return;
    const roots = new Map();
    try {
        for (const page of ["inicio", "indicadores", "gestao"]) {
            if (current.dataset.page === page) roots.set(page, current);
            else {
                const response = await fetch(`/${page}`);
                if (!response.ok) throw new Error("Falha ao carregar intervalos");
                const root = new DOMParser().parseFromString(await response.text(), "text/html");
                restoreSetup(root, page);
                roots.set(page, root);
            }
        }
        const update = () => {
            let count = 1n;
            roots.forEach(root => { count *= pagePassageCount(root); });
            counter.textContent = count === 0n ? "Combinações: intervalos inválidos" : `Combinações: ${count.toLocaleString("pt-BR")}`;
        };
        current.addEventListener("input", update);
        current.addEventListener("change", update);
        update();
    } catch {
        counter.textContent = "Combinações: indisponível";
    }
}

document.addEventListener("DOMContentLoaded", bindPassageCounter);
