import json
import pytest
from mt5_bridge.curves import read_curves
from mt5_bridge.errors import BridgeError


def curve(pass_id='0'):
    return {'pass':pass_id,'trades':2,'points':[[1000,10000],[2000,10050]]}


def test_curve_pagination_and_partial_write(tmp_path):
    path=tmp_path/'curves.jsonl'
    assert not read_curves(path)['available']
    first=json.dumps(curve())+'\n';second=json.dumps(curve('1'))+'\n'
    path.write_bytes((first+second[:10]).encode('utf-8'))
    page=read_curves(path)
    assert page['curves']==[curve()] and page['offset']==len(first) and not page['more']
    with path.open('ab') as stream:stream.write(second[10:].encode('utf-8'))
    assert read_curves(path,page['offset'])['curves']==[curve('1')]
    assert read_curves(path,limit=1)['more']
    with pytest.raises(BridgeError):read_curves(path,3)


@pytest.mark.parametrize('points',[[[2000,10000],[1000,10050]],[[1000,float('nan')],[2000,0]],[[1000,1]]])
def test_invalid_curve_data_rejected(tmp_path,points):
    path=tmp_path/'curves.jsonl';data=curve();data['points']=points
    path.write_text(json.dumps(data)+'\n',encoding='utf-8')
    with pytest.raises(BridgeError):read_curves(path)


def test_curve_endpoint_reads_only_the_requested_job(settings,payload):
    from fastapi.testclient import TestClient
    from mt5_bridge.api import create_app
    from mt5_bridge.models import JobRequest
    from test_bridge import FakeMT5
    app=create_app(settings,FakeMT5(settings),start_worker=False)
    manager=app.state.manager;job=manager.submit('backtest',JobRequest(**payload))
    path=settings.work_dir/job['id']/'curves.jsonl'
    path.write_bytes((json.dumps(curve())+'\n').encode('utf-8'))
    url=f"/api/v1/jobs/{job['id']}/curves"
    with TestClient(app) as client:
        assert client.get(url).status_code==401
        headers={'Authorization':'Bearer '+settings.token}
        response=client.get(url,headers=headers)
        assert response.json()['data']['curves']==[curve()]
        assert client.get(url+'?offset=-1',headers=headers).status_code==422
        assert client.get(url+'?limit=501',headers=headers).status_code==422
