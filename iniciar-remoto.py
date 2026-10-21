"""Start existing local services, then the outbound agent, with no console window."""
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT/'.venv/Scripts/python.exe'
DATA = ROOT/'mt5_bridge/data'


if __name__ == '__main__':
    config = DATA/'remote-agent.json'
    if not config.exists():
        raise SystemExit('Configure mt5_bridge/data/remote-agent.json antes de iniciar.')
    # This reuses the same MT5 paths and local credentials as the current setup.
    subprocess.run([str(PYTHON), str(ROOT/'iniciar-servicos.py')], cwd=ROOT, check=True)
    import psutil
    for process in psutil.process_iter(['cmdline']):
        try:
            if 'mt5_bridge.remote_agent' in (process.info['cmdline'] or []):
                print('Agente remoto ja esta em execucao.')
                raise SystemExit(0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    with (DATA/'remote-agent.log').open('ab') as log:
        process = subprocess.Popen([str(PYTHON), '-m', 'mt5_bridge.remote_agent'], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    (DATA/'remote-agent-process.json').write_text(json.dumps({'pid': process.pid}))
    print('Agente remoto iniciado. Mantenha este PC ligado e conectado.')
