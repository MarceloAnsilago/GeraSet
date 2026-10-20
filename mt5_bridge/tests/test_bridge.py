import base64
import json
from pathlib import Path
import threading
import time
import pytest
from fastapi.testclient import TestClient
from mt5_bridge.api import create_app
from mt5_bridge.errors import BridgeError
from mt5_bridge.ini import build_ini
from mt5_bridge.models import JobRequest
from mt5_bridge.presets import parse_set, execution_set
from mt5_bridge.reports import read_report, read_optimization
from mt5_bridge.runner import MT5Runner, file_lock
from mt5_bridge.store import Store


HTML='<html><table><tr><td>Total Net Profit:</td><td>1 234.56</td><td>Total Trades:</td><td>10</td></tr><tr><td>Profit Trades (% of total):</td><td>6 (60.00%)</td></tr></table></html>'
XML='<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet><Table><Row><Cell><Data>Pass</Data></Cell><Cell><Data>Profit</Data></Cell></Row><Row><Cell><Data>1</Data></Cell><Cell><Data>12.3400</Data></Cell></Row></Table></Worksheet></Workbook>'


class FakeMT5:
    """Simulation explicitly injected only into tests, never selected by production API."""
    def __init__(self,settings,mode='ok'):self.settings,self.mode=settings,mode;self.entered=threading.Event()
    def status(self):return {'ready':True,'busy':False,'errors':[],'live_trading':False}
    def ensure_ready(self):pass
    def execute(self,job,values,callback,cancelled):
        callback('running');self.entered.set()
        if self.mode=='wait':
            while not cancelled():time.sleep(.01)
            raise BridgeError('CANCELLED','Cancelado no simulador.')
        if self.mode=='missing':raise BridgeError('REPORT_MISSING','Sem relatório.')
        if self.mode=='crash':raise RuntimeError('secret must not leak')
        callback('collecting_results')
        path=self.settings.work_dir/job['id']/('report.xml' if job['kind']=='optimize' else 'report.htm')
        path.write_text(XML if job['kind']=='optimize' else HTML,encoding='utf-8')
        return read_report(path),[path.name]


def wait(client,job_id,headers,state='completed'):
    end=time.monotonic()+3
    while time.monotonic()<end:
        job=client.get('/api/v1/jobs/'+job_id,headers=headers).json()['data']
        if job['state']==state:return job
        time.sleep(.02)
    raise AssertionError(job)


@pytest.fixture
def headers(settings):return {'Authorization':'Bearer '+settings.token}


def test_auth_and_validation(settings,payload,headers):
    with TestClient(create_app(settings,FakeMT5(settings),start_worker=False)) as client:
        assert client.get('/api/v1/health').status_code==401
        assert client.get('/api/v1/health',headers={'Authorization':'Bearer bad'}).status_code==401
        assert client.get('/api/v1/health',headers=headers).status_code==200
        for changes in [dict(terminal='cmd.exe'),dict(symbol='EURUSD\n[Experts]'),dict(date_to='2026-09-01'),dict(forward_mode=4),dict(tick_model=99),dict(set_name='../x.set')]:
            response=client.post('/api/v1/jobs/backtest',json=payload|changes,headers=headers)
            assert response.status_code==422,response.text
        assert client.post('/api/v1/jobs/backtest',json=payload|{'symbol':'WIN$'},headers=headers).status_code==400
        assert client.get('/api/v1/jobs/not-a-uuid',headers=headers).status_code==422
        assert client.get('/api/v1/jobs/00000000-0000-0000-0000-000000000000',headers=headers).status_code==404


def test_full_api_backtest_and_artifacts(settings,payload,headers):
    app=create_app(settings,FakeMT5(settings))
    with TestClient(app) as client:
        started=time.monotonic();response=client.post('/api/v1/jobs/backtest',json=payload,headers=headers)
        assert response.status_code==202 and time.monotonic()-started<1
        job_id=response.json()['data']['id'];job=wait(client,job_id,headers)
        assert job['set_hash'] and job['started_at'] and job['finished_at']
        result=client.get(f'/api/v1/jobs/{job_id}/results',headers=headers).json()['data']
        assert result['metrics']['net_profit']['value']=='1234.56'
        assert result['win_rate_percent']=='60.00'
        progress=client.get(f'/api/v1/jobs/{job_id}/progress',headers=headers).json()['data']
        assert progress['percent'] is None and progress['stage']=='completed'
        artifacts=client.get(f'/api/v1/jobs/{job_id}/artifacts',headers=headers).json()['data']
        assert 'report.htm' in {a['id'] for a in artifacts}
        download=client.get(f'/api/v1/jobs/{job_id}/artifacts/report.htm',headers=headers)
        assert download.status_code==200 and 'attachment' in download.headers['content-disposition']
        assert client.get(f'/api/v1/jobs/{job_id}/artifacts/not-found',headers=headers).status_code==404
        assert client.get('/api/v1/jobs',headers=headers).json()['data'][0]['id']==job_id
        assert client.post(f'/api/v1/jobs/{job_id}/cancel',headers=headers).status_code==409
    assert Store(settings.work_dir/'jobs.sqlite3').get(job_id)['state']=='completed'


