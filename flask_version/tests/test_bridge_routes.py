from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import app
from bridge_client import BridgeUnavailable, HTTPBridgeClient


class Transport:
    def __init__(self):self.calls=[]
    def call(self,method,path,payload=None,raw=False):
        self.calls.append((method,path,payload))
        if raw:return b'<html>report</html>','text/html'
        return {'data':{'accepted':True,'path':path}}


@pytest.fixture
def client():
    transport=Transport();app.config.update(TESTING=True,BRIDGE_CLIENT=transport)
    with app.test_client() as client:yield client,transport
    app.config.pop('BRIDGE_CLIENT',None)


def test_flask_does_not_require_running_bridge(monkeypatch):
    monkeypatch.delenv('GERASET_BRIDGE_TOKEN',raising=False)
    app.config.pop('BRIDGE_CLIENT',None)
    with app.test_client() as client:
        assert client.get('/inicio').status_code==200
        assert client.get('/indicadores').status_code==200
        assert client.get('/revisao').status_code==200
        assert client.get('/bridge/status').status_code==503


def test_csrf_proxy_and_no_token_in_browser(client):
    client,transport=client
    assert client.post('/bridge/jobs',json={'operation':'backtest'}).status_code==403
    csrf=client.get('/bridge/session').json['data']['csrf']
    headers={'X-GeraSet-CSRF':csrf}
    body={'operation':'backtest','symbol':'EURUSD'}
    response=client.post('/bridge/jobs',json=body,headers=headers)
    assert response.status_code==202
    assert transport.calls[-1]==('POST','/jobs/backtest',{'symbol':'EURUSD'})
    assert client.post('/bridge/jobs',json=body|{'operation':'shell'},headers=headers).status_code==400
    assert client.get('/bridge/status').status_code==200
    assert 'token' not in str(client.get('/bridge/session').json).lower()


def test_artifact_attachment_and_routes(client):
    client,_=client;job='00000000-0000-0000-0000-000000000001'
    response=client.get(f'/bridge/jobs/{job}/artifacts/report.htm')
    assert response.status_code==200 and 'attachment' in response.headers['Content-Disposition']
    assert client.get(f'/bridge/jobs/{job}/unknown').status_code==404
    assert client.get('/bridge/jobs/not-a-uuid').status_code==404


def test_client_rejects_external_or_embedded_credentials():
    for url in ('http://example.com','https://127.0.0.1','http://u:p@localhost','http://localhost/path'):
        with pytest.raises(BridgeUnavailable):HTTPBridgeClient(url,'token')


def test_flask_package_entrypoint():
    import subprocess
    result=subprocess.run([sys.executable,'-c',
        'from flask_version.app import app; r=app.test_client().get("/bridge/session"); assert r.status_code==200 and r.is_json'],
        cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
