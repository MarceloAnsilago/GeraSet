import base64
import json

import pytest

from mt5_bridge.contracts.sync_uni_inputs import build_contract
from mt5_bridge.errors import BridgeError
from mt5_bridge.presets import CONTRACT, parse_set, validate_value


def parse(extra):
    text = 'InpName=Teste\nInpMagic=1\nInpLot=0.01\nInpSignal1=1,0,1,0,1,0,1,1,0,0,0\n'
    replaced = {line.split('=', 1)[0] for line in extra.splitlines()}
    text = '\n'.join(line for line in text.splitlines() if line.split('=', 1)[0] not in replaced)
    return parse_set(base64.b64encode((text+'\n'+extra).encode()).decode(), 100000)


@pytest.mark.parametrize('line', [
    'InpMagic=0', 'InpMagic=2147483648', 'InpLot=0', 'InpLot=-1',
    'InpMarket=2', 'InpTradeMode=-1', 'InpDirection=3', 'InpOrderMode=2',
    'InpPendingReference=4', 'InpPendingCandle=0', 'InpStopCandle=4',
    'InpIndicator1Timeframe=16385', 'InpIndicator1Timeframe=22',
    'InpIndicator1Type=3', 'InpIndicator1Exit=2', 'InpIndicator1MaPrice=0',
    'InpIndicator1MaMethod=4', 'InpIndicator1MaShift=-100001',
    'InpRsiEntryPeriod=100001', 'InpRsiExitLower=-0.1', 'InpRsiEntryUpper=100.1',
    'InpEntryStart=1436', 'InpEntryStart=3', 'InpStopLoss=-1',
    'InpStopLoss=100000001', 'InpTrailingTrigger=-1',
    'InpCurveSession=forged', 'InpName='+'x'*49,
    'InpHistogramasBarras=0', 'InpHistogramasBarras=5001',
    'InpMarkerFontSize=2147483648',
    'InpMarket=0||0||1||2||Y', 'InpLot=0.01||0||0.01||0.02||Y',
    'InpEntryStart=0||0||1||10||Y', 'InpStopBody=true||0||1||2||Y',
    'InpExibirPainel=true||0||1||1||Y',
])
def test_rejects_out_of_contract_scalar_values_and_active_bounds(line):
    with pytest.raises(BridgeError, match='.'):
        parse(line)


@pytest.mark.parametrize('line', [
    'InpTakeMode=-1', 'InpIndicator1Type=-1', 'InpIndicator1Timeframe=21',
    'InpIndicator1MaShift=-100000', 'InpMagic=2147483647',
    'InpEntryEnd=1435', 'InpRsiEntryLower=0', 'InpRsiEntryUpper=100',
    'InpStopBody=true||0||1||1||Y', 'InpStopBody=1||0||1||1||Y',
    'InpEntryStart=0||0||5||1430||Y',
    # Disabled optimization columns are not active values (native preset compatibility).
    'InpMagic=1||0||0||0||N',
])
def test_preserves_valid_boundaries_legacy_take_and_boolean_presets(line):
    assert parse(line)[1]


def test_all_declared_numeric_defaults_satisfy_contract():
    for key, spec in CONTRACT.items():
        if spec['kind'] in ('string', 'bool'):
            continue
        validate_value(spec['default'], key)
    assert CONTRACT['InpCurveSession']['internal'] is True
    assert CONTRACT['InpIndicator1Timeframe']['enum_values']['UNI_SLOT_H1'] == 12
    assert CONTRACT['InpRsiEntryPrice']['default'] == 1


def test_extraction_tracks_mql_names_implicit_enums_defaults_and_static_inputs(tmp_path):
    config = tmp_path/'Include/Configuration'
    config.mkdir(parents=True)
    (config/'UniTypes.mqh').write_text('enum Market { FOREX=0, B3 };', encoding='utf-8')
    (config/'UniInputOptions.mqh').write_text('', encoding='utf-8')
    ea = tmp_path/'UniEA.mq5'
    ea.write_text('input Market InpMarket=B3;\nsinput bool InpExibirPainel=true;\n', encoding='utf-8')
    first = build_contract(tmp_path)
    assert first['InpMarket']['default'] == 1
    assert first['InpMarket']['enum_values'] == {'FOREX': 0, 'B3': 1}
    assert first['InpExibirPainel']['optimizable'] is False
    ea.write_text('input Market InpMarket=FOREX;\n', encoding='utf-8')
    assert build_contract(tmp_path) != first


def test_contract_is_utf8_and_contains_only_supported_types():
    assert all(s['kind'] in {'string', 'bool', 'enum', 'int', 'long', 'double', 'color'}
               for s in CONTRACT.values())
    assert json.loads(json.dumps(CONTRACT, ensure_ascii=False)) == CONTRACT
