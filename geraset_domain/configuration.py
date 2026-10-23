"""Adapt existing native configurations to v1.0 without deriving rules from HTML."""
from decimal import Decimal

from .errors import UniValidationError
from .strategy import StrategySpec
from .uni_mapping import COMPARISONS, MODES, PRICES, PRICE_SOURCES, TIMEFRAMES, compile_strategy
from .uni_presets import CONTRACT


def strategy_from_inputs(values):
    def raw(key):
        return values.get(key, str(CONTRACT[key]['default'])).split('||')[0]

    def integer(key):
        return int(Decimal(raw(key)))

    def boolean(key):
        return raw(key).lower() in ('true', '1')

    def choice(key, options):
        return {v: k for k, v in options.items()}[integer(key)]

    def clock(number):
        return f'{number//60:02d}:{number%60:02d}'

    order = {'type': 'market' if integer('InpOrderMode') == 0 else 'pending',
             'mirror_sell': boolean('InpPendingMirrorSell')}
    if order['type'] == 'pending':
        order.update(reference=choice('InpPendingReference', {'high': 0, 'low': 1, 'open': 2, 'close': 3}),
                     candle=integer('InpPendingCandle'))
    fixed_stop = integer('InpStopMode') == 1
    stop = {'type': 'fixed' if fixed_stop else 'candle', 'distance': raw('InpStopLoss')}
    if not fixed_stop:
        stop.update(multiplier=raw('InpStopCandleMultiplier'), candle=integer('InpStopCandle'),
                    measure='body' if boolean('InpStopBody') else 'total')
    take_mode = integer('InpTakeMode')
    if take_mode == -1:
        take_mode = 1 if Decimal(raw('InpTakeProfit')) > 0 else 0
    take = ({'type': 'fixed', 'distance': raw('InpTakeProfit')} if take_mode == 1 else
            {'type': 'stop_multiple', 'multiplier': raw('InpTakeStopMultiplier')})
    risk = {'target_unit': choice('InpTargetUnit', {'points': 0, 'percent': 1}),
            'stop_loss': stop, 'take_profit': take}
    for field, prefix, params in (
        ('breakeven', 'InpBreakeven', {'trigger': 'Trigger', 'offset': 'Offset'}),
        ('trailing', 'InpTrailing', {'trigger': 'Trigger', 'distance': 'Distance', 'adjustment_step': 'Step'}),
        ('moving_stop', 'InpMovingStop', {'trigger': 'Trigger', 'distance': 'Distance', 'adjustment_step': 'Step'}),
    ):
        risk[field] = {'mode': choice(prefix+'Mode', MODES), **{k: raw(prefix+v) for k, v in params.items()}}
    indicators = []
    for slot in range(1, 5):
        kind = choice(f'InpIndicator{slot}Type', {'disabled': -1, 'ma': 0, 'rsi': 1, 'adx': 2})
        purpose = 'exit' if integer(f'InpIndicator{slot}Exit') else 'entry'
        item = {'type': kind, 'slot': slot, 'purpose': purpose,
                'timeframe': choice(f'InpIndicator{slot}Timeframe', TIMEFRAMES)}
        if kind == 'ma':
            prefix = f'InpIndicator{slot}Ma'
            item.update(period=integer(prefix+'Period'), shift=integer(prefix+'Shift'),
                        price=choice(prefix+'Price', PRICES),
                        method=choice(prefix+'Method', {'sma': 0, 'ema': 1, 'smma': 2, 'lwma': 3}))
        elif kind in ('rsi', 'adx'):
            prefix = 'Inp'+('Rsi' if kind == 'rsi' else 'Adx')+('Exit' if purpose == 'exit' else 'Entry')
            item['period'] = integer(prefix+'Period')
            if kind == 'rsi':
                item.update(price=choice(prefix+'Price', PRICES), **{k: raw(prefix+k.title()) for k in ('lower','middle','upper')})
        indicators.append(item)

    def operand(source, candle, fixed):
        if source <= 8:
            return {'kind': 'price', 'source': {v: k for k, v in PRICE_SOURCES.items()}[source], 'candle': candle}
        if source == 9:
            return {'kind': 'fixed', 'value': fixed}
        slot, line = divmod(source-(22 if source >= 22 else 10), 3)
        return {'kind': 'indicator', 'slot': slot+1,
                'line': (('upper','middle','lower') if source >= 22 else ('main','di_plus','di_minus'))[line], 'candle': candle}

    entries, exits = [], []
    for index in range(1, 11):
        payload = values.get(f'InpSignal{index}', '')
        if not payload:
            continue
        parts = payload.split(',')
        op, usage, side, source, candle, comparison, reference, refbar = map(lambda v: int(Decimal(v)), parts[:8])
        position_side = side if usage == 0 else -side
        (entries if usage == 0 else exits).append({
            'slot': index, 'operator': {1:'if',2:'and',3:'or'}[op], 'side': 'buy' if position_side == 1 else 'sell',
            'left': operand(source, candle, parts[8]), 'right': operand(reference, refbar, parts[8]),
            'comparison': {v:k for k,v in COMPARISONS.items()}[comparison],
            'distance': parts[9], 'distance_unit': {0:'none',1:'points',2:'percent'}[int(Decimal(parts[10]))],
        })
    payload = {
        'schema_version': '1.0', 'name': raw('InpName'), 'magic': integer('InpMagic'),
        'metadata': {'origin': 'import'},
        'operation': {'market': choice('InpMarket', {'forex':0,'b3':1}),
                      'trade_mode': choice('InpTradeMode', {'day_trade':0,'swing_trade':1}),
                      'direction': choice('InpDirection', {'both':0,'buy':1,'sell':2}), 'lot': raw('InpLot')},
        'session': {'entry_start': clock(integer('InpEntryStart')), 'entry_end': clock(integer('InpEntryEnd'))},
        'order': order, 'indicators': indicators, 'entry_rules': entries, 'exit_rules': exits, 'risk': risk,
        'display': {'show_panel': boolean('InpExibirPainel'), 'show_histograms': boolean('InpExibirHistogramas'),
                    'histogram_bars': integer('InpHistogramasBarras')},
    }
    spec = StrategySpec.model_validate(payload)
    _, bindings = compile_strategy(spec, include_bindings=True)
    by_input = {key: (path, options, kind) for path, (key, options, kind) in bindings.items()}
    optimization = []
    for key, native in values.items():
        parts = native.split('||')
        if len(parts) != 5 or parts[4] != 'Y':
            continue
        if key not in by_input:
            raise UniValidationError('UNMODELED_OPTIMIZATION', f'O modelo não representa a otimização de {key}; arquivo preservado no fluxo antigo.')
        path, options, kind = by_input[key]
        if kind == 'choice':
            reverse = {v: k for k, v in options.items()}
            # A non-unit enum stride cannot be represented by a contiguous choice range.
            if Decimal(parts[2]) != 1:
                raise UniValidationError('UNMODELED_OPTIMIZATION', f'Passo de enum não representável em {key}.')
            item = {'kind': kind, 'parameter': path, 'start': reverse[int(Decimal(parts[1]))], 'end': reverse[int(Decimal(parts[3]))]}
        elif kind == 'time':
            if Decimal(parts[2]) != 5:
                raise UniValidationError('UNMODELED_OPTIMIZATION', f'Passo de horário não representável em {key}.')
            item = {'kind': kind, 'parameter': path, 'start': clock(int(Decimal(parts[1]))), 'end': clock(int(Decimal(parts[3])))}
        else:
            item = {'kind': kind, 'parameter': path, 'start': parts[1], 'step': parts[2], 'end': parts[3]}
        optimization.append(item)
    return StrategySpec.model_validate(payload | {'optimization': optimization})
