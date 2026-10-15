const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({document: {addEventListener() {}}, window: {addEventListener() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8'), context);

test('each RSI level selects the RSI from its own slot without changing comparison or target candle', () => {
    for (const slot of [1, 2, 3, 4]) {
        for (const level of ['superior', 'médio', 'inferior']) {
            const fields = {'-target': {value: 'Fechamento da vela'}, '-reference-candle': {value: 'Anterior'}};
            const reference = {
                value: `Indicador ${slot}: RSI Nível ${level}`,
                closest: () => ({querySelector: selector => fields[/"(.+)"/.exec(selector)[1]]}),
            };
            context.selectRsiForLevel(reference);
            assert.equal(fields['-target'].value, `Indicador ${slot}: RSI`);
            assert.equal(fields['-reference-candle'].value, 'N.usar');
        }
    }
});

test('other sources leave the signal unchanged', () => {
    for (const value of ['Valor fixo', 'Indicador 2: ADX', 'N.usar']) {
        context.selectRsiForLevel({value, closest() {throw new Error('Unexpected change');}});
    }
});
