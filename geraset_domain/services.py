"""Offline configuration, validation, export and legacy equivalence services."""
import base64
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
import hashlib
import json
import re

from pydantic import Field, ValidationError

from .configuration import strategy_from_inputs
from .errors import UniValidationError
from .strategy import Model, StrategySpec
from .uni_mapping import compile_strategy, contract_hash, text
from .uni_presets import CONTRACT, parse_set


@dataclass(frozen=True)
class Issue:
    category: str
    code: str
    message: str
    path: tuple = ()


@dataclass(frozen=True)
class ConfigurationResult:
    strategy: StrategySpec | None
    errors: tuple[Issue, ...] = ()
    warnings: tuple[Issue, ...] = ()
    export_options: dict | None = None

    @property
    def valid(self):
        return self.strategy is not None and not self.errors

    def as_dict(self):
        return {'valid': self.valid, 'financial_state': 'not_tested', 'contract_sha256': contract_hash(),
                'errors': [asdict(e) for e in self.errors], 'warnings': [asdict(w) for w in self.warnings],
                'strategy': self.strategy.model_dump(mode='json') if self.strategy else None,
                'export_options': self.export_options}


class StrategyServiceError(Exception):
    def __init__(self, errors):
        self.errors = tuple(errors)
        super().__init__('; '.join(e.message for e in errors))


class ExportOptions(Model):
    # Test-only activation belongs to export/execution, not live strategy inputs.
    tester_auto_start: bool | None = Field(default=None, strict=True)


@dataclass(frozen=True)
class SetArtifact:
    filename: str
    contents: bytes
    inputs: dict[str, str]
    warnings: tuple[Issue, ...]

    @property
    def sha256(self):
        return hashlib.sha256(self.contents).hexdigest()


def _issues(exc):
    if isinstance(exc, UniValidationError):
        return (Issue('uni', exc.code, exc.message),)
    issues = []
    for error in exc.errors():
        cause = error.get('ctx', {}).get('error')
        cause = getattr(cause, '__cause__', None)
        if isinstance(cause, UniValidationError):
            issues.append(Issue('uni', cause.code, cause.message, error['loc']))
        else:
            issues.append(Issue('structural', error['type'], error['msg'], error['loc']))
    return tuple(issues)


def _warnings(spec):
    risk = spec.risk
    result = [Issue('financial', 'NOT_FINANCIALLY_VALIDATED', 'Arquivo tecnicamente válido não comprova desempenho nem aprovação financeira.'),
              Issue('operational', 'SYMBOL_CHECKS_PENDING', 'Volume, margem, tick, stops, histórico e aceitação da corretora exigem o contexto do ativo.')]
    if risk.stop_loss.distance == 0 and (risk.stop_loss.type == 'fixed' or risk.stop_loss.multiplier == 0):
        result.append(Issue('financial', 'NO_STOP_LOSS', 'A configuração não possui Stop Loss inicial.'))
    if (risk.take_profit.type == 'fixed' and risk.take_profit.distance == 0 or
            risk.take_profit.type == 'stop_multiple' and risk.take_profit.multiplier == 0):
        result.append(Issue('financial', 'NO_TAKE_PROFIT', 'A configuração não possui Take Profit inicial.'))
    if risk.target_unit == 'percent' or any(item.mode == 'percent' for item in (risk.breakeven, risk.trailing, risk.moving_stop)):
        result.append(Issue('financial', 'PRICE_PERCENT_NOT_EQUITY_RISK', 'Os percentuais são distâncias de preço, não percentuais de risco sobre o patrimônio.'))
    return tuple(result)


def configure_strategy(payload):
    """Accept a v1 object/JSON string; return normalized configuration and diagnostics."""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except (ValueError, UnicodeError):
            return ConfigurationResult(None, (Issue('structural', 'INVALID_JSON', 'Envie uma estratégia JSON válida.'),))
    try:
        spec = StrategySpec.model_validate(payload)
    except ValidationError as exc:
        return ConfigurationResult(None, _issues(exc))
    return ConfigurationResult(spec, warnings=_warnings(spec))


def to_uni_inputs(payload, options=None):
    result = configure_strategy(payload)
    if not result.valid:
        raise StrategyServiceError(result.errors)
    try:
        options = ExportOptions.model_validate({} if options is None else options)
    except ValidationError as exc:
        raise StrategyServiceError(_issues(exc)) from exc
    values = compile_strategy(result.strategy)
    # Live startup is never enabled by this service. Test startup is explicit.
    if options.tester_auto_start is not None:
        values['InpTesterAutoStart'] = text(options.tester_auto_start)
    return result, values


def set_filename(name):
    name = re.sub(r'\.set$', '', name.strip(), flags=re.I)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).rstrip('. ')[:120] or 'Meu setup'
    if re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', name, flags=re.I):
        name = '_'+name
    return name+'.set'


def export_strategy(payload, options=None):
    """Deterministic UTF-16LE/BOM/CRLF export; no Bridge or MT5 connection."""
    result, values = to_uni_inputs(payload, options)
    metadata = {'format': 'geraset-strategy', 'version': 1, 'strategy': result.strategy.model_dump(mode='json'),
                'export_options': ExportOptions.model_validate({} if options is None else options).model_dump(mode='json')}
    lines = ['; GeraSet Python -> UniEA: strategy schema 1.0',
             *(f'{key}={value}' for key, value in values.items()),
             *('; '+line for line in json.dumps(metadata, ensure_ascii=False, indent=2).splitlines()), '']
    contents = b'\xff\xfe'+'\r\n'.join(lines).encode('utf-16-le')
    return SetArtifact(set_filename(result.strategy.name), contents, values, result.warnings)


