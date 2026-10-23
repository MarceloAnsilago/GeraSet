import base64
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from geraset_domain.services import (StrategyServiceError, compare_legacy_set, configure_from_set,
                                     configure_strategy, export_preserving_legacy, export_strategy)
from geraset_domain.uni_presets import parse_set


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def payload():
    return json.loads((ROOT/'geraset_domain/examples/rsi-v1.json').read_text(encoding='utf-8'))


def test_offline_export_is_deterministic_utf16_and_can_be_reimported(payload):
    report = configure_strategy(json.dumps(payload))
    assert report.valid
    first = export_strategy(report.strategy)
    assert first.contents == export_strategy(report.strategy).contents
    assert first.contents.startswith(b'\xff\xfe')
    decoded = first.contents[2:].decode('utf-16-le')
    assert '\r\n' in decoded and '\n' not in decoded.replace('\r\n', '')
    assert 'InpAutoStart=false' in decoded
    imported = configure_from_set(first.contents)
    assert imported.valid and imported.strategy == report.strategy
    assert imported.strategy.strategy_id == report.strategy.strategy_id
    assert imported.export_options == {'tester_auto_start': None}
    assert imported.as_dict()['financial_state'] == 'not_tested'


def test_structural_uni_and_financial_diagnostics_are_separate(payload):
    assert configure_strategy('{oops').errors[0].category == 'structural'
    assert configure_strategy(payload | {'schema_version':'99'}).errors[0].category == 'structural'
    incompatible = deepcopy(payload)
    incompatible['risk']['stop_loss']['distance'] = '0'
    assert configure_strategy(incompatible).errors[0].category == 'uni'
    allowed = deepcopy(incompatible)
    allowed['risk']['take_profit'] = {'type':'fixed','distance':'0'}
    report = configure_strategy(allowed)
    assert report.valid and not report.errors
    assert {'NO_STOP_LOSS','NO_TAKE_PROFIT','NOT_FINANCIALLY_VALIDATED'} <= {w.code for w in report.warnings}
    assert export_strategy(report.strategy).contents


def test_export_options_cannot_enable_live_trading(payload):
    artifact = export_strategy(payload, {'tester_auto_start':True})
    assert artifact.inputs['InpAutoStart'] == 'false'
    assert artifact.inputs['InpTesterAutoStart'] == 'true'
    for options in ({'auto_start':True}, {'tester_auto_start':'true'}, False, [], 0):
        with pytest.raises(StrategyServiceError):
            export_strategy(payload, options)


def test_v1_metadata_cannot_disagree_with_native_inputs(payload):
    artifact = export_strategy(payload)
    changed = artifact.contents.decode('utf-16').replace('InpLot=0.01', 'InpLot=0.02')
    report = configure_from_set(changed.encode('utf-16'))
    assert not report.valid and report.errors[0].code == 'PARAMETER_MISMATCH'
    truncated = artifact.contents.decode('utf-16').rsplit('; }', 1)[0]
    assert not configure_from_set(truncated.encode('utf-16')).valid


