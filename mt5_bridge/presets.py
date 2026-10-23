"""Bridge adapter for the shared deterministic Uni validators."""
from geraset_domain import uni_presets as shared
from geraset_domain.errors import UniValidationError
from .errors import BridgeError

CONTRACT = shared.CONTRACT


def _call(function, *args):
    try:
        return function(*args)
    except UniValidationError as exc:
        raise BridgeError(exc.code, exc.message, exc.status) from exc


def parse_set(encoded, limit):
    return _call(shared.parse_set, encoded, limit)


def number(value, key, kind):
    return _call(shared.number, value, key, kind)


def validate_value(value, key):
    return _call(shared.validate_value, value, key)


def execution_set(values, enable_entries):
    # Explicit tester-only overrides. Original receipt remains an immutable artifact.
    actual = dict(values)
    actual['InpAutoStart'] = 'false'
    actual['InpTesterAutoStart'] = str(enable_entries).lower()
    return ('\ufeff'+'\r\n'.join(f'{k}={v}' for k,v in actual.items())+'\r\n').encode('utf-16-le')
