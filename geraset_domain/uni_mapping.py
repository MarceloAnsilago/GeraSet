"""Semantic strategy -> native inputs for compatibility checks, not file export.

The same parser/validators serve this mapping and the existing Bridge adapter.
No filesystem writes, UI state, trading activation or model calls occur here.
"""
import base64
import hashlib
import json
from decimal import Decimal

from .errors import UniValidationError
from .uni_presets import CONTRACT, parse_set


PRICES = dict(zip(('close','open','high','low','median','typical','weighted'), range(1, 8)))
TIMEFRAMES = dict(zip(('current','M1','M2','M3','M4','M5','M6','M10','M12','M15','M20','M30',
                      'H1','H2','H3','H4','H6','H8','H12','D1','W1','MN1'), range(22)))
PRICE_SOURCES = dict(zip(('close','open','high','low','day_open','day_high','day_low',
                         'previous_day_high','previous_day_low'), range(9)))
COMPARISONS = dict(zip(('gt','lt','gte','lte','eq','ne','touch','cross_up','cross_down','cross_close_up','cross_close_down'), range(11)))
MODES = {'disabled': 0, 'points': 1, 'percent': 2}


def contract_hash():
    return hashlib.sha256(json.dumps(CONTRACT, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def text(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, Decimal):
        return format(value, 'f')
    return str(value)


def minutes(clock):
    hours, minute = map(int, clock.split(':'))
    return hours*60+minute


def compile_strategy(spec):
    values, bindings = {}, {}

    def put(key, value, path=None, choices=None, kind='numeric'):
        values[key] = text(value)
        if path:
            bindings[path] = key, choices, kind

    put('InpName', spec.name)
    put('InpMagic', spec.magic)
    put('InpAutoStart', False)
    put('InpTesterAutoStart', False)
    put('InpMarket', {'forex': 0, 'b3': 1}[spec.operation.market])
    put('InpTradeMode', {'day_trade': 0, 'swing_trade': 1}[spec.operation.trade_mode])
    put('InpLot', spec.operation.lot)
    direction = {'both': 0, 'buy': 1, 'sell': 2}
    put('InpDirection', direction[spec.operation.direction], 'operation.direction', direction, 'choice')
    put('InpEntryStart', minutes(spec.session.entry_start), 'session.entry_start', kind='time')
    put('InpEntryEnd', minutes(spec.session.entry_end), 'session.entry_end', kind='time')
    pending = spec.order.type == 'pending'
    put('InpOrderMode', int(pending))
    references = {'high': 0, 'low': 1, 'open': 2, 'close': 3}
    put('InpPendingReference', references[spec.order.reference] if pending else 0,
        'order.reference' if pending else None, references, 'choice')
    put('InpPendingCandle', spec.order.candle if pending else 1, 'order.candle' if pending else None)
    put('InpPendingMirrorSell', spec.order.mirror_sell if pending else False)
    risk = spec.risk
    put('InpTargetUnit', {'points': 0, 'percent': 1}[risk.target_unit])
    candle = risk.stop_loss.type == 'candle'
    put('InpStopMode', 0 if candle else 1)
    put('InpStopLoss', risk.stop_loss.distance, 'risk.stop_loss.distance')
    put('InpStopCandleMultiplier', risk.stop_loss.multiplier if candle else 0)
    put('InpStopCandle', risk.stop_loss.candle if candle else 1, 'risk.stop_loss.candle' if candle else None)
    measures = {'total': 0, 'body': 1}
    put('InpStopBody', measures[risk.stop_loss.measure] if candle else 0,
        'risk.stop_loss.measure' if candle else None, measures, 'choice')
    multiple = risk.take_profit.type == 'stop_multiple'
    put('InpTakeMode', 0 if multiple else 1)
    put('InpTakeProfit', 0 if multiple else risk.take_profit.distance, None if multiple else 'risk.take_profit.distance')
    put('InpTakeStopMultiplier', risk.take_profit.multiplier if multiple else 0,
        'risk.take_profit.multiplier' if multiple else None)
    for key, prefix, item, fields in (
        ('breakeven', 'InpBreakeven', risk.breakeven, {'trigger': 'Trigger', 'offset': 'Offset'}),
        ('trailing', 'InpTrailing', risk.trailing, {'trigger': 'Trigger', 'distance': 'Distance', 'adjustment_step': 'Step'}),
        ('moving_stop', 'InpMovingStop', risk.moving_stop, {'trigger': 'Trigger', 'distance': 'Distance', 'adjustment_step': 'Step'}),
    ):
        put(prefix+'Mode', MODES[item.mode])
        for field, suffix in fields.items():
            put(prefix+suffix, getattr(item, field) if item.mode != 'disabled' else 0,
                f'risk.{key}.{field}' if item.mode != 'disabled' else None)

    indicators = {i.slot: i for i in spec.indicators}
    for slot in range(1, 5):
        indicator = indicators.get(slot)
        put(f'InpIndicator{slot}Type', {'ma': 0, 'rsi': 1, 'adx': 2}[indicator.type] if indicator else -1)
        put(f'InpIndicator{slot}Exit', int(indicator.purpose == 'exit') if indicator else 0)
        put(f'InpIndicator{slot}Timeframe', TIMEFRAMES[indicator.timeframe] if indicator else 0,
            f'indicators.{slot}.timeframe' if indicator else None, TIMEFRAMES, 'choice')
        if indicator is None:
            continue
        path = f'indicators.{slot}'
        if indicator.type == 'ma':
            prefix = f'InpIndicator{slot}Ma'
            methods = {'sma': 0, 'ema': 1, 'smma': 2, 'lwma': 3}
            put(prefix+'Period', indicator.period, path+'.period')
            put(prefix+'Shift', indicator.shift, path+'.shift')
            put(prefix+'Method', methods[indicator.method], path+'.method', methods, 'choice')
            put(prefix+'Price', PRICES[indicator.price], path+'.price', PRICES, 'choice')
        else:
            instance = 'Exit' if indicator.purpose == 'exit' else 'Entry'
            prefix = 'Inp'+('Rsi' if indicator.type == 'rsi' else 'Adx')+instance
            put(prefix+'Period', indicator.period, path+'.period')
            if indicator.type == 'rsi':
                put(prefix+'Price', PRICES[indicator.price], path+'.price', PRICES, 'choice')
                for field in ('lower', 'middle', 'upper'):
                    put(prefix+field.title(), getattr(indicator, field), path+'.'+field)

    def operand(item):
        if item.kind == 'price':
            return PRICE_SOURCES[item.source], item.candle
        if item.kind == 'fixed':
            return 9, 0
        if item.line in ('upper', 'middle', 'lower'):
            return 22+(item.slot-1)*3+('upper','middle','lower').index(item.line), 0
        return 10+(item.slot-1)*3+('main','di_plus','di_minus').index(item.line), item.candle

    rules = []
    for usage, items in enumerate((spec.entry_rules, spec.exit_rules)):
        for rule in items:
            a, bar = operand(rule.left)
            b, refbar = operand(rule.right)
            side = 1 if rule.side == 'buy' else -1
            if usage:
                side = -side  # native buy signal closes sells; semantic side is position closed
            fields = ({'if': 1, 'and': 2, 'or': 3}[rule.operator], usage, side,
                      a, bar, COMPARISONS[rule.comparison], b, refbar,
                      rule.right.value if rule.right.kind == 'fixed' else 0,
                      rule.distance, {'none': 0, 'points': 1, 'percent': 2}[rule.distance_unit])
            rules.append(','.join(map(text, fields)))
    for index in range(10):
        put(f'InpSignal{index+1}', rules[index] if index < len(rules) else '')

    seen = set()
    for item in spec.optimization:
        if item.parameter in seen or item.parameter not in bindings:
            raise UniValidationError('INVALID_OPTIMIZATION', f'Parâmetro duplicado, inativo ou não otimizável: {item.parameter}.')
        seen.add(item.parameter)
        key, choices, kind = bindings[item.parameter]
        if item.kind != kind:
            raise UniValidationError('INVALID_OPTIMIZATION', f'Tipo de intervalo incompatível com {item.parameter}.')
        if kind == 'choice':
            if item.start not in choices or item.end not in choices:
                raise UniValidationError('INVALID_OPTIMIZATION', f'Opção inválida em {item.parameter}.')
            start, end = sorted((choices[item.start], choices[item.end]))
            step = 1
        elif kind == 'time':
            start, end = sorted((minutes(item.start), minutes(item.end)))
            step = 5
        else:
            start, step, end = item.start, item.step, item.end
        # Equal bounds are disabled and must not replace the independent fixed value.
        values[key] = '||'.join(map(text, (values[key], start, step, end)))+'||'+('Y' if start != end else 'N')

    # Reuse the exact decoder, scalar and relational validators used by the Bridge.
    # This byte sequence exists only in memory; public .set export remains unchanged.
    payload = '\n'.join(f'{key}={value}' for key, value in values.items()).encode('utf-8')
    parse_set(base64.b64encode(payload).decode(), 1024*1024)
    return values