def test_optimization_ranges_and_real_result_shape(settings,payload,preset,headers):
    body=payload|{'set_base64':base64.b64encode(preset.replace('0.03||N','0.03||Y').encode()).decode()}
    with TestClient(create_app(settings,FakeMT5(settings))) as client:
        assert client.post('/api/v1/jobs/optimize',json=payload,headers=headers).status_code==400
        response=client.post('/api/v1/jobs/optimize',json=body,headers=headers)
        assert response.status_code==202
        job=wait(client,response.json()['data']['id'],headers)
        assert job['progress']['total_passes']==3
        assert job['results']['worksheets'][0]['passes'][0]['Profit']=='12.3400'


@pytest.mark.parametrize('mode,code',[('missing','REPORT_MISSING'),('crash','INTERNAL_ERROR')])
def test_failures_are_not_completed(settings,payload,headers,mode,code):
    with TestClient(create_app(settings,FakeMT5(settings,mode))) as client:
        response=client.post('/api/v1/jobs/backtest',json=payload,headers=headers)
        job=wait(client,response.json()['data']['id'],headers,'failed')
        assert job['error']['code']==code and 'secret' not in json.dumps(job)
        assert client.get(f'/api/v1/jobs/{job["id"]}/results',headers=headers).status_code==409


def test_running_and_queued_cancellation(settings,payload,headers):
    fake=FakeMT5(settings,'wait')
    with TestClient(create_app(settings,fake)) as client:
        first=client.post('/api/v1/jobs/backtest',json=payload,headers=headers).json()['data']['id']
        assert fake.entered.wait(1)
        second=client.post('/api/v1/jobs/backtest',json=payload,headers=headers).json()['data']['id']
        assert client.post(f'/api/v1/jobs/{second}/cancel',headers=headers).json()['data']['state']=='cancelled'
        assert client.post(f'/api/v1/jobs/{first}/cancel',headers=headers).status_code==200
        wait(client,first,headers,'cancelled')


def test_queue_limits_and_restart(settings,payload,headers):
    from dataclasses import replace
    settings=replace(settings,max_queue=1)
    app=create_app(settings,FakeMT5(settings),start_worker=False)
    with TestClient(app) as client:
        job=client.post('/api/v1/jobs/backtest',json=payload,headers=headers).json()['data']
        assert client.post('/api/v1/jobs/backtest',json=payload,headers=headers).status_code==429
    store=app.state.manager.store
    store.update(job['id'],state='running',owner={'pid':999999,'created':1})
    store.reconcile();recovered=store.get(job['id'])
    assert recovered['state']=='failed' and recovered['error']['code']=='BRIDGE_RESTARTED'


def test_ini_is_tester_only(settings,payload):
    request=JobRequest(**payload)
    text=build_ini(settings,request,'backtest','uuid.set','geraset_reports/uuid/report.htm')
    assert 'AllowLiveTrading=0' in text and 'UseCloud=0' in text and 'UseRemote=0' in text
    assert '[StartUp]\nExpert=\nScript=' in text
    assert 'Expert=Uni\\UniEA.ex5' in text and 'Optimization=0' in text
    assert 'Password=' not in text and 'ShutdownTerminal=1' in text
    assert 'Optimization=2' in build_ini(settings,request.model_copy(update={'optimization':2}),'optimize','uuid.set','x.xml')


@pytest.mark.parametrize('replacement',['InpBad=1','InpLot=NaN','InpLot=1e99999','InpLot=1||2||0||5||Y','InpSignal1=abc'])
def test_bad_sets(preset,replacement):
    source=preset+'\n'+replacement if replacement.startswith('InpBad') else '\n'.join(replacement if line.startswith(replacement.split('=')[0]+'=') else line for line in preset.splitlines())
    with pytest.raises(BridgeError):parse_set(base64.b64encode(source.encode()).decode(),1048576)