CASES = [
    {},
    *[{'gestao':{'order_mode':'Pendente','pending_reference':reference,'pending_bar':'3'},'mirrorSell':True}
      for reference in ('Máxima','Mínima','Abertura','Fechamento')],
    {'mirrorSell':True},  # hidden pending preference survives even in market mode
    {'gestao':{'order_mode':'Pendente','pending_reference':'Fechamento','pending_bar':'3',
               'pending-reference-start':'Máxima','pending-reference-end':'Fechamento',
               'pending-bar-start':'1','pending-bar-step':'2','pending-bar-end':'5'}},
    {'gestao':{'target_stop_mode':'Distância fixa','target_stop':'80','target_take_mode':'Distância fixa','target_take_distance':'250'}},
    {'gestao':{'target_stop_mode':'Distância fixa','target_stop':'0','target_take_mode':'Distância fixa','target_take_distance':'0'}},
    {'gestao':{'target_stop_mode':'Distância fixa','target_stop':'2','target_unit':'Porcentagem',
               'target_take_mode':'Distância fixa','target_take_distance':'4',
               'target-stop-start':'1','target-stop-step':'0.5','target-stop-end':'3',
               'target-take-distance-start':'2','target-take-distance-step':'1','target-take-distance-end':'5'}},
    {'gestao':{'target_candle':'Antepenúltimo','target_size':'Corpo','target_stop_multiplier':'1.5',
               'target-candle-start':'último','target-candle-end':'Antepenúltimo',
               'target-size-start':'Total com pavios','target-size-end':'Corpo',
               'target-take-multiplier-start':'1','target-take-multiplier-step':'0.5','target-take-multiplier-end':'3'}},
    {'gestao':{'breakeven-mode':'Pontos','breakeven-trigger':'100','breakeven-offset':'20',
               'breakeven-activate-start':'80','breakeven-activate-step':'10','breakeven-activate-end':'120',
               'breakeven-distance-start':'10','breakeven-distance-step':'10','breakeven-distance-end':'40',
               'trailing-mode':'Pontos','trailing-trigger':'120','trailing-distance':'60','trailing-step':'10',
               'moving-stop-mode':'Pontos','moving-stop-trigger':'150','moving-stop-distance':'70','moving-stop-step':'15'}},
    {'gestao':{'breakeven-mode':'Porcentagem','breakeven-trigger':'1','breakeven-offset':'0.1',
               'trailing-mode':'Porcentagem','trailing-trigger':'1.5','trailing-distance':'0.5','trailing-step':'0.1',
               'trailing-distance-start':'0.25','trailing-distance-step':'0.25','trailing-distance-end':'1',
               'moving-stop-mode':'Porcentagem','moving-stop-trigger':'2','moving-stop-distance':'0.7','moving-stop-step':'0.2'}},
    {'inicio':{'setup_market':'B3','setup_mode':'Swing trade','setup_direction':'Somente venda','setup_lot':'1',
               'operation-direction-start':'Somente compra','operation-direction-end':'Somente venda'},
     'display':{'show_signal_histograms':False,'show_mt5_panel':False},'state':{'testerAutoStart':True}},
    {'inicio':{'setup_entry_start':'22:00','setup_entry_end':'02:00',
               'schedule-entry-start-start':'23:55','schedule-entry-start-end':'22:00',
               'schedule-entry-end-start':'02:00','schedule-entry-end-end':'03:00'}},
    {'indicators':[{'timeframe':'M15','params':{'Shift':-2,'Período':7},'ranges':{'Período':[5,2,11],'Shift':[-3,1,3]},
                    'combos':{'Método':'LWMA','Preço aplicado':'Weighted'},'comboRanges':{'Método':['SMA','LWMA'],'Preço aplicado':['Close','Weighted']}},
                   {'params':{'Sobrevenda':25,'Nível médio':50,'Sobrecompra':75},'ranges':{'Sobrecompra':[70,'2.5',80]}},
                   {'params':{'Período':20},'ranges':{'Período':[10,10,30]}},
                   {'type':'Não usar','purpose':'Saída','timeframe':'H4'}]},
    {'indicators':[{}, {'params':{'Sobrevenda':'0.0000000000001','Sobrecompra':'75.1234567890123'}}, {}, {}]},
    {'state':{'testerAutoStart':False}},
    {'signalUnit':'Pontos', 'rules':{
        0:{'operator':'Se','usage':'Entrada','normalSide':'Compra','sense':'Normal','target':'Indicador 1: Média Móvel',
           'targetCandle':'Penúltima','comparison':'Cruzar&fechar acima de','reference':'Abertura do dia','referenceCandle':'Anterior','fixed':'0','distance':'10'},
        2:{'operator':'E','usage':'Entrada','normalSide':'Compra','sense':'Normal','target':'Indicador 3: ADX +DI',
           'targetCandle':'Anterior','comparison':'Maior que','reference':'Valor fixo','referenceCandle':'N.usar','fixed':'25','distance':'0'},
        5:{'operator':'Se','usage':'Saída','normalSide':'Compra','sense':'Inverter','target':'Indicador 2: RSI',
           'targetCandle':'Anterior','comparison':'Maior que','reference':'Valor fixo','referenceCandle':'N.usar','fixed':'70','distance':'0'},
    }},
    {'signalUnit':'Porcentagem','rules':{
        0:{'operator':'Se','usage':'Entrada','normalSide':'Compra','sense':'Normal','target':'Indicador 1: Média Móvel',
           'targetCandle':'Anterior','comparison':'Maior que','reference':'Fechamento da vela','referenceCandle':'Anterior','fixed':'0','distance':'1'},
        5:{'operator':'Se','usage':'Saída','normalSide':'Venda','sense':'Normal','target':'Indicador 2: RSI Nível superior',
           'targetCandle':'N.usar','comparison':'Maior ou igual que','reference':'Indicador 2: RSI','referenceCandle':'Anterior','fixed':'0','distance':'0'},
    }},
]


