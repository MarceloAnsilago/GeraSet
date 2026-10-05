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
