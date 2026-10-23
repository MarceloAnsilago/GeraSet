import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from geraset_domain.schema import strategy_schema
from geraset_domain.strategy import StrategySpec, validate_strategy
from geraset_domain.uni_mapping import compile_strategy
from geraset_domain.uni_presets import parse_set as domain_parse
from mt5_bridge.errors import BridgeError
from mt5_bridge.presets import parse_set as bridge_parse


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def proposal():
    return json.loads((ROOT/'examples/rsi-v1.json').read_text(encoding='utf-8'))


def test_json_round_trip_preserves_identity_revision_decimal_values_and_metadata(proposal):
    strategy = StrategySpec.model_validate(proposal)
    restored = StrategySpec.model_validate_json(strategy.model_dump_json())
    assert restored == strategy
    assert restored.strategy_id == strategy.strategy_id
    assert restored.metadata.created_at == strategy.metadata.created_at
    assert restored.operation.lot.as_tuple() == strategy.operation.lot.as_tuple()
    assert restored.revision == 1


def test_native_projection_uses_existing_bridge_validation_and_exit_position_semantics(proposal):
    inputs = compile_strategy(StrategySpec.model_validate(proposal))
    encoded = base64.b64encode('\n'.join(f'{k}={v}' for k, v in inputs.items()).encode()).decode()
    assert domain_parse(encoded, 100000) == bridge_parse(encoded, 100000)
    assert inputs['InpSignal1'] == '1,0,1,10,1,1,9,0,30,0,0'
    assert inputs['InpSignal2'] == '1,1,-1,13,1,0,9,0,70,0,0'  # close buy
    assert inputs['InpRsiEntryPeriod'] == '14||10||5||20||Y'
    assert inputs['InpIndicator1Timeframe'] == '9'  # M15 slot index
    assert inputs['InpIndicator2Timeframe'] == '0'  # inherit execution base
    assert inputs['InpAutoStart'] == inputs['InpTesterAutoStart'] == 'false'
    assert 'InpStrategyTimeframe' not in inputs


def test_execution_hint_never_changes_native_strategy_inputs(proposal):
    original = compile_strategy(StrategySpec.model_validate(proposal))
    proposal['execution_hint'] = {'symbol': 'WIN$', 'base_timeframe': 'H1'}
    assert compile_strategy(StrategySpec.model_validate(proposal)) == original


def test_errors_are_structured_and_financial_state_cannot_be_self_declared(proposal):
    result = validate_strategy(proposal)
    assert result.state == 'structurally_valid'
    assert result.financial_state == 'not_tested'
    assert len(result.contract_sha256) == 64
    assert 'broker_execution' in result.pending_checks
    proposal['approved'] = True
    failed = validate_strategy(proposal)
    assert failed.state == 'invalid' and failed.strategy is None
    assert failed.issues[0].path == ('approved',)
    assert failed.financial_state == 'not_tested'


@pytest.mark.parametrize('mutate', [
    lambda p: p.update(schema_version='2.0'),
    lambda p: p.update(magic=True),
    lambda p: p.update(magic=0),
    lambda p: p.update(revision=1, parent_revision=1),
    lambda p: p.update(name='bad\nInpAutoStart=true'),
    lambda p: p.update(indicators=p['indicators']+[deepcopy(p['indicators'][0])]),
    lambda p: p['indicators'][0].update(period=0),
    lambda p: p['indicators'][0].update(period=14.5),
    lambda p: p['indicators'][0].update(timeframe='M7'),
    lambda p: p['indicators'][0].update(timeframe='Tempo corrente'),
    lambda p: p['risk']['trailing'].update(distance_policy='indicator'),
    lambda p: p['operation'].update(lot='NaN'),
    lambda p: p['operation'].update(lot='1e-10000'),
    lambda p: p['session'].update(entry_start='09:01'),
    lambda p: p['metadata'].update(created_at='2026-10-22T12:00:00'),
    lambda p: p['entry_rules'][0].update(left={'kind': 'fixed', 'value': '10'}),
    lambda p: p.update(entry_rules=[], exit_rules=[]),
    lambda p: p.update(entry_rules=p['entry_rules']*10, exit_rules=p['exit_rules']),
    lambda p: p['execution_hint'].update(base_timeframe='current'),
    lambda p: p.update(native_inputs={'InpAutoStart': True}),
])
def test_rejects_unknown_versions_types_capabilities_and_invalid_structure(proposal, mutate):
    mutate(proposal)
    assert validate_strategy(proposal).state == 'invalid'


