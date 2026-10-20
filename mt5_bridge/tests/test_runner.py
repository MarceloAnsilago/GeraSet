import configparser
from dataclasses import replace
from pathlib import Path
import pytest
from mt5_bridge.manager import Manager
from mt5_bridge.models import JobRequest
from mt5_bridge.runner import MT5Runner
from test_bridge import HTML


@pytest.mark.parametrize('mode,expected',[('ok','completed'),('missing','failed'),('incomplete','failed'),('timeout','failed'),('start_error','failed')])
def test_real_executor_with_fake_os_process(settings,payload,monkeypatch,mode,expected):
    settings=replace(settings,timeout_seconds=.02)
    monkeypatch.setattr('mt5_bridge.runner.psutil.process_iter',lambda *args:[])
    handles=[]
    class ProcessInfo:
        def create_time(self):return 123.0
        def exe(self):return str(settings.terminal)
        def terminate(self):handles[0].returncode=-15
    monkeypatch.setattr('mt5_bridge.runner.psutil.Process',lambda pid:ProcessInfo())
    class FakeProcess:
        pid=123
        def __init__(self,command,**kwargs):
            if mode=='start_error':raise OSError('simulated process start error')
            handles.append(self);self.returncode=None if mode=='timeout' else 0
            assert isinstance(command,list) and 'shell' not in kwargs
            ini=Path(next(arg.split(':',1)[1] for arg in command if arg.startswith('/config:')))
            config=configparser.ConfigParser();config.read(ini,encoding='utf-16')
            assert config['Experts']['AllowLiveTrading']=='0' and config['Experts']['AllowDllImport']=='0'
            assert config['StartUp']['Expert']=='' and config['Tester']['UseCloud']=='0'
            receipt=settings.data_dir/'MQL5/Profiles/Tester'/config['Tester']['ExpertParameters']
            assert receipt.exists() and 'InpTesterAutoStart=true' in receipt.read_text(encoding='utf-16')
            if mode in ('ok','incomplete'):
                target=settings.terminal.parent/Path(config['Tester']['Report'].replace('\\','/'))
                target.write_text(HTML if mode=='ok' else '<html>',encoding='utf-8')
        def poll(self):return self.returncode
        def wait(self,timeout=None):return self.returncode
    monkeypatch.setattr('mt5_bridge.runner.subprocess.Popen',FakeProcess)
    runner=MT5Runner(settings);manager=Manager(settings,runner)
    job=manager.submit('backtest',JobRequest(**payload));manager.store.update(job['id'],state='preparing')
    manager.run_job(manager.store.get(job['id']))
    result=manager.store.get(job['id']);assert result['state']==expected
    if mode!='ok':
        assert result['error']['code']=={'missing':'REPORT_MISSING','incomplete':'INCOMPLETE_REPORT','timeout':'TIMEOUT','start_error':'START_FAILED'}[mode]
    assert not list((settings.data_dir/'MQL5/Profiles/Tester').glob('geraset_*.set'))
    if mode=='timeout':assert handles[0].returncode==-15
