// Indicator-specific signal capabilities. Add new indicator families here.
const signalProfiles = {
    RSI: {family: "RSI", levelReferences: true},
    ADX: {family: "ADX", levelReferences: false},
};

function signalSourceInfo(source) {
    if (source === "Valor fixo") return {family: "constant"};
    const match = /^Indicador (\d+): (RSI|ADX)(?: |$)/.exec(source);
    return match ? {...signalProfiles[match[2]], slot: match[1]} : {family: "price"};
}

function signalSourcesCompatible(target, reference) {
    if (!signalChosen(target) || !signalChosen(reference)) return true;
    const a = signalSourceInfo(target), b = signalSourceInfo(reference);
    if (a.family === "constant" || b.family === "constant") return true;
    if (a.family !== b.family) return false;
    return !a.levelReferences || a.slot === b.slot;
}

function filterSignalSources(row) {
    const target = row.querySelector('[name$="-target"]');
    const reference = row.querySelector('[name$="-reference"]');
    for (const option of reference.options) {
        const compatible = signalSourcesCompatible(target.value, option.value);
        option.hidden = !compatible || /: RSI$/.test(option.value);
        option.disabled = !compatible;
    }
    if (!signalSourcesCompatible(target.value, reference.value)) reference.value = "N.usar";
}

function signalConstantSource(source) {
    return source === "Valor fixo" || /: RSI Nível (superior|médio|inferior)$/.test(source);
}

function readSignalRow(row) {
    const value = key => row.querySelector(`[name$="-${key}"]`).value;
    const rule = Object.fromEntries(["operator", "target", "target-candle", "comparison", "reference", "reference-candle", "distance", "sense", "fixed", "normal-side"]
        .map(key => [key.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase()), value(key)]));
    const root = row.closest("[data-page]");
    const usages = new Set([rule.target, rule.reference].map(source => {
        const match = /^Indicador (\d+):/.exec(source);
        if (!match) return null;
        return root.querySelector(`[data-indicator-type="${match[1]}"]`)
            ?.closest(".indicator-card").querySelector("[data-indicator-usage] input:checked")?.value;
    }).filter(Boolean));
    rule.usage = usages.size > 1 ? "Conflito de finalidade" : [...usages][0] || "Entrada";
    return rule;
}

function signalResultSide(rule) {
    if (!["Compra", "Venda"].includes(rule.normalSide) || !["Normal", "Inverter"].includes(rule.sense)) return "";
    return rule.sense === "Normal" ? rule.normalSide : rule.normalSide === "Compra" ? "Venda" : "Compra";
}

function signalAction(rule) {
    const side = signalResultSide(rule);
    if (!side) return "Selecione o sinal normal";
    if (rule.usage === "Saída") return side === "Compra" ? "Fechar vendas" : "Fechar compras";
    return side === "Compra" ? "Abrir compra" : "Abrir venda";
}

function signalChosen(value) {
    return Boolean(value) && value !== "N.usar" && value !== "Não usar";
}

function signalRowActive(rule) {
    return [rule.operator, rule.target, rule.targetCandle, rule.comparison, rule.reference, rule.referenceCandle].some(signalChosen)
        || rule.distance.trim() !== "0" && rule.distance.trim() !== "" && Number(rule.distance) !== 0;
}

