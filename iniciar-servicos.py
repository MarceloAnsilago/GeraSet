"""Start local GeraSet services with persistent server-only credentials."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
python = ROOT / '.venv/Scripts/python.exe'
check = subprocess.run([str(python), '-c', 'import flask, uvicorn, fastapi, pydantic, psutil, httpx'],
                       capture_output=True, text=True)
if check.returncode:
    raise SystemExit('Dependencias ausentes no ambiente do projeto. Execute:\n'
                     r'.\.venv\Scripts\python.exe -m pip install -r mt5_bridge/requirements.txt -r flask_version/requirements-flask.txt')
DATA = ROOT / 'mt5_bridge' / 'data'
DATA.mkdir(parents=True, exist_ok=True)
secret_file = DATA / 'local-service-secrets.json'
if not secret_file.exists():
    secret_file.write_text(json.dumps({'token': secrets.token_urlsafe(48), 'flask_secret': secrets.token_hex(32)}))
credentials = json.loads(secret_file.read_text())
env = os.environ.copy()
terminal = Path(env.get('MT5_TERMINAL_PATH', r'C:\Program Files\MetaTrader 5\terminal64.exe'))
data_dir = env.get('MT5_DATA_DIR')
if not data_dir:
    candidates=[]
    terminals=Path(env.get('APPDATA', ''))/'MetaQuotes/Terminal'
    for origin in terminals.glob('*/origin.txt'):
        raw=origin.read_bytes()
        location=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').strip()
        if os.path.normcase(location)==os.path.normcase(str(terminal.parent)):
            candidates.append(origin.parent)
    if len(candidates)!=1:
        raise SystemExit('Configure MT5_DATA_DIR com o diretorio de dados do MT5 habitual.')
    data_dir=str(candidates[0])
env.update(BRIDGE_TOKEN=credentials['token'], GERASET_BRIDGE_TOKEN=credentials['token'],
           GERASET_FLASK_SECRET=credentials['flask_secret'], GERASET_BRIDGE_URL='http://127.0.0.1:8765',
           MT5_TERMINAL_PATH=str(terminal), MT5_DATA_DIR=data_dir,
           MT5_EA_PATH=env.get('MT5_EA_PATH',str(Path(data_dir)/'MQL5/Experts/Uni/UniEA.ex5')), MT5_PORTABLE=env.get('MT5_PORTABLE','false'),
           MT5_ALLOWED_SYMBOLS='EURUSD', BRIDGE_DATA_DIR=str(DATA))

def listening(url, headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

processes = {}
services = [
    ('bridge', str(python), ['-m', 'mt5_bridge'], 'http://127.0.0.1:8765/api/v1/health', {'Authorization': 'Bearer ' + credentials['token']}),
    ('flask', str(ROOT / '.venv/Scripts/python.exe'), ['-m', 'flask', '--app', 'flask_version.app', 'run', '--host', '127.0.0.1', '--port', '5000'], 'http://127.0.0.1:5000/bridge/status', {}),
]
for name, executable, args, url, headers in services:
    if listening(url, headers):
        print(name + ': conectado')
        continue
    with (DATA / (name + '-service.log')).open('ab') as log:
        process = subprocess.Popen([executable, *args], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    processes[name] = process.pid
    for attempt in range(30):
        if listening(url, headers):
            print(name + ': conectado')
            break
        if process.poll() is not None:
            raise SystemExit(name + ': falha; consulte mt5_bridge/data/' + name + '-service.log')
        time.sleep(0.5)
    else:
        raise SystemExit(name + ': sem resposta')
(DATA / 'local-service-processes.json').write_text(json.dumps(processes))
print('Abra http://127.0.0.1:5000')
