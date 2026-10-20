import base64
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from mt5_bridge.settings import Settings


@pytest.fixture
def settings(tmp_path):
    terminal=tmp_path/'terminal/terminal64.exe';terminal.parent.mkdir();terminal.write_bytes(b'MZ'+b'0'*100)
    expert=terminal.parent/'MQL5/Experts/Uni/UniEA.ex5';expert.parent.mkdir(parents=True);expert.write_bytes(b'x'*100)
    return Settings(token='test-service-token-not-a-real-secret-1234',terminal=terminal,data_dir=terminal.parent,
                    expert=expert,work_dir=tmp_path/'jobs',poll_seconds=.1,timeout_seconds=2)


@pytest.fixture
def preset():
    return 'InpName=Teste\nInpMagic=123\nInpLot=0.01||0.01||0.01||0.03||N\nInpSignal1=1,0,1,0,1,0,1,1,0,0,0\n'


@pytest.fixture
def payload(preset):
    return dict(setup_id='Teste',set_name='Teste.set',set_base64=base64.b64encode(preset.encode()).decode(),
                symbol='EURUSD',date_from='2026-10-01',date_to='2026-10-02')
