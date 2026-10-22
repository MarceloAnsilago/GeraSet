import base64
import json
from pathlib import Path

import pytest

from mt5_bridge.errors import BridgeError
from mt5_bridge.presets import parse_set


CASES = json.loads((Path(__file__).parent/'fixtures/uni_relations.json').read_text(encoding='utf-8'))


def parse(inputs):
    values = {'InpName': 'Teste', 'InpMagic': '1', 'InpLot': '0.01',
              'InpSignal1': '1,0,1,0,1,0,1,1,0,0,0'} | inputs
    text = '\n'.join(f'{key}={value}' for key, value in values.items())
    return parse_set(base64.b64encode(text.encode()).decode(), 100000)


@pytest.mark.parametrize('example', CASES, ids=[case['name'] for case in CASES])
def test_same_relational_cases_as_browser(example):
    if example['valid']:
        assert parse(example['inputs'])
    else:
        with pytest.raises(BridgeError):
            parse(example['inputs'])


@pytest.mark.parametrize('signal', [
    '1,0,1,9,0,0,0,1,10,0,0',  # constant on A
    '1,0,1,34,1,0,0,1,0,0,0',  # unknown buffer
    '1,0,1,10,1,0,0,1,0,0,0',  # missing indicator
    '1,0,1,0,4,0,1,1,0,0,0',
    '1,0,1,0,0,9,1,1,0,0,0',  # closed crossing on current candle
    '1,0,1,0,1,0,9,0,0,1,2',  # percent against zero
    '1,0,1,0,1,0,1,1,0,1,0',  # no unit with distance
    '1.5,0,1,0,1,0,1,1,0,0,0',
    '1,0,0,0,1,0,1,1,0,0,0',
    '2,0,1,0,1,0,1,1,0,0,0',  # group must start with Se
])
def test_signal_semantics_are_checked_before_launch(signal):
    with pytest.raises(BridgeError):
        parse({'InpSignal1': signal})


def test_signal_indicator_buffers_scales_purposes_and_logic_groups():
    signal = '1,0,1,10,1,0,9,0,25,0,0'
    assert parse({'InpIndicator1Type': '2', 'InpSignal1': signal})
    for changes in [
        {'InpIndicator1Exit': '1'},
        {'InpSignal1': '1,0,1,10,1,0,0,1,0,0,0'},  # oscillator against price
        {'InpSignal1': '1,0,1,10,1,0,9,0,25,1,1'},  # oscillator points
        {'InpSignal2': signal},  # repeated Se in same group
        {'InpIndicator2Type': '2'},  # repeated ADX entry
        {'InpIndicator1Type': '2||0||1||2||Y'},  # optimization changes buffer scale/points independently
    ]:
        candidate = {'InpIndicator1Type': '2', 'InpSignal1': signal} | changes
        # A plain buffer 0 against a fixed value may change indicator type safely.
        if 'InpIndicator1Type' in changes:
            candidate['InpSignal1'] = '1,0,1,11,1,0,9,0,25,0,0'
        with pytest.raises(BridgeError):
            parse(candidate)
    assert parse({'InpIndicator1Type': '2', 'InpSignal1': signal,
                  'InpSignal2': signal.replace('1,0,1,', '2,0,1,', 1)})
