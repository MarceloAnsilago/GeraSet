"""Symbol-independent Uni configuration rules, applied before starting MT5.

Scalar types/ranges are checked by presets.py. Domains here include only values
actually reached by an active optimization, never the inactive N columns.
"""
from decimal import Decimal, ROUND_FLOOR
import math

from .errors import BridgeError


class Configuration:
    def __init__(self, values, contract):
        self.values, self.contract = values, contract

    def parts(self, key):
        return self.values.get(key, str(self.contract[key]['default'])).split('||')

    def fixed(self, key):
        return Decimal(self.parts(key)[0])

    def domain(self, key, optimized):
        parts = self.parts(key)
        if not optimized or len(parts) != 5 or parts[4] != 'Y':
            value = Decimal(parts[0])
            return value, value, Decimal(1)
        start, step, stop = map(Decimal, parts[1:4])
        count = ((stop-start)/step).to_integral_value(rounding=ROUND_FLOOR)
        return start, start+count*step, step

    def choices(self, key, optimized):
        start, stop, step = self.domain(key, optimized)
        return set(range(int(start), int(stop)+1, int(step)))

    @staticmethod
    def fail(message):
        raise BridgeError('INVALID_SET', message)

    def validate(self, optimized):
        d = lambda key: self.domain(key, optimized)
        choices = lambda key: self.choices(key, optimized)
        a, b = d('InpEntryStart'), d('InpEntryEnd')
        if any(b[0] <= n <= b[1] and (n-b[0]) % b[2] == 0
               for n in range(int(a[0]), int(a[1])+1, int(a[2]))):
            self.fail('Horários: início e fim devem ser diferentes em todas as combinações.')

        take = choices('InpTakeMode')
        uses_multiple = 0 in take or (-1 in take and d('InpTakeProfit')[0] == 0)
        stop_modes = choices('InpStopMode')
        no_candle = 1 in stop_modes or (0 in stop_modes and d('InpStopCandleMultiplier')[0] == 0)
        if uses_multiple and d('InpTakeStopMultiplier')[1] > 0 and no_candle and d('InpStopLoss')[0] == 0:
            self.fail('Take Profit em vezes o stop exige Stop Loss maior que zero, inclusive na otimização.')

        for prefix, label in (('InpBreakeven', 'Breakeven'), ('InpTrailing', 'Trailing stop'), ('InpMovingStop', 'Stop móvel')):
            if not choices(prefix+'Mode') - {0}:
                continue
            trigger = d(prefix+'Trigger')
            if prefix == 'InpBreakeven':
                if trigger[0] <= 0 or d(prefix+'Offset')[1] >= trigger[0]:
                    self.fail('Breakeven: ativação positiva e proteção menor que a ativação em todas as combinações.')
            elif any(d(prefix+suffix)[0] <= 0 for suffix in ('Trigger', 'Distance', 'Step')):
                self.fail(f'{label}: ativação, distância e passo devem ser positivos em todas as combinações.')

        types = [choices(f'InpIndicator{i}Type') for i in range(1, 5)]
        usages = [choices(f'InpIndicator{i}Exit') for i in range(1, 5)]
        for i in range(4):
            for j in range(i):
                if types[i] & types[j] & {1, 2} and usages[i] & usages[j]:
                    self.fail('RSI e ADX permitem apenas um indicador por finalidade, inclusive na otimização.')
            if 1 in types[i]:
                for usage in usages[i]:
                    prefix = 'InpRsi'+('Exit' if usage else 'Entry')
                    if not (d(prefix+'Lower')[1] < d(prefix+'Middle')[0] and d(prefix+'Middle')[1] < d(prefix+'Upper')[0]):
                        self.fail('RSI: inferior < médio < superior em todas as combinações.')
        self.validate_signals(types, usages)

    def source(self, source, usage, types, usages):
        if 0 <= source <= 8:
            return {0}, None, False
        if source == 9:
            return {-1}, None, True
        if 10 <= source <= 21:
            slot, buffer = divmod(source-10, 3)
            allowed = {0, 1, 2} if buffer == 0 else {2}
            if not types[slot] <= allowed or usages[slot] != {usage}:
                self.fail('Condição: buffer, indicador ou finalidade incompatível, inclusive na otimização.')
            return {0 if kind == 0 else 1 for kind in types[slot]}, slot, False
        if 22 <= source <= 33:
            slot = (source-22)//3
            if types[slot] != {1} or usages[slot] != {usage}:
                self.fail('Condição: nível exige RSI com a mesma finalidade.')
            return {1}, slot, True
        self.fail('Condição: fonte desconhecida.')

    def validate_signals(self, types, usages):
        groups = set()
        for index in range(1, 11):
            payload = self.values.get(f'InpSignal{index}', '')
            if not payload:
                continue
            parts = payload.split(',')
            numbers = [Decimal(part) for part in parts]
            if any(not math.isfinite(float(n)) for n in numbers) or any(numbers[i] != int(numbers[i]) for i in (*range(8), 10)):
                self.fail(f'Condição {index}: números finitos e códigos inteiros exigidos.')
            op, usage, side, source, bar, comparison, reference, refbar = map(int, numbers[:8])
            fixed, distance, unit = numbers[8:]
            if (op not in (1, 2, 3) or usage not in (0, 1) or side not in (-1, 1) or source == 9
                    or not 0 <= bar <= 3 or not 0 <= refbar <= 3 or not 0 <= comparison <= 10
                    or distance < 0 or unit not in (0, 1, 2) or (unit == 0 and distance != 0)):
                self.fail(f'Condição {index}: códigos, candles ou distância inválidos.')
            a, aslot, aconstant = self.source(source, usage, types, usages)
            b, bslot, bconstant = self.source(reference, usage, types, usages)
            if comparison >= 9 and ((not aconstant and bar == 0) or (not bconstant and refbar == 0)):
                self.fail(f'Condição {index}: cruzar e fechar exige candles fechados.')
            same_slot = aslot is not None and aslot == bslot
            if (-1 not in b and not same_slot and any(x != y for x in a for y in b)
                    or unit == 1 and distance > 0 and (1 in a or 1 in b)
                    or unit == 2 and distance > 0 and reference == 9 and fixed == 0):
                self.fail(f'Condição {index}: escalas ou unidades incompatíveis.')
            group = usage, side
            if (group not in groups and op != 1) or (group in groups and op == 1):
                self.fail(f'Condição {index}: a primeira regra de cada finalidade/lado usa Se; as demais E/Ou.')
            groups.add(group)


def validate_configuration(values, contract):
    config = Configuration(values, contract)
    config.validate(optimized=False)
    config.validate(optimized=True)