function signalRuleErrors(rule, unit) {
    const errors = [];
    if (!["Compra", "Venda"].includes(rule.normalSide)) errors.push("selecione Compra ou Venda em Sinal normal");
    if (!["Normal", "Inverter"].includes(rule.sense)) errors.push("selecione Normal ou Inverter em Sentido");
    const finite = value => value.trim() !== "" && Number.isFinite(Number(value));
    if (rule.usage === "Conflito de finalidade") errors.push("os indicadores selecionados têm finalidades diferentes; ajuste Usar como nos indicadores");
    if (![rule.operator, rule.target, rule.comparison, rule.reference].every(signalChosen)) errors.push("preencha condição, A, comparação e Da (DE)");
    if (!signalConstantSource(rule.target) && !signalChosen(rule.targetCandle)) errors.push("selecione o candle de A");
    if (!signalConstantSource(rule.reference) && !signalChosen(rule.referenceCandle)) errors.push("selecione o candle de Da (DE)");
    if (rule.reference === "Valor fixo" && !finite(rule.fixed)) errors.push("informe um valor fixo numérico");
    if (!finite(rule.distance) || Number(rule.distance) < 0) errors.push("a distância deve ser um número maior ou igual a zero");
    if (unit === "N.usar" && Number(rule.distance) !== 0) errors.push("selecione a unidade da distância ou zere a distância");
    if (unit === "Porcentagem" && rule.reference === "Valor fixo" && Number(rule.fixed) === 0 && Number(rule.distance) > 0) errors.push("porcentagem exige referência diferente de zero");
    const scale = source => /: (RSI|ADX)( |$)/.test(source) ? "índice" : source === "Valor fixo" ? "fixo" : "preço";
    const targetScale = scale(rule.target), referenceScale = scale(rule.reference);
    if (!signalSourcesCompatible(rule.target, rule.reference) && targetScale === referenceScale) errors.push("selecione fontes compatíveis com o indicador e o slot de A");
    if (signalChosen(rule.target) && signalChosen(rule.reference) && referenceScale !== "fixo" && targetScale !== referenceScale) errors.push("compare valores da mesma escala; para RSI/ADX, use um indicador compatível ou valor fixo");
    if (unit === "Pontos" && Number(rule.distance) > 0 && (targetScale === "índice" || referenceScale === "índice")) errors.push("distância em pontos só se aplica a preços");
    if (rule.comparison.startsWith("Cruzar&fechar") && (!signalConstantSource(rule.target) && rule.targetCandle === "Vela atual" || !signalConstantSource(rule.reference) && rule.referenceCandle === "Vela atual")) errors.push("cruzar e fechar exige candles fechados");
    return errors;
}

function validateSignalCard(card) {
    if (!card) return [];
    const unit = card.querySelector("[data-unit-selector]").value;
    const groups = new Set();
    return Array.from(card.querySelectorAll(".condition-row")).flatMap((row, index) => {
        const rule = readSignalRow(row);
        if (!signalRowActive(rule)) return [];
        const errors = signalRuleErrors(rule, unit);
        const group = `${rule.usage}|${signalResultSide(rule)}`;
        if (!groups.has(group)) {
            if (rule.operator !== "Se") errors.push("a primeira condição desta finalidade e sinal resultante deve usar Se");
            groups.add(group);
        } else if (rule.operator === "Se") errors.push("continue esta finalidade e sinal resultante com E ou Ou");
        return errors.map(message => `Condição ${index + 1}: ${message}.`);
    });
}

function updateSignalFields(card) {
    card.querySelectorAll(".condition-row").forEach(row => {
        filterSignalSources(row);
        const rule = readSignalRow(row);
        const fixed = rule.reference === "Valor fixo";
        row.querySelector("[data-signal-fixed]").classList.toggle("is-hidden", !fixed);
        row.querySelector('[name$="-fixed"]').disabled = !fixed;
        row.querySelector('[name$="-reference-candle"]').disabled = signalConstantSource(rule.reference);
        row.querySelector('[name$="-target-candle"]').disabled = signalConstantSource(rule.target);
    });
}

function signalSummaryLines(card) {
    const unit = card.querySelector("[data-unit-selector]").value;
    const groups = new Map();
    const lines = Array.from(card.querySelectorAll(".condition-row")).flatMap((row, index) => {
        const rule = readSignalRow(row);
        if (!signalRowActive(rule)) return [];
        const group = `${rule.usage} / ${signalResultSide(rule) || "Sinal não definido"}`;
        if (!groups.has(group)) groups.set(group, []);
        groups.get(group).push({operator: rule.operator, label: `C${index + 1}`});
        const reference = rule.reference === "Valor fixo" ? rule.fixed : signalConstantSource(rule.reference) ? rule.reference : `${rule.reference} (${rule.referenceCandle})`;
        const distance = unit === "N.usar" ? "" : ` — distância: ${rule.distance} ${unit === "Porcentagem" ? "%" : "pontos"}`;
        const incomplete = signalRuleErrors(rule, unit).length ? " — incompleta ou inválida" : "";
        return [`Condição ${index + 1} (${group}; ${rule.normalSide || "—"} / ${rule.sense} → ${signalAction(rule)}): ${rule.operator} ${rule.target}${signalConstantSource(rule.target) ? "" : ` (${rule.targetCandle})`} ${rule.comparison} ${reference}${distance}${incomplete}`];
    });
    groups.forEach((rules, group) => {
        const clauses = [[]];
        rules.forEach(rule => {
            if (rule.operator === "Ou") clauses.push([]);
            clauses[clauses.length - 1].push(rule.label);
        });
        lines.push(`${group}: ${clauses.map(clause => `(${clause.join(" E ")})`).join(" Ou ")}`);
    });
    return lines;
}
