from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
import uuid
from .errors import BridgeError
from .models import TERMINAL_STATES


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL)')

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

    def create(self, kind, config, set_hash, max_queue):
        job = dict(id=str(uuid.uuid4()), kind=kind, state='queued', created_at=now(), started_at=None,
                   finished_at=None, config=config, set_hash=set_hash, messages=[], error=None,
                   artifacts=[], results=None, cancel_requested=False, owner=None,
                   progress={'stage':'queued','completed_passes':None,'total_passes':None,'percent':None})
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            count=db.execute("SELECT COUNT(*) FROM jobs WHERE state NOT IN ('completed','failed','cancelled')").fetchone()[0]
            if count >= max_queue:
                raise BridgeError('QUEUE_FULL','Fila cheia.',429)
            db.execute('INSERT INTO jobs VALUES (?,?,?,?)',(job['id'],job['state'],job['created_at'],json.dumps(job)))
        return job

    def get(self, job_id):
        with self.connect() as db:
            row=db.execute('SELECT payload FROM jobs WHERE id=?',(str(job_id),)).fetchone()
        if row is None:
            raise BridgeError('JOB_NOT_FOUND','Tarefa não encontrada.',404)
        return json.loads(row[0])

    def list(self, limit=50, offset=0):
        with self.connect() as db:
            rows=db.execute('SELECT payload FROM jobs ORDER BY created DESC LIMIT ? OFFSET ?',(limit,offset)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def update(self, job_id, **changes):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT payload FROM jobs WHERE id=?',(job_id,)).fetchone()
            job=json.loads(row[0])
            if job['state'] in TERMINAL_STATES and changes.get('state',job['state']) != job['state']:
                raise BridgeError('TERMINAL_JOB','Tarefa já encerrada.',409)
            if 'state' in changes and 'progress' not in changes:
                changes['progress']=dict(job['progress'],stage=changes['state'])
            job.update(changes)
            db.execute('UPDATE jobs SET state=?,payload=? WHERE id=?',(job['state'],json.dumps(job),job_id))
        return job

    def next_queued(self):
        with self.connect() as db:
            row=db.execute("SELECT id FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
        return self.get(row[0]) if row else None

    def active_owner(self):
        with self.connect() as db:
            row=db.execute("SELECT payload FROM jobs WHERE state='running' ORDER BY created LIMIT 1").fetchone()
        return json.loads(row[0]).get('owner') if row else None

    def reconcile(self):
        with self.connect() as db:
            rows=db.execute("SELECT id FROM jobs WHERE state IN ('preparing','running','collecting_results')").fetchall()
        for row in rows:
            self.update(row[0],state='failed',finished_at=now(),error={'code':'BRIDGE_RESTARTED','message':'Execução interrompida pelo reinício. Relatório não foi presumido válido; processos anteriores não foram encerrados.'})
