import base64
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path
from .errors import BridgeError

CONTRACT = json.loads((Path(__file__).parent/'contracts/uni_inputs.json').read_text())


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
        if not match or match[1] not in CONTRACT or match[1] in values:
            raise BridgeError('INVALID_SET', 'Input desconhecido, duplicado ou linha inválida no .set.')
        key, value = match.groups()
        parts = value.split('||')
        if len(parts) not in (1,5):
            raise BridgeError('INVALID_SET', f'Intervalo inválido em {key}.')
        kind = CONTRACT[key]['kind']
        if kind == 'string':
            if len(parts) != 1 or len(parts[0]) > 256:
                raise BridgeError('INVALID_SET', f'Texto inválido em {key}.')
            if key.startswith('InpSignal') and parts[0]:
                fields = parts[0].split(',')
                if len(fields) != 11 or any(not re.fullmatch(r'-?\d+(?:\.\d+)?', f) for f in fields):
                    raise BridgeError('INVALID_SET', f'Condição inválida em {key}.')
        elif kind == 'bool':
            if parts[0].lower() not in ('true','false','0','1'):
                raise BridgeError('INVALID_SET', f'Booleano inválido em {key}.')
        else:
            number(parts[0], key, kind)
        if len(parts) == 5:
            if parts[4] not in ('Y','N') or kind == 'string':
                raise BridgeError('INVALID_SET', f'Otimização inválida em {key}.')
            if parts[4] == 'Y':
                start, step, stop = [number(p,key,kind) for p in parts[1:4]]
                if step <= 0 or stop < start:
                    raise BridgeError('INVALID_SET', f'Intervalo crescente e passo positivo exigidos em {key}.')
                ranges[key] = int(((stop-start)/step).to_integral_value(rounding=ROUND_FLOOR))+1
        values[key] = value
    if not {'InpName','InpMagic','InpLot'} <= values.keys():
        raise BridgeError('INVALID_SET', 'Identificação e lote do Uni ausentes.')
    if not any(values.get(f'InpSignal{i}', '').strip() for i in range(1,11)):
        raise BridgeError('INVALID_SET', 'Configure ao menos uma condição do Uni.')
    return raw, values, ranges, hashlib.sha256(raw).hexdigest()


def number(value, key, kind):
    try:
        result = Decimal(value)
        if not result.is_finite() or (result and abs(result.adjusted())>20) or (kind in ('int','long','enum','bool') and result != result.to_integral_value()):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError) as exc:
        raise BridgeError('INVALID_SET', f'Número inválido em {key}.') from exc


def execution_set(values, enable_entries):
    # Explicit tester-only overrides. Original receipt remains an immutable artifact.
    actual = dict(values)
    actual['InpAutoStart'] = 'false'
    actual['InpTesterAutoStart'] = str(enable_entries).lower()
    return ('\ufeff'+'\r\n'.join(f'{k}={v}' for k,v in actual.items())+'\r\n').encode('utf-16-le')