def _signature(key, value):
    parts = value.split('||')
    spec = CONTRACT[key]
    if spec['kind'] == 'string':
        fixed = tuple(Decimal(v) for v in parts[0].split(',')) if key.startswith('InpSignal') and parts[0] else parts[0]
    elif spec['kind'] == 'bool':
        fixed = parts[0].lower() in ('true', '1')
    else:
        fixed = Decimal(parts[0])
    active = tuple(map(Decimal, parts[1:4])) if len(parts) == 5 and parts[4] == 'Y' else None
    return fixed, active


def compare_inputs(original, generated):
    differences = []
    for key in sorted(original.keys() | generated.keys()):
        default = text(CONTRACT[key]['default'])
        before, after = original.get(key, default), generated.get(key, default)
        if key == 'InpTakeMode':
            # Native legacy AUTO is equivalent to the mode resolved from the
            # fixed distance. Other dependent parameters/ranges are still compared.
            if before.split('||')[0] == '-1' and (len(before.split('||')) != 5 or before.split('||')[4] != 'Y'):
                before = '1' if Decimal(original.get('InpTakeProfit', '0').split('||')[0]) > 0 else '0'
            if after.split('||')[0] == '-1' and (len(after.split('||')) != 5 or after.split('||')[4] != 'Y'):
                after = '1' if Decimal(generated.get('InpTakeProfit', '0').split('||')[0]) > 0 else '0'
        if _signature(key, before) != _signature(key, after):
            differences.append({'input': key, 'original': original.get(key), 'python': generated.get(key)})
    return differences


def configure_from_set(contents):
    """Read existing presets without evaluating comments or changing a UI draft."""
    try:
        _, values, _, _ = parse_set(base64.b64encode(contents).decode(), 1024*1024)
        decoded = contents.decode('utf-16' if contents.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
        lines = decoded.splitlines()
        start = next((i for i, line in enumerate(lines) if re.fullmatch(r';\s*\{\s*', line)), None)
        metadata = None
        if start is not None:
            try:
                metadata = json.loads('\n'.join(re.sub(r'^;\s?', '', line) for line in lines[start:] if line.startswith(';')))
            except ValueError:
                metadata = None
            if isinstance(metadata, dict) and metadata.get('format') == 'geraset-strategy':
                if type(metadata.get('version')) is not int or metadata.get('version') != 1:
                    return ConfigurationResult(None, (Issue('structural', 'UNSUPPORTED_SET_METADATA', 'Versão dos metadados não suportada.'),))
                result = configure_strategy(metadata.get('strategy'))
                if not result.valid:
                    return result
                _, expected = to_uni_inputs(result.strategy, metadata.get('export_options'))
                if compare_inputs(values, expected):
                    return ConfigurationResult(None, (Issue('uni', 'PARAMETER_MISMATCH', 'Inputs diferem da estratégia dos metadados.'),))
                meta_options = metadata.get('export_options')
                return replace(result, export_options=ExportOptions.model_validate({} if meta_options is None else meta_options).model_dump(mode='json'))
        if decoded.startswith('; GeraSet Python -> UniEA'):
            return ConfigurationResult(None, (Issue('structural', 'INVALID_SET_METADATA', 'Metadados da estratégia ausentes ou incompletos.'),))
        spec = strategy_from_inputs(values)
        options = {'tester_auto_start': values['InpTesterAutoStart'].split('||')[0].lower() in ('true','1')} if 'InpTesterAutoStart' in values else {}
        result, expected = to_uni_inputs(spec, options)
        differences = compare_inputs(values, expected)
        if differences:
            return ConfigurationResult(None, tuple(Issue('uni', 'UNMODELED_PARAMETER', f'Conversão não preserva {d["input"]}.', (d['input'],)) for d in differences))
        return replace(result, export_options=options)
    except (UniValidationError, ValidationError) as exc:
        return ConfigurationResult(None, _issues(exc))
    except StrategyServiceError as exc:
        return ConfigurationResult(None, exc.errors)


def compare_legacy_set(contents):
    """Produce an independent Python artifact before checking semantic equivalence."""
    try:
        _, original, _, digest = parse_set(base64.b64encode(contents).decode(), 1024*1024)
        spec = strategy_from_inputs(original)
    except (UniValidationError, ValidationError) as exc:
        raise StrategyServiceError(_issues(exc)) from exc
    options = {'tester_auto_start': original['InpTesterAutoStart'].split('||')[0].lower() in ('true','1')} if 'InpTesterAutoStart' in original else None
    artifact = export_strategy(spec, options)
    differences = compare_inputs(original, artifact.inputs)
    return {'equivalent': not differences, 'comparison': 'native_values_and_active_optimization',
            'original_sha256': digest, 'python_sha256': artifact.sha256,
            'export_options': ExportOptions.model_validate({} if options is None else options).model_dump(mode='json'),
            'differences': differences, 'configuration': configure_strategy(spec).as_dict()}, artifact


def export_preserving_legacy(payload, contents, options=None):
    """Preserve v2 comments, rule positions, inactive fields and original encoding.

    Only allowed after comparing every effective input and active range with the
    newly compiled Python configuration. Unknown/unmodeled non-default values
    cannot silently pass. This is a compatibility envelope, not a second compiler.
    """
    result, generated = to_uni_inputs(payload, options)
    try:
        _, original, _, _ = parse_set(base64.b64encode(contents).decode(), 1024*1024)
    except UniValidationError as exc:
        raise StrategyServiceError(_issues(exc)) from exc
    differences = compare_inputs(original, generated)
    if differences:
        raise StrategyServiceError(tuple(Issue('uni', 'PARAMETER_MISMATCH', f'Parâmetro divergente: {d["input"]}.', (d['input'],)) for d in differences))
    return SetArtifact(set_filename(result.strategy.name), contents, original, result.warnings)
