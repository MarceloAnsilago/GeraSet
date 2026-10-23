import base64
import json
from pathlib import Path
import subprocess
import sys

import pytest

from flask_version.app import app
from geraset_domain.services import export_strategy


@pytest.fixture
def proposal():
    root = Path(__file__).resolve().parents[2]
    return json.loads((root/'geraset_domain/examples/rsi-v1.json').read_text(encoding='utf-8'))


@pytest.fixture
def api():
    class ForbiddenBridge:
        def call(self, *args, **kwargs):
            raise AssertionError('Serviços de estratégias não podem depender do Bridge.')
    old = app.config.get('BRIDGE_CLIENT')
    app.config['BRIDGE_CLIENT'] = ForbiddenBridge()
    try:
        with app.test_client() as client:
            csrf = client.get('/strategies/session').json['data']['csrf']
            yield client, {'X-GeraSet-Strategy-CSRF':csrf}
    finally:
        if old is None:
            app.config.pop('BRIDGE_CLIENT', None)
        else:
            app.config['BRIDGE_CLIENT'] = old


def test_validate_and_export_are_offline_and_keep_old_ui_available(api, proposal):
    client, headers = api
    assert client.post('/strategies/validate', json=proposal).status_code == 403
    assert client.post('/strategies/validate', json=proposal, headers=headers).json['data']['valid']
    response = client.post('/strategies/export', json={'strategy':proposal}, headers=headers)
    assert response.status_code == 200
    assert response.data == export_strategy(proposal).contents
    assert response.headers['X-GeraSet-Financial-State'] == 'not_tested'
    assert response.headers['Cache-Control'] == 'no-store'
    assert 'attachment' in response.headers['Content-Disposition']
    assert client.get('/strategies/schema').json['$id'] == 'urn:geraset:strategy:1.0'
    html = client.get('/revisao').get_data(as_text=True)
    assert 'data-export-set' in html and 'data-python-export' in html


def test_invalid_structures_options_and_uni_incompatibilities_are_distinct(api, proposal):
    client, headers = api
    bad = client.post('/strategies/validate', json=proposal | {'schema_version':'bad'}, headers=headers)
    assert bad.status_code == 422 and bad.json['data']['errors'][0]['category'] == 'structural'
    proposal['risk']['stop_loss']['distance'] = '0'
    bad = client.post('/strategies/export', json={'strategy':proposal}, headers=headers)
    assert bad.status_code == 422 and bad.json['data']['errors'][0]['category'] == 'uni'
    for body in ({'set_base64':'!invalid'}, {'set_base64':None}, {'set_base64':'','extra':True}):
        assert client.post('/strategies/compare', json=body, headers=headers).status_code == 422


def test_compare_and_legacy_export_preserve_the_snapshot(api, proposal):
    client, headers = api
    artifact = export_strategy(proposal)
    encoded = base64.b64encode(artifact.contents).decode()
    compared = client.post('/strategies/compare', json={'set_base64':encoded}, headers=headers)
    assert compared.status_code == 200 and compared.json['data']['equivalent']
    body = {'strategy':compared.json['data']['configuration']['strategy'],
            'legacy_set_base64':encoded, 'options':compared.json['data']['export_options']}
    response = client.post('/strategies/export', json=body, headers=headers)
    assert response.status_code == 200 and response.data == artifact.contents
    body['strategy']['operation']['lot'] = '0.02'
    response = client.post('/strategies/export', json=body, headers=headers)
    assert response.status_code == 422
    assert response.json['data']['errors'][0]['code'] == 'PARAMETER_MISMATCH'


def test_standalone_flask_import_can_find_the_domain_package():
    flask_dir = Path(__file__).resolve().parents[1]
    script = 'import sys;sys.path.insert(0,sys.argv[1]);from app import app;assert app.test_client().get("/strategies/schema").status_code==200'
    result = subprocess.run([sys.executable,'-I','-c',script,str(flask_dir)], cwd=flask_dir, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
