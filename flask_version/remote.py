"""Single-home-PC outbound relay. Requests are claimed once, never replayed."""
import base64
from contextlib import contextmanager
import hmac
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.security import check_password_hash
from .bridge_client import BridgeUnavailable

relay = Blueprint('relay', __name__, url_prefix='/agent/v1')


class RelayStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS rpc (id TEXT PRIMARY KEY, created REAL, state TEXT, request TEXT, response TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS presence (id INTEGER PRIMARY KEY, seen REAL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def submit(self, payload):
        now = time.time()
        with self.connect() as db:
            seen = db.execute('SELECT seen FROM presence WHERE id=1').fetchone()
            if not seen or now - seen['seen'] > 15:
                raise BridgeUnavailable('PC de casa desconectado. Confira o agente remoto.')
            count = db.execute("SELECT count(*) FROM rpc WHERE state='queued' AND created>?", (now-25,)).fetchone()[0]
            if count >= 30:
                raise BridgeUnavailable('Conexao ocupada. Aguarde e tente novamente.', 429)
            ident = str(uuid.uuid4())
            db.execute('INSERT INTO rpc VALUES (?,?,?,?,NULL)', (ident, now, 'queued', json.dumps(payload)))
        return ident

    def claim(self):
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR REPLACE INTO presence VALUES (1,?)', (now,))
            db.execute('DELETE FROM rpc WHERE created<?', (now-300,))
            db.execute("UPDATE rpc SET state='expired' WHERE state='queued' AND created<?", (now-25,))
            row = db.execute("SELECT * FROM rpc WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE rpc SET state='claimed' WHERE id=?", (row['id'],))
                return {'id': row['id'], **json.loads(row['request'])}
        return None

    def finish(self, ident, result):
        with self.connect() as db:
            row = db.execute('SELECT state FROM rpc WHERE id=?', (ident,)).fetchone()
            if not row or row['state'] not in ('claimed', 'done'):
                return False
            if row['state'] == 'claimed':
                db.execute("UPDATE rpc SET state='done',response=? WHERE id=?", (json.dumps(result), ident))
        return True

    def result(self, ident):
        with self.connect() as db:
            row = db.execute('SELECT response FROM rpc WHERE id=?', (ident,)).fetchone()
            return json.loads(row['response']) if row and row['response'] else None


class RelayClient:
    def __init__(self, store):
        self.store = store

    def call(self, method, path, payload=None, raw=False):
        ident = self.store.submit({'method': method, 'path': path, 'payload': payload, 'raw': raw})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            result = self.store.result(ident)
            if result is not None:
                if 'error' in result:
                    err = result['error']
                    raise BridgeUnavailable(err['message'], err.get('status', 503), err.get('code', 'BRIDGE_ERROR'))
                if raw:
                    return base64.b64decode(result['body'], validate=True), result['mime']
                return result['data']
            time.sleep(.15)
        raise BridgeUnavailable('PC sem resposta. O pedido pode ter sido recebido: confira o historico antes de executar novamente.', 504, 'REMOTE_TIMEOUT')


@relay.before_request
def agent_auth():
    expected = 'Bearer ' + current_app.config['REMOTE_AGENT_TOKEN']
    if not hmac.compare_digest(request.headers.get('Authorization', ''), expected):
        return jsonify(error='unauthorized'), 401


@relay.post('/poll')
def poll():
    return jsonify(data=current_app.config['RELAY_STORE'].claim())


@relay.post('/responses/<uuid:ident>')
def response(ident):
    result = request.get_json(silent=True)
    if not isinstance(result, dict):
        return jsonify(error='invalid response'), 400
    valid = ('data' in result or
             isinstance(result.get('error'), dict) and isinstance(result['error'].get('message'), str) or
             isinstance(result.get('body'), str) and isinstance(result.get('mime'), str))
    if not valid:
        return jsonify(error='invalid response'), 400
    accepted = current_app.config['RELAY_STORE'].finish(str(ident), result)
    return jsonify(accepted=accepted), 200 if accepted else 410


def configure_remote(app):
    if os.getenv('GERASET_REMOTE') != '1':
        return
    required = ('GERASET_FLASK_SECRET', 'GERASET_AGENT_TOKEN', 'GERASET_WEB_USER', 'GERASET_WEB_PASSWORD_HASH')
    if any(not os.getenv(key) for key in required):
        raise RuntimeError('Configure todos os segredos do modo remoto.')
    if len(os.environ['GERASET_AGENT_TOKEN']) < 32:
        raise RuntimeError('Credencial remota muito curta.')
    app.config.update(SESSION_COOKIE_SECURE=True, REMOTE_AGENT_TOKEN=os.environ['GERASET_AGENT_TOKEN'])
    store = RelayStore(os.getenv('GERASET_RELAY_DB', '/data/relay.sqlite3'))
    app.config.update(RELAY_STORE=store, BRIDGE_CLIENT=RelayClient(store))
    app.register_blueprint(relay)

    @app.before_request
    def protect_remote():
        if request.path == '/healthz':
            return None
        if request.path.startswith('/agent/v1/'):
            # Large base64 artifacts are accepted only on the authenticated agent API.
            request.max_content_length = 72 * 1024 * 1024
            return None
        auth = request.authorization
        if not (auth and auth.type == 'basic' and
                hmac.compare_digest(auth.username or '', os.environ['GERASET_WEB_USER']) and
                check_password_hash(os.environ['GERASET_WEB_PASSWORD_HASH'], auth.password or '')):
            return Response('Entre com seu usuario e senha do GeraSet.', 401,
                            {'WWW-Authenticate': 'Basic realm="GeraSet", charset="UTF-8"', 'Cache-Control': 'no-store'})

    @app.after_request
    def private_response(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

