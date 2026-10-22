import base64
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path
from .errors import BridgeError

CONTRACT = json.loads((Path(__file__).parent/'contracts/uni_inputs.json').read_text(encoding='utf-8'))


def parse_set(encoded: str, limit: int):
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > limit:
            raise BridgeError('SET_TOO_LARGE', 'O .set excede o limite.', 413)
        text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    except (ValueError, UnicodeError) as exc:
        raise BridgeError('INVALID_SET', 'Use um .set UTF-8 ou UTF-16 válido em base64.') from exc
    if '\x00' in text:
        raise BridgeError('INVALID_SET', 'Caracteres nulos no .set.')
    values, ranges = {}, {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        match = re.fullmatch(r'(Inp\w+)=(.*)', line)
        if not match:
            raise BridgeError('INVALID_SET', 'Linha inválida no .set; use o formato Input=valor.')
        if match[1] not in CONTRACT:
            raise BridgeError('INVALID_SET', f'Input não reconhecido pelo contrato do Bridge: {match[1]}.')
        if match[1] in values:
            raise BridgeError('INVALID_SET', f'Input duplicado no .set: {match[1]}.')
        key, value = match.groups()
        spec = CONTRACT[key]
        if spec.get('internal'):
            raise BridgeError('INVALID_SET', f'O input {key} é reservado ao executor do Bridge.')
        parts = value.split('||')
        if len(parts) not in (1,5):
            raise BridgeError('INVALID_SET', f'Intervalo inválido em {key}.')
        kind = CONTRACT[key]['kind']
        if kind == 'string':
            if (len(parts) != 1 or not spec.get('min_length', 0) <= len(parts[0]) <= spec.get('max_length', 256)
                    or key == 'InpName' and (not parts[0].strip() or re.search(r'[\x00-\x1f\x7f|]', parts[0]))):
                raise BridgeError('INVALID_SET', f'Texto inválido em {key}.')
            if key.startswith('InpSignal') and parts[0]:
                fields = parts[0].split(',')
                if len(fields) != 11 or any(not re.fullmatch(r'-?\d+(?:\.\d+)?', f) for f in fields):
                    raise BridgeError('INVALID_SET', f'Condição inválida em {key}.')
        elif kind == 'bool':
            if parts[0].lower() not in ('true','false','0','1'):
                raise BridgeError('INVALID_SET', f'Booleano inválido em {key}.')
        else:
            validate_value(number(parts[0], key, kind), key)
        if len(parts) == 5:
            if parts[4] not in ('Y','N') or kind == 'string':
                raise BridgeError('INVALID_SET', f'Otimização inválida em {key}.')
            if parts[4] == 'Y':
                if not CONTRACT[key].get('optimizable',True):
                    raise BridgeError('INVALID_SET', f'O input estático {key} não permite otimização.')
                start, step, stop = [number(p,key,kind) for p in parts[1:4]]
                validate_value(start, key)
                validate_value(stop, key)
                if step <= 0 or stop < start:
                    raise BridgeError('INVALID_SET', f'Intervalo crescente e passo positivo exigidos em {key}.')
                if spec.get('multiple_of') and step % Decimal(str(spec['multiple_of'])):
                    raise BridgeError('INVALID_SET', f'Passo incompatível com a unidade de {key}.')
                allowed = spec.get('enum_values', {}).values() or spec.get('values')
                if allowed and any(start <= n <= stop and n not in allowed
                                   for n in range(int(start), int(stop)+1, int(step))):
                    raise BridgeError('INVALID_SET', f'Intervalo contém opção inválida em {key}.')
                ranges[key] = int(((stop-start)/step).to_integral_value(rounding=ROUND_FLOOR))+1
        values[key] = value
    if not {'InpName','InpMagic','InpLot'} <= values.keys():
        raise BridgeError('INVALID_SET', 'Identificação e lote do Uni ausentes.')
    if not any(values.get(f'InpSignal{i}', '').strip() for i in range(1,11)):
        raise BridgeError('INVALID_SET', 'Configure ao menos uma condição do Uni.')
    validate_managed_stops(values)
    return raw, values, ranges, hashlib.sha256(raw).hexdigest()


def number(value, key, kind):
    try:
        result = Decimal(value)
        if not result.is_finite() or (result and abs(result.adjusted())>20) or (kind in ('int','long','enum','bool','color') and result != result.to_integral_value()):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError) as exc:
        raise BridgeError('INVALID_SET', f'Número inválido em {key}.') from exc


def validate_value(value, key):
    """Scalar input limits. Symbol-dependent and cross-field rules remain in Uni."""
    spec = CONTRACT[key]
    allowed = spec.get('enum_values', {}).values() or spec.get('values')
    invalid = (allowed and value not in allowed or
               'min' in spec and value < Decimal(str(spec['min'])) or
               'max' in spec and value > Decimal(str(spec['max'])) or
               'exclusive_min' in spec and value <= Decimal(str(spec['exclusive_min'])) or
               'multiple_of' in spec and value % Decimal(str(spec['multiple_of'])) != 0)
    if invalid:
        raise BridgeError('INVALID_SET', f'Valor fora das opções ou limites permitidos em {key}.')


def validate_managed_stops(values):
    """Standard distance policy only; indicator-following will need a new contract.

    Validate fixed inputs as well as every potentially enabled optimization
    combination. Do not impose distance < trigger: Uni permits that combination.
    """
    for prefix, label in (('InpTrailing', 'Trailing stop'), ('InpMovingStop', 'Stop móvel')):
        def parts(suffix):
            key = prefix+suffix
            return values.get(key, str(CONTRACT[key]['default'])).split('||')

        mode = parts('Mode')
        enabled = Decimal(mode[0]) != 0
        optimized_enabled = Decimal(mode[3]) > 0 if len(mode) == 5 and mode[4] == 'Y' else enabled
        for suffix in ('Trigger', 'Distance', 'Step'):
            field = parts(suffix)
            if enabled and Decimal(field[0]) <= 0:
                raise BridgeError('INVALID_SET', f'{label}: ativação, distância e passo devem ser maiores que zero.')
            minimum = field[1] if len(field) == 5 and field[4] == 'Y' else field[0]
            if optimized_enabled and Decimal(minimum) <= 0:
                raise BridgeError('INVALID_SET', f'{label}: toda combinação habilitada deve ter ativação, distância e passo positivos.')


def execution_set(values, enable_entries):
    # Explicit tester-only overrides. Original receipt remains an immutable artifact.
    actual = dict(values)
    actual['InpAutoStart'] = 'false'
    actual['InpTesterAutoStart'] = str(enable_entries).lower()
    return ('\ufeff'+'\r\n'.join(f'{k}={v}' for k,v in actual.items())+'\r\n').encode('utf-16-le')
