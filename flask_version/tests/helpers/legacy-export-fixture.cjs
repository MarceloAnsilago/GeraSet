// Runs the real legacy serializer and validators against a controlled UI snapshot.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
function generate(config = {}) {
    const context = vm.createContext({document: {addEventListener() {}}, window: {addEventListener() {}}, TextEncoder});
    for (const file of ['signal.js','app.js','export.js'])
        vm.runInContext(fs.readFileSync(path.join(__dirname, '../../static', file), 'utf8'), context);
    context.restoreSetup = () => {};
    context.readSignalRow = row => row;
    context.setupControls = root => root.controls;
    const control = (key, value, checked) => ({name: key, value: String(value), checked});
    const zeroRanges = (prefix, keys) => Object.fromEntries(keys.flatMap(key => ['start','step','end'].map(b => [`${prefix}-${key}-${b}`, '0'])));
    const start = {setup_name: config.name || 'Equivalência técnica', setup_magic: '1', setup_market: 'Forex', setup_mode: 'Day trade',
        setup_lot: '0.01', setup_direction: 'Compra e venda', setup_timeframe: 'Tempo corrente',
        setup_entry_start: '09:00', setup_entry_end: '17:00', 'operation-direction-start': 'Compra e venda', 'operation-direction-end': 'Compra e venda',
        'schedule-entry-start-start': '09:00', 'schedule-entry-start-end': '09:00', 'schedule-entry-end-start': '17:00', 'schedule-entry-end-end': '17:00',
        ...(config.inicio || {})};
    const management = {order_mode: 'A mercado', pending_reference: 'Máxima', pending_bar: '1',
        'pending-reference-start': 'Máxima', 'pending-reference-end': 'Máxima', ...zeroRanges('pending',['bar']),
        target_unit: 'Pontos', target_stop_mode: 'Distância + candle', target_stop: '20', target_stop_multiplier: '1',
        target_candle: 'último', target_size: 'Total com pavios', 'target-candle-start': 'último', 'target-candle-end': 'último',
        'target-size-start': 'Total com pavios', 'target-size-end': 'Total com pavios', target_take_mode: 'Vezes o stop',
        target_take_distance: '150', target_take_multiplier: '2', ...zeroRanges('target',['stop','take-distance','take-multiplier']),
        'breakeven-mode': 'Desativado', 'breakeven-trigger': '0', 'breakeven-offset': '0', ...zeroRanges('breakeven',['activate','distance']),
        ...Object.fromEntries(['trailing','moving-stop'].flatMap(key => Object.entries({[key+'-mode']: 'Desativado', [key+'-trigger']: '0',
            [key+'-distance']: '0', [key+'-step']: '0', ...zeroRanges(key,['activate','distance','step'])}))),
        ...(config.gestao || {})};
    const fields = new Map(), indicatorControls = [];
    const add = (selector, key, value, checked) => {
        const item = control(key, value, checked); fields.set(selector, item); indicatorControls.push(item);
    };
    for (let slot = 1; slot <= 4; slot++) {
        const item = config.indicators?.[slot-1] || {};
        const type = item.type || ['Média Móvel','RSI','ADX','Média Móvel'][slot-1];
        const purpose = item.purpose || (slot === 2 ? 'Saída' : 'Entrada');
        add(`[data-indicator-type="${slot}"]`, `indicator-type-${slot}`, type);
        add(`[name="indicator-usage-${slot}"]:checked`, `indicator-usage-${slot}`, purpose, true);
        for (const [suffix, value] of [['',item.timeframe || 'Tempo corrente'], ['-start',item.frameStart || item.timeframe || 'Tempo corrente'], ['-end',item.frameEnd || item.timeframe || 'Tempo corrente']])
            add(`[name="indicator-timeframe-${slot}${suffix}"]`, `indicator-timeframe-${slot}${suffix}`, value);
        const numbers = type === 'RSI' ? [[1,'Período',14],[2,'Sobrevenda',30],[3,'Sobrecompra',70],[4,'Nível médio',50]]
            : [[1,'Período',20],[2,'Shift',0]];
        for (const [index,title,value] of numbers) {
            add(`[id="param-${slot}-${type}-${index}"]`, `param-${slot}-${type}-${index}`, item.params?.[title] ?? value);
            for (let i=1;i<=3;i++) add(`[id="opt-${slot}-${type}-${i}-${title}"]`, `opt-${slot}-${type}-${i}-${title}`, item.ranges?.[title]?.[i-1] ?? '0');
        }
        for (const [index,title,defaultValue] of [[1,'Preço aplicado','Close'],[2,'Método','EMA']]) {
            const value = item.combos?.[title] || defaultValue;
            add(`[id="combo-${slot}-${type}-${index}"]`, `combo-${slot}-${type}-${index}`, value);
            for (const [i,bound] of ['start','end'].entries())
                add(`[name="opt-combo-${slot}-${type}-${title}-${bound}"]`, `opt-combo-${slot}-${type}-${title}-${bound}`, item.comboRanges?.[title]?.[i] || value);
        }
    }
    const baseRule = {operator:'Se',usage:'Entrada',normalSide:'Compra',sense:'Normal',target:'Indicador 1: Média Móvel',targetCandle:'Anterior',
        comparison:'Maior que',reference:'Fechamento da vela',referenceCandle:'Anterior',fixed:'0',distance:'0'};
    const configuredRules = config.rules || {0:baseRule,5:{...baseRule,usage:'Saída',normalSide:'Venda',target:'Indicador 2: RSI',reference:'Valor fixo',referenceCandle:'N.usar',fixed:'70'}};
    const rows = Array.from({length:10},(_,index) => configuredRules[index] || {...baseRule,operator:'N.usar',target:'N.usar',targetCandle:'N.usar',comparison:'N.usar',reference:'N.usar',referenceCandle:'N.usar'});
    // Include all condition/hidden draft fields in metadata, independently of native payloads.
    for (const [index,row] of rows.entries()) for (const [key,value] of Object.entries(row)) indicatorControls.push(control(`signal-${index}-${key}`,value));
    const signalCard = {querySelector: () => ({value:config.signalUnit || 'N.usar'}), querySelectorAll: () => rows};
    const roots = new Map();
    for (const [page, values] of [['inicio',start],['gestao',management],['configuracoes',{show_signal_histograms:'on',show_mt5_panel:'on'}]]) {
        const controls = Object.entries(values).map(([key,value])=>control(key,value));
        if(page==='gestao')controls.push(control('pending_mirror_sell','on',config.mirrorSell ?? false));
        if(page==='configuracoes')for(const item of controls)item.checked=config.display?.[item.name] ?? true;
        roots.set(page,{controls, querySelector(selector) {
            if(selector.startsWith('[data-page='))return this;
            if(page==='inicio'&&selector==='[data-setup-name]')return controls.find(c=>c.name==='setup_name');
            if(page==='inicio'&&selector==='[data-setup-magic]')return controls.find(c=>c.name==='setup_magic');
            return null;
        }});
    }
    roots.set('indicadores',{controls:indicatorControls,querySelector(selector) {
        if(selector.startsWith('[data-page='))return this;
        return selector==='[data-conditions]'?signalCard:fields.get(selector)||null;
    }});
    const result = context.serializeSetupSet(roots,config.state || {});
    return {filename:result.filename,set_base64:Buffer.from(result.contents).toString('base64')};
}
module.exports = {generate};
if(require.main===module){const cases=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(cases.map(generate)));}