def test_receipt_encoding_and_overrides(preset):
    raw=b'\xff\xfe'+preset.encode('utf-16-le')
    original,values,ranges,digest=parse_set(base64.b64encode(raw).decode(),1048576)
    assert original==raw and len(digest)==64
    execution=execution_set(values,True).decode('utf-16')
    assert 'InpAutoStart=false' in execution and 'InpTesterAutoStart=true' in execution
    with pytest.raises(BridgeError):parse_set(base64.b64encode(raw).decode(),2)


def test_static_visual_inputs_from_geraset(preset):
    text=preset+'InpExibirPainel=true\nInpExibirHistogramas=false\nInpHistogramasBarras=300\n'
    _,values,_,_=parse_set(base64.b64encode(text.encode()).decode(),1048576)
    assert values['InpHistogramasBarras']=='300'
    invalid=text.replace('InpHistogramasBarras=300','InpHistogramasBarras=300||100||100||300||Y')
    with pytest.raises(BridgeError,match='estático'):parse_set(base64.b64encode(invalid.encode()).decode(),1048576)


def test_report_errors_and_locale(tmp_path):
    path=tmp_path/'x.htm';path.write_text(HTML.replace('1 234.56','1.234,56'))
    assert read_report(path)['metrics']['net_profit']['value']=='1234.56'
    path.write_text('<html>incomplete')
    with pytest.raises(BridgeError):read_report(path)
    with pytest.raises(BridgeError):read_optimization('<!DOCTYPE x><Workbook/>')
    with pytest.raises(BridgeError):read_optimization('<Workbook>')
    with pytest.raises(BridgeError):read_optimization(XML.replace('<Cell><Data>1','<Cell xmlns:ss="urn:test" ss:Index="9999999"><Data>1'))


def test_installation_busy_does_not_kill_or_start(settings,monkeypatch):
    class Process:info={'exe':str(settings.terminal)}
    monkeypatch.setattr('mt5_bridge.runner.psutil.process_iter',lambda *args:[Process()])
    runner=MT5Runner(settings)
    assert runner.status()['busy']
    with pytest.raises(BridgeError,match='Terminal já aberto'):runner.ensure_ready()


def test_lock_and_ownership_guard(settings,monkeypatch):
    with file_lock(settings.work_dir/'test.lock'):
        with pytest.raises(BridgeError):
            with file_lock(settings.work_dir/'test.lock'):pass
    terminated=[]
    class Process:
        def create_time(self):return 2
        def exe(self):return str(settings.terminal)
        def terminate(self):terminated.append(True)
    monkeypatch.setattr('mt5_bridge.runner.psutil.Process',lambda pid:Process())
    runner=MT5Runner(settings);runner.stop_owned({'pid':10,'created':1,'exe':str(settings.terminal)})
    assert not terminated
    runner.stop_owned({'pid':10,'created':2,'exe':str(settings.terminal)})
    assert terminated


def test_real_account_failure_journal(tmp_path):
    from mt5_bridge.monitor import LogMonitor
    logs=tmp_path/'logs';logs.mkdir()
    monitor=LogMonitor(tmp_path)
    (logs/'20261020.log').write_text('Tester\ttester not started because the account is not specified\n',encoding='utf-16-le')
    monitor.poll()
    assert monitor.error['code']=='ACCOUNT_REQUIRED'


def test_optimization_metrics_preserve_unavailable():
    from mt5_bridge.reports import pass_metrics
    metrics=pass_metrics({'Profit':'123.45','Trades':'9','Profit Factor':'1.2'})
    assert metrics['net_profit']['value']=='123.45'
    assert metrics['total_trades']['value']=='9'
    assert metrics['gross_loss'] is None


def test_owned_terminal_accepts_queue_but_external_does_not(settings,monkeypatch):
    class Process:
        info={'exe':str(settings.terminal)}
        def create_time(self):return 42
        def exe(self):return str(settings.terminal)
    monkeypatch.setattr('mt5_bridge.runner.psutil.process_iter',lambda *args:[Process()])
    monkeypatch.setattr('mt5_bridge.runner.psutil.Process',lambda pid:Process())
    runner=MT5Runner(settings)
    runner.ensure_queueable({'pid':123,'created':42,'exe':str(settings.terminal)})
    with pytest.raises(BridgeError):runner.ensure_queueable(None)
    with pytest.raises(BridgeError):runner.ensure_queueable({'pid':123,'created':41,'exe':str(settings.terminal)})