@pytest.mark.parametrize('mutate', [
    lambda p: p['session'].update(entry_end='09:00'),
    lambda p: p['risk']['stop_loss'].update(distance='0'),
    lambda p: p['indicators'][0].update(lower='60'),
    lambda p: p['risk']['breakeven'].update(offset='100'),
    lambda p: p['risk']['trailing'].update(adjustment_step='0'),
    lambda p: p['entry_rules'][0]['left'].update(slot=4),
    lambda p: p['entry_rules'][0]['left'].update(line='di_plus'),
    lambda p: p['entry_rules'][0]['left'].update(slot=2),  # exit indicator on entry rule
    lambda p: p['entry_rules'][0].update(operator='and'),
    lambda p: p['optimization'][0].update(start='0'),
    lambda p: p['optimization'][1].update(start='0'),
    lambda p: p['optimization'].append({'kind': 'numeric', 'parameter': 'indicators.1.lower', 'start': '20', 'step': '5', 'end': '55'}),
    lambda p: p['optimization'].append({'kind': 'time', 'parameter': 'session.entry_start', 'start': '00:00', 'end': '23:55'}),
])
def test_reuses_native_business_rules_instead_of_accepting_structurally_valid_incompatibilities(proposal, mutate):
    mutate(proposal)
    result = validate_strategy(proposal)
    assert result.state == 'invalid'
    assert result.issues


@pytest.mark.parametrize('optimization', [
    {'kind': 'numeric', 'parameter': 'InpAutoStart', 'start': 0, 'step': 1, 'end': 1},
    {'kind': 'numeric', 'parameter': 'risk.moving_stop.distance', 'start': 1, 'step': 1, 'end': 2},
    {'kind': 'numeric', 'parameter': 'indicators.4.period', 'start': 1, 'step': 1, 'end': 2},
    {'kind': 'choice', 'parameter': 'indicators.1.timeframe', 'start': 'M5', 'end': 'M7'},
    {'kind': 'numeric', 'parameter': 'indicators.1.timeframe', 'start': 1, 'step': 1, 'end': 2},
    {'kind': 'numeric', 'parameter': 'indicators.1.period', 'start': 1, 'step': 1, 'end': 2},
])
def test_optimization_requires_unique_active_semantic_paths_and_compatible_range_types(proposal, optimization):
    proposal['optimization'].append(optimization)
    assert validate_strategy(proposal).state == 'invalid'


def test_choice_and_time_ranges_use_native_enums_and_minutes_not_labels(proposal):
    proposal['optimization'] = [
        {'kind': 'choice', 'parameter': 'indicators.1.timeframe', 'start': 'M5', 'end': 'M15'},
        {'kind': 'choice', 'parameter': 'operation.direction', 'start': 'sell', 'end': 'buy'},
        {'kind': 'time', 'parameter': 'session.entry_start', 'start': '09:00', 'end': '10:00'},
    ]
    values = compile_strategy(StrategySpec.model_validate(proposal))
    assert values['InpIndicator1Timeframe'] == '9||5||1||9||Y'
    assert values['InpDirection'] == '0||1||1||2||Y'
    assert values['InpEntryStart'] == '540||540||5||600||Y'


def test_frozen_model_revalidates_copies_before_validation_report(proposal):
    spec = StrategySpec.model_validate(proposal)
    with pytest.raises(ValidationError):
        spec.name = 'changed'
    corrupted = spec.model_copy(update={'magic': 0})
    assert validate_strategy(corrupted).state == 'invalid'


