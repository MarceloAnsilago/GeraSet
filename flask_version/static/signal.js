function readSignalRow(row) {
    const value = key => row.querySelector(`[name$="-${key}"]`).value;
    return Object.fromEntries(["operator", "target", "target-candle", "comparison", "reference", "reference-candle", "distance", "usage", "direction", "fixed"]
        .map(key => [key.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase()), value(key)]));
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
    const finite = value => value.trim() !== "" && Number.isFinite(Number(value));
    if (![rule.operator, rule.target, rule.comparison, rule.reference].every(signalChosen)) errors.push("preencha condição, A, comparação e Da (DE)");
    if (!signalChosen(rule.targetCandle)) errors.push("selecione o candle de A");
    if (rule.reference !== "Valor fixo" && !signalChosen(rule.referenceCandle)) errors.push("selecione o candle de Da (DE)");
    if (rule.reference === "Valor fixo" && !finite(rule.fixed)) errors.push("informe um valor fixo numérico");
    if (!finite(rule.distance) || Number(rule.distance) < 0) errors.push("a distância deve ser um número maior ou igual a zero");
    if (unit === "N.usar" && Number(rule.distance) !== 0) errors.push("selecione a unidade da distância ou zere a distância");
    if (unit === "Porcentagem" && rule.reference === "Valor fixo" && Number(rule.fixed) === 0 && Number(rule.distance) > 0) errors.push("porcentagem exige referência diferente de zero");
    const scale = source => /: (RSI|ADX)( |$)/.test(source) ? "índice" : source === "Valor fixo" ? "fixo" : "preço";
    const targetScale = scale(rule.target), referenceScale = scale(rule.reference);
    if (signalChosen(rule.target) && signalChosen(rule.reference) && referenceScale !== "fixo" && targetScale !== referenceScale) errors.push("compare valores da mesma escala; para RSI/ADX, use um indicador compatível ou valor fixo");
    if (unit === "Pontos" && Number(rule.distance) > 0 && (targetScale === "índice" || referenceScale === "índice")) errors.push("distância em pontos só se aplica a preços");
    if (rule.comparison.startsWith("Cruzar&fechar") && (rule.targetCandle === "Vela atual" || rule.reference !== "Valor fixo" && rule.referenceCandle === "Vela atual")) errors.push("cruzar e fechar exige candles fechados");
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
        const group = `${rule.usage}|${rule.direction}`;
        if (!groups.has(group)) {
            if (rule.operator !== "Se") errors.push("a primeira condição desta finalidade e direção deve usar Se");
            groups.add(group);
        } else if (rule.operator === "Se") errors.push("continue esta finalidade e direção com E ou Ou");
        return errors.map(message => `Condição ${index + 1}: ${message}.`);
    });
}

function updateSignalFields(card) {
    card.querySelectorAll(".condition-row").forEach(row => {
        const fixed = readSignalRow(row).reference === "Valor fixo";
        row.querySelector("[data-signal-fixed]").classList.toggle("is-hidden", !fixed);
        row.querySelector('[name$="-fixed"]').disabled = !fixed;
        row.querySelector('[name$="-reference-candle"]').disabled = fixed;
    });
}

function signalSummaryLines(card) {
    const unit = card.querySelector("[data-unit-selector]").value;
    const groups = new Map();
    const lines = Array.from(card.querySelectorAll(".condition-row")).flatMap((row, index) => {
        const rule = readSignalRow(row);
        if (!signalRowActive(rule)) return [];
        const group = `${rule.usage} / ${rule.direction}`;
        if (!groups.has(group)) groups.set(group, []);
        groups.get(group).push({operator: rule.operator, label: `C${index + 1}`});
        const reference = rule.reference === "Valor fixo" ? rule.fixed : `${rule.reference} (${rule.referenceCandle})`;
        const distance = unit === "N.usar" ? "" : ` — distância: ${rule.distance} ${unit === "Porcentagem" ? "%" : "pontos"}`;
        const incomplete = signalRuleErrors(rule, unit).length ? " — incompleta ou inválida" : "";
        return [`Condição ${index + 1} (${group}): ${rule.operator} ${rule.target} (${rule.targetCandle}) ${rule.comparison} ${reference}${distance}${incomplete}`];
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
