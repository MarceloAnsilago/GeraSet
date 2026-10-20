// Mirroring is an explicit editable copy. It never guesses a fixed RSI level.
function mirrorBuyRule(rule) {
    const mirrored = {...rule, normalSide: 'Venda', sense: 'Normal', mirrorNote: ''};
    const reverse = {
        'Maior que': 'Menor que', 'Menor que': 'Maior que',
        'Maior ou igual que': 'Menor ou igual que', 'Menor ou igual que': 'Maior ou igual que',
        'Cruzar p/ cima de': 'Cruzar p/ baixo de', 'Cruzar p/ baixo de': 'Cruzar p/ cima de',
        'Cruzar&fechar acima de': 'Cruzar&fechar abaixo de', 'Cruzar&fechar abaixo de': 'Cruzar&fechar acima de',
        'Igual que': 'Igual que', 'Diferente de': 'Diferente de', 'Toque': 'Toque',
    };
    const a = signalSourceDefinition(rule.target), b = signalSourceDefinition(rule.reference);
    const type = source => /^Indicador \d+: (RSI|ADX|Média Móvel)/.exec(source)?.[1];
    const fail = message => ({rule: {...mirrored, comparison: 'N.usar', mirrorNote: message}, directional: false});
    if (signalResultSide(rule) !== 'Compra') return fail('A origem precisa ser um sinal de compra.');
    if (!reverse[rule.comparison]) return fail('Complete a comparação de compra antes de espelhar.');
    if (!signalChosen(rule.target) || !signalChosen(rule.reference)) return fail('Complete as fontes da compra antes de espelhar.');
    if (rule.comparison === 'Toque' && (rule.targetCandle === 'Vela atual' || rule.referenceCandle === 'Vela atual'))
        return fail('Toque na vela atual exige definir manualmente a regra de venda.');
    const swapLine = source => {
        const definition = signalSourceDefinition(source);
        if (type(source) === 'RSI' && definition?.constant) {
            const slot = /^Indicador (\d+):/.exec(source)[1];
            return indicatorSignalSources('RSI', slot).find(line => line.level === 2 - definition.level).source;
        }
        if (type(source) === 'ADX' && definition?.buffer > 0) {
            const slot = /^Indicador (\d+):/.exec(source)[1];
            return indicatorSignalSources('ADX', slot).find(line => line.buffer === 3 - definition.buffer).source;
        }
        const prices = {'Máxima da vela':'Mínima da vela', 'Mínima da vela':'Máxima da vela',
            'Máxima do dia':'Mínima do dia', 'Mínima do dia':'Máxima do dia',
            'Máxima do dia anterior':'Mínima do dia anterior', 'Mínima do dia anterior':'Máxima do dia anterior'};
        return prices[source] || source;
    };
    if (type(rule.target) === 'ADX' || type(rule.reference) === 'ADX') {
        if (type(rule.target) !== 'ADX' || (rule.reference !== 'Valor fixo' && type(rule.reference) !== 'ADX'))
            return fail('A combinação de ADX com outra fonte exige revisão manual.');
        if (a?.buffer === 0 && (rule.reference === 'Valor fixo' || b?.buffer === 0))
            return {rule: mirrored, directional: false}; // Strength filter, same threshold on both sides.
        if (a?.buffer > 0 && (rule.reference === 'Valor fixo' || b?.buffer > 0))
            return {rule: {...mirrored, target: swapLine(rule.target), reference: swapLine(rule.reference)}, directional: true};
        return fail('Não há espelhamento definido entre a força ADX e as linhas DI.');
    }
    if (rule.reference === 'Valor fixo') return fail('Informe a referência de venda: um valor fixo não define seu nível correspondente.');
    if (type(rule.target) === 'RSI' || type(rule.reference) === 'RSI') {
        if (type(rule.target) !== 'RSI' || type(rule.reference) !== 'RSI' || !b?.constant || a?.constant)
            return fail('Para espelhar RSI, compare a linha RSI com um nível inferior, médio ou superior.');
    } else if ((a && a.scale !== 'preço') || (b && b.scale !== 'preço')) {
        return fail('Esta combinação de fontes não possui espelhamento definido.');
    }
    return {rule: {...mirrored, target: swapLine(rule.target), reference: swapLine(rule.reference), comparison: reverse[rule.comparison]}, directional: true};
}

const signalBankFields = ['operator','target','targetCandle','comparison','reference','referenceCandle','distance','normalSide','sense','fixed'];
function writeSignalBankRow(row, rule = {}) {
    for (const key of signalBankFields) {
        const name = key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
        const control = row.querySelector(`[name$="-${name}"]`);
        control.value = rule[key] ?? (key === 'distance' || key === 'fixed' ? '0' : key === 'normalSide' ? row.dataset.signalSide : key === 'sense' ? 'Normal' : 'N.usar');
        control.signalPickerRefresh?.();
    }
    row.querySelector('[data-mirror-note]').value = rule.mirrorNote || '';
}