@pytest.fixture(scope='module')
def legacy_exports():
    if not shutil.which('node'):
        pytest.fail('Node é necessário para conferir equivalência com o exportador atual.')
    result = subprocess.run(['node','flask_version/tests/helpers/legacy-export-fixture.cjs'], cwd=ROOT,
                            input=json.dumps(CASES), text=True, capture_output=True, check=True)
    return [base64.b64decode(item['set_base64']) for item in json.loads(result.stdout)]


@pytest.mark.parametrize('index', range(len(CASES)))
def test_real_legacy_exporter_and_python_match_all_supported_inputs(index, legacy_exports):
    original = legacy_exports[index]
    comparison, artifact = compare_legacy_set(original)
    assert comparison['equivalent'], comparison['differences']
    assert artifact.contents != original  # independent serializer, metadata/layout differ
    assert artifact.contents.startswith(b'\xff\xfe')
    strategy = comparison['configuration']['strategy']
    preserved = export_preserving_legacy(strategy, original, comparison['export_options'])
    assert preserved.contents == original  # v2 comments, inactive fields and exact bytes retained
    assert preserved.sha256 == comparison['original_sha256']
    imported = configure_from_set(original)
    assert imported.valid
    assert imported.strategy.entry_rules[0].slot == 1
    assert imported.strategy.exit_rules[0].slot == 6
    assert imported.export_options == ({'tester_auto_start':True} if index == 13 else {'tester_auto_start':False} if index == 17 else {})


def test_comparison_is_not_blind_to_mutations_and_never_drops_unmodeled_values(legacy_exports, monkeypatch):
    import geraset_domain.services as services
    export = services.export_strategy
    def corrupted(*args, **kwargs):
        artifact = export(*args, **kwargs)
        return replace(artifact, inputs=artifact.inputs | {'InpLot':'999'})
    monkeypatch.setattr(services, 'export_strategy', corrupted)
    comparison, _ = services.compare_legacy_set(legacy_exports[0])
    assert not comparison['equivalent']
    assert comparison['differences'][0]['input'] == 'InpLot'
    monkeypatch.setattr(services, 'export_strategy', export)
    text = legacy_exports[0].decode('utf-16').replace('InpName=', 'InpCandleFilter=1\r\nInpName=', 1)
    original = b'\xff\xfe'+text.encode('utf-16-le')
    comparison, _ = compare_legacy_set(original)
    assert not comparison['equivalent']
    assert not configure_from_set(original).valid
    with pytest.raises(StrategyServiceError):
        export_preserving_legacy(comparison['configuration']['strategy'], original)


def test_pre_trailing_presets_keep_their_effective_disabled_behavior(legacy_exports):
    lines = legacy_exports[0].decode('utf-16').splitlines(keepends=True)
    original = b'\xff\xfe'+''.join(line for line in lines if not line.startswith(('InpTrailing','InpMovingStop'))).encode('utf-16-le')
    comparison, _ = compare_legacy_set(original)
    assert comparison['equivalent']
    assert export_preserving_legacy(comparison['configuration']['strategy'], original).contents == original
