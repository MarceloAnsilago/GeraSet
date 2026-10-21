from mt5_bridge.monitor import LogMonitor, reported_percent
from mt5_bridge.api import create_app
from fastapi.testclient import TestClient
from test_bridge import FakeMT5


def test_mt5_percentage_rejects_unrelated_and_out_of_range_messages():
    assert reported_percent(['balance 10000','Core 1: 99 %']) is None
    assert reported_percent(['AutoTesting processing 101 %']) is None
    assert reported_percent(['AutoTesting processing 0 %']) == 0
    assert reported_percent(['AutoTesting processing 2 %','AutoTesting processing 14,5 %']) == 14.5


def test_monitor_retains_latest_observed_percentage(tmp_path):
    logs=tmp_path/'logs';logs.mkdir();path=logs/'today.log';path.write_bytes(b'')
    monitor=LogMonitor(tmp_path)
    with path.open('ab') as f:f.write('CD 0 AutoTesting processing 14 %\r\n'.encode('utf-16-le'))
    monitor.poll();assert monitor.percent==14
    with path.open('ab') as f:f.write('CD 0 AutoTesting processing 5 %\r\n'.encode('utf-16-le'))
    monitor.poll();assert monitor.percent==14
    monitor.poll();assert monitor.percent==14


def test_historical_failed_task_exposes_logged_percentage(settings,payload):
    from mt5_bridge.models import JobRequest
    app=create_app(settings,FakeMT5(settings),start_worker=False)
    manager=app.state.manager;job=manager.submit('backtest',JobRequest(**payload))
    manager.store.update(job['id'],state='failed',messages=['AutoTesting processing 14 %'])
    with TestClient(app) as client:
        progress=client.get(f"/api/v1/jobs/{job['id']}/progress",headers={'Authorization':'Bearer '+settings.token}).json()['data']
    assert progress['state']=='failed' and progress['percent']==14
    assert progress['source']=='mt5_journal'
