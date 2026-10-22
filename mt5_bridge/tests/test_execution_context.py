import base64
from dataclasses import replace

from fastapi.testclient import TestClient

from mt5_bridge.api import create_app
from mt5_bridge.ini import build_ini
from mt5_bridge.models import JobRequest


class ReadyRunner:
    def ensure_ready(self):
        pass


def test_same_strategy_preserves_distinct_execution_context_per_job(settings, payload):
    settings = replace(settings, symbols=('EURUSD', 'WIN$'))
    headers = {'Authorization': 'Bearer '+settings.token}
    app = create_app(settings, ReadyRunner(), start_worker=False)
    contexts = [('EURUSD', 'M5'), ('WIN$', 'H1')]
    with TestClient(app) as client:
        jobs = []
        for symbol, timeframe in contexts:
            body = payload | {'symbol': symbol, 'timeframe': timeframe}
            response = client.post('/api/v1/jobs/backtest', json=body, headers=headers)
            assert response.status_code == 202
            jobs.append(response.json()['data'])
        assert jobs[0]['set_hash'] == jobs[1]['set_hash']
        for job, (symbol, timeframe) in zip(jobs, contexts):
            stored = client.get('/api/v1/jobs/'+job['id'], headers=headers).json()['data']
            assert stored['config']['symbol'] == symbol
            assert stored['config']['timeframe'] == timeframe
            assert (settings.work_dir/job['id']/'original.set').read_bytes() == base64.b64decode(payload['set_base64'])
            request = JobRequest(**(stored['config'] | {'set_base64': payload['set_base64']}))
            ini = build_ini(settings, request, 'backtest', 'preset.set', 'report.htm')
            assert f'Symbol={symbol}\nPeriod={timeframe}\n' in ini
        # Execution context must resolve to an explicit test period, unlike a slot.
        for invalid in ('Tempo corrente', 'PERIOD_CURRENT', 'M7', ''):
            response = client.post('/api/v1/jobs/backtest', json=payload | {'timeframe': invalid}, headers=headers)
            assert response.status_code == 422