def test_schema_artifact_matches_python_model():
    assert json.loads((ROOT/'strategy-v1.schema.json').read_text(encoding='utf-8')) == strategy_schema()
    assert strategy_schema()['additionalProperties'] is False


def test_domain_imports_do_not_require_flask_fastapi_or_mt5():
    script = "from geraset_domain.strategy import StrategySpec; from geraset_domain.uni_mapping import compile_strategy; import sys; print(','.join(m for m in ('flask','fastapi','psutil','MetaTrader5','mt5_bridge.presets') if m in sys.modules))"
    result = subprocess.run([sys.executable, '-c', script], cwd=ROOT.parent, text=True, capture_output=True, check=True)
    assert result.stdout.strip() == ''


def test_bridge_keeps_its_error_contract_after_shared_validation_extraction():
    with pytest.raises(BridgeError) as caught:
        bridge_parse(base64.b64encode(b'InpName=Too large').decode(), 1)
    assert caught.value.code == 'SET_TOO_LARGE'
    assert caught.value.status == 413


def test_ma_adx_pending_order_candle_stop_and_percentage_management(proposal):
    proposal['indicators'] = [
        {'type': 'ma', 'slot': 1, 'period': 20, 'method': 'ema', 'price': 'close', 'shift': -1},
        {'type': 'adx', 'slot': 2, 'purpose': 'exit', 'period': 14},
    ]
    proposal['entry_rules'][0].update(comparison='gt', right={'kind': 'price', 'source': 'close', 'candle': 1})
    proposal['exit_rules'][0]['left']['line'] = 'di_plus'
    proposal['risk']['stop_loss'] = {'type': 'candle', 'distance': '20', 'multiplier': '1.5', 'candle': 2, 'measure': 'body'}
    proposal['risk']['target_unit'] = 'percent'
    proposal['risk']['take_profit'] = {'type': 'fixed', 'distance': '1.5'}
    proposal['risk']['moving_stop'] = {'mode': 'percent', 'trigger': '1', 'distance': '0.5', 'adjustment_step': '0.1'}
    proposal['order'] = {'type': 'pending', 'reference': 'high', 'candle': 2, 'mirror_sell': True}
    proposal['optimization'] = [
        {'kind': 'choice', 'parameter': 'indicators.1.method', 'start': 'sma', 'end': 'ema'},
        {'kind': 'numeric', 'parameter': 'risk.moving_stop.distance', 'start': '0.25', 'step': '0.25', 'end': '1'},
        {'kind': 'choice', 'parameter': 'order.reference', 'start': 'high', 'end': 'close'},
    ]
    values = compile_strategy(StrategySpec.model_validate(proposal))
    assert values['InpIndicator1MaShift'] == '-1'
    assert values['InpIndicator1MaMethod'] == '1||0||1||1||Y'
    assert values['InpAdxExitPeriod'] == '14'
    assert values['InpSignal2'].split(',')[3] == '14'  # slot 2 DI+
    assert values['InpPendingMirrorSell'] == 'true'
    assert values['InpStopBody'] == '1'
    assert values['InpTargetUnit'] == '1'
    assert values['InpMovingStopDistance'] == '0.5||0.25||0.25||1||Y'


def test_model_runs_with_the_same_minimal_files_copied_by_docker(tmp_path, proposal):
    import shutil
    shutil.copytree(ROOT, tmp_path/'geraset_domain', ignore=shutil.ignore_patterns('tests', '__pycache__'))
    contract = tmp_path/'mt5_bridge/contracts'
    contract.mkdir(parents=True)
    shutil.copy2(ROOT.parent/'mt5_bridge/contracts/uni_inputs.json', contract/'uni_inputs.json')
    script = 'import sys,json;sys.path.insert(0,sys.argv[1]);from geraset_domain.strategy import validate_strategy;print(validate_strategy(json.loads(sys.stdin.read())).state)'
    result = subprocess.run([sys.executable, '-I', '-c', script, str(tmp_path)], input=json.dumps(proposal),
                            text=True, capture_output=True, check=True, cwd=tmp_path)
    assert result.stdout.strip() == 'structurally_valid'