// Existing five-row setups can contain both sides and Inverter. Preserve their
// resulting direction while moving them into the new banks, without changing logic.
function normalizeSignalBanks(root) {
    const rows = Array.from(root.querySelectorAll('.condition-row'));
    if (!rows.length || !rows[0].dataset?.signalSide) return;
    const rules = rows.map(readSignalRow);
    const move = rules.some((rule, i) => signalRowActive(rule) && signalResultSide(rule) && signalResultSide(rule) !== rows[i].dataset.signalSide);
    if (move) {
        const banks = {Compra: [], Venda: []};
        rules.forEach((rule, i) => {
            if (signalRowActive(rule)) banks[signalResultSide(rule) || rows[i].dataset.signalSide].push(rule);
        });
        if (banks.Compra.length > 5 || banks.Venda.length > 5) throw new Error('Cada direção admite até cinco condições.');
        for (const side of ['Compra','Venda']) rows.filter(row => row.dataset.signalSide === side)
            .forEach((row, i) => writeSignalBankRow(row, banks[side][i] ? {...banks[side][i], normalSide: side, sense: 'Normal'} : {}));
    }
    rows.forEach(row => {
        row.querySelector('[name$="-normal-side"]').value = row.dataset.signalSide;
        row.querySelector('[name$="-sense"]').value = 'Normal';
    });
}

function bindSignalBanks() {
    const card = document.querySelector('[data-conditions]');
    if (!card) return;
    const root = card.closest('[data-page]');
    const rows = side => Array.from(card.querySelectorAll(`.condition-row[data-signal-side="${side}"]`));
    const fingerprint = () => JSON.stringify({unit: card.querySelector('[data-unit-selector]').value,
        rules: rows('Compra').map(readSignalRow),
        indicators: Array.from(root.querySelectorAll('.indicator-card input, .indicator-card select:not([data-source-ui])')).map(c => [c.name || c.id,c.value,c.checked])});
    const source = card.querySelector('[data-mirror-source]');
    const status = card.querySelector('[data-mirror-status]');
    const refresh = () => {
        card.querySelectorAll('.condition-row').forEach(row => {
            const note = row.querySelector('[data-mirror-note]').value;
            row.querySelector('.signal-mirror-warning').hidden = !note;
            row.querySelector('[data-mirror-message]').textContent = note;
        });
        status.textContent = source.value && source.value !== fingerprint()
            ? 'Compra ou parâmetros alterados após o espelhamento. A venda continua independente; confira ou espelhe novamente.'
            : source.value ? 'Venda espelhada. Revise as pendências destacadas; você pode editar a cópia.' : 'Copie as condições de compra quando houver uma transformação definida.';
    };
    card.querySelectorAll('[data-signal-tab]').forEach(button => button.addEventListener('click', () => {
        card.querySelectorAll('[data-signal-tab]').forEach(tab => tab.setAttribute('aria-selected', String(tab === button)));
        card.querySelectorAll('[data-signal-panel]').forEach(panel => { panel.hidden = panel.dataset.signalPanel !== button.dataset.signalTab; });
        card.querySelector('[data-signal-mirror-tools]').hidden = button.dataset.signalTab !== 'Venda';
    }));
    const confirmation = card.querySelector('[data-mirror-confirm]');
    const mirror = (replace = false) => {
        const buys = rows('Compra').map(readSignalRow).filter(signalRowActive);
        if (!buys.length) { status.textContent = 'Preencha pelo menos uma condição de compra.'; return; }
        const errors = buys.flatMap(rule => signalRuleErrors(rule, card.querySelector('[data-unit-selector]').value));
        if (errors.length) { status.textContent = `Revise a compra antes de espelhar: ${errors.join(' ')}`; return; }
        if (!replace && rows('Venda').some(row => signalRowActive(readSignalRow(row)))) { confirmation.hidden = false; return; }
        confirmation.hidden = true;
        const mirrored = buys.map(mirrorBuyRule);
        for (const usage of new Set(buys.map(rule => rule.usage))) {
            const group = mirrored.filter(result => result.rule.usage === usage);
            if (!group.some(result => result.directional) && !group.some(result => result.rule.mirrorNote)) {
                group[0].rule.comparison = 'N.usar';
                group[0].rule.mirrorNote = 'Este grupo contém somente filtros de força. Defina a condição direcional da venda.';
            }
        }
        rows('Venda').forEach((row,i) => writeSignalBankRow(row, mirrored[i]?.rule));
        source.value = fingerprint();
        card.dispatchEvent(new Event('change', {bubbles:true}));
        refresh();
    };
    card.querySelector('[data-mirror-buy]').addEventListener('click', () => mirror());
    card.querySelector('[data-mirror-replace]').addEventListener('click', () => mirror(true));
    card.querySelector('[data-mirror-cancel]').addEventListener('click', () => { confirmation.hidden = true; });
    card.querySelectorAll('[data-mirror-reviewed]').forEach(button => button.addEventListener('click', () => {
        const row = button.closest('.condition-row'), rule = readSignalRow(row);
        const errors = signalRuleErrors({...rule, mirrorNote:''}, card.querySelector('[data-unit-selector]').value);
        if (signalRowActive(rule) && errors.length) { row.querySelector('[data-mirror-message]').textContent = errors.join(' '); return; }
        row.querySelector('[data-mirror-note]').value = '';
        card.dispatchEvent(new Event('change', {bubbles:true}));
    }));
    root.addEventListener('change',refresh);
    root.addEventListener('input',refresh);
    refresh();
}
