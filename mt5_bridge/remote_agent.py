"""Outbound HTTPS connector; MT5 and its API stay on the home PC."""
import base64
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import socket
import time
from urllib.parse import urlsplit

import httpx

from flask_version.bridge_client import HTTPBridgeClient, BridgeUnavailable

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger('geraset.remote')
GET_PATH = re.compile(r'^/(?:health|mt5/(?:status|capabilities)|jobs(?:\?limit=30|/[a-f0-9-]{36}(?:/(?:progress|results|artifacts|curves(?:\?offset=\d+&limit=\d+)?|artifacts/[A-Za-z0-9_.-]{1,100}))?)?)$')
POST_PATH = re.compile(r'^/jobs/(?:backtest|optimize|visual|[a-f0-9-]{36}/cancel)$')


def cloud_post(client, config, path, **kwargs):
    """Optional bootstrap IP handles negative DNS caching; TLS still checks hostname."""
    hostname = urlsplit(config['url']).hostname
    if config.get('bootstrap_ip'):
        try:
            socket.getaddrinfo(hostname, 443)
        except socket.gaierror:
            address = ipaddress.ip_address(config['bootstrap_ip'])
            if address.version != 4 or not address.is_global:
                raise ValueError('Bootstrap exige IPv4 publico do aplicativo Fly.')
            headers = {**kwargs.pop('headers', {}), 'Host': hostname}
            req = client.build_request('POST', 'https://'+str(address)+path, headers=headers,
                                       extensions={'sni_hostname': hostname}, **kwargs)
            return client.send(req)
    return client.post(path, **kwargs)


def execute(task, bridge):
    method, path = task.get('method'), task.get('path', '')
    if not ((method == 'GET' and GET_PATH.fullmatch(path)) or
            (method == 'POST' and POST_PATH.fullmatch(path))):
        return {'error': {'code': 'INVALID_REMOTE_REQUEST', 'message': 'Pedido remoto invalido.', 'status': 400}}
    try:
        value = bridge.call(method, path, task.get('payload'), raw=task.get('raw', False))
        if task.get('raw'):
            body, mime = value
            return {'body': base64.b64encode(body).decode('ascii'), 'mime': mime}
        return {'data': value}
    except BridgeUnavailable as exc:
        return {'error': {'message': exc.message, 'status': exc.status, 'code': exc.code}}


def run(config_path=None):
    config = json.loads(Path(config_path or ROOT/'mt5_bridge/data/remote-agent.json').read_text())
    parts = urlsplit(config['url'])
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('', '/'):
        raise ValueError('O servidor remoto deve usar uma URL HTTPS sem caminhos.')
    if len(config['agent_token']) < 32:
        raise ValueError('Credencial remota invalida.')
    local = json.loads((ROOT/'mt5_bridge/data/local-service-secrets.json').read_text())
    bridge = HTTPBridgeClient('http://127.0.0.1:8765', local['token'])
    journal = sqlite3.connect(ROOT/'mt5_bridge/data/remote-agent.sqlite3')
    journal.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, response TEXT, created REAL)')
    with httpx.Client(base_url=config['url'].rstrip('/'),
                      headers={'Authorization': 'Bearer '+config['agent_token']}, timeout=40,
                      follow_redirects=False, trust_env=False) as cloud:
        delay = 1
        while True:
            try:
                # Retry delivery of saved responses, never execution of a request.
                for ident, result in journal.execute('SELECT id,response FROM requests WHERE response IS NOT NULL').fetchall():
                    reply = cloud_post(cloud, config, '/agent/v1/responses/'+ident, content=result, headers={'Content-Type': 'application/json'})
                    if reply.status_code in (200, 410):
                        journal.execute('DELETE FROM requests WHERE id=?', (ident,))
                        journal.commit()
                    else:
                        reply.raise_for_status()
                reply = cloud_post(cloud, config, '/agent/v1/poll')
                reply.raise_for_status()
                task = reply.json()['data']
                delay = 1
                if not task:
                    time.sleep(1)
                    continue
                ident = task['id']
                previous = journal.execute('SELECT response FROM requests WHERE id=?', (ident,)).fetchone()
                if previous:
                    result = json.loads(previous[0]) if previous[0] else {'error': {
                        'code': 'REMOTE_UNCERTAIN', 'status': 409,
                        'message': 'Pedido interrompido. Confira o historico antes de repetir.'}}
                else:
                    journal.execute('INSERT INTO requests VALUES (?,NULL,?)', (ident, time.time()))
                    journal.commit()
                    result = execute(task, bridge)
                journal.execute('UPDATE requests SET response=? WHERE id=?', (json.dumps(result), ident))
                journal.commit()
                journal.execute('DELETE FROM requests WHERE response IS NULL AND created<?', (time.time()-86400,))
                journal.commit()
            except (httpx.HTTPError, ValueError, KeyError, OSError) as exc:
                # Do not log request URLs, credentials, payloads or reports.
                LOG.warning('Conexao remota indisponivel (%s); nova tentativa em %ss.', type(exc).__name__, delay)
                time.sleep(delay)
                delay = min(30, delay * 2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s')
    run(os.getenv('GERASET_AGENT_CONFIG'))
