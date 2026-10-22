import base64
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from mt5_bridge.errors import BridgeError
from mt5_bridge.presets import parse_set


def parse(lines):
    text = 'InpName=Teste\nInpMagic=1\nInpLot=0.01\nInpSignal1=1,0,1,0,1,0,1,1,0,0,0\n'+lines
    return parse_set(base64.b64encode(text.encode()).decode(), 100000)


@pytest.mark.parametrize('prefix', ['InpTrailing', 'InpMovingStop'])
def test_standard_management_requires_positive_parameters_when_enabled(prefix):
    fixed = {prefix+'Mode': '1', prefix+'Trigger': '100', prefix+'Distance': '30', prefix+'Step': '5'}
    assert parse('\n'.join(f'{k}={v}' for k, v in fixed.items()))
    for suffix in ('Trigger', 'Distance', 'Step'):
        for value in ('0', '0||0||1||10||Y'):
            invalid = fixed | {prefix+suffix: value}
            with pytest.raises(BridgeError):
                parse('\n'.join(f'{k}={v}' for k, v in invalid.items()))
        # A valid current value cannot hide a zero in an active optimization.
        invalid = fixed | {prefix+suffix: '5||0||1||10||Y'}
        with pytest.raises(BridgeError):
            parse('\n'.join(f'{k}={v}' for k, v in invalid.items()))


@pytest.mark.parametrize('prefix', ['InpTrailing', 'InpMovingStop'])
def test_mode_optimization_cannot_enable_zero_defaults(prefix):
    with pytest.raises(BridgeError):
        parse(f'{prefix}Mode=0||0||1||2||Y')
    assert parse(f'{prefix}Mode=0')
    assert parse(f'{prefix}Mode=2\n{prefix}Trigger=0.5\n{prefix}Distance=1\n{prefix}Step=0.01')


def test_browser_exports_are_accepted_and_preserved_by_bridge():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node necessário para o teste integrado do exportador JavaScript.')
    root = Path(__file__).resolve().parents[2]
    script = r"""
const fs=require('node:fs'),vm=require('node:vm');
const c=vm.createContext({document:{addEventListener(){}}});
vm.runInContext(fs.readFileSync('flask_version/static/export.js','utf8'),c);
const values={};
for(const key of ['trailing','moving-stop']){
 values[key+'-mode']='Porcentagem';values[key+'-trigger']='1,5';values[key+'-distance']='0,75';values[key+'-step']='0,10';
 for(const field of ['activate','distance','step'])for(const bound of ['start','step','end'])values[key+'-'+field+'-'+bound]='0';
}
values['trailing-distance-start']='0.25';values['trailing-distance-step']='0.25';values['trailing-distance-end']='1';
process.stdout.write(JSON.stringify(Array.from(c.managedStopSetLines(Object.entries(values).map(([key,value])=>({key,value}))))));
"""
    result = subprocess.run([node, '-e', script], cwd=root, text=True, capture_output=True, check=True)
    lines = json.loads(result.stdout)
    _, actual, ranges, _ = parse('\n'.join(lines))
    assert actual['InpTrailingMode'].startswith('2||')
    assert actual['InpMovingStopDistance'].startswith('0.75||')
    assert ranges == {'InpTrailingDistance': 4}
    for line in lines:
        key, value = line.split('=', 1)
        assert actual[key] == value
