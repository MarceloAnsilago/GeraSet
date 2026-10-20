import hashlib
import json
import logging
import math
from pathlib import Path
import threading
from .errors import BridgeError
from .models import JobRequest, TERMINAL_STATES
from .presets import parse_set
from .runner import file_lock
from .store import Store, now

logger=logging.getLogger('geraset.bridge')


class Manager:
    def __init__(self,settings,runner):
        self.settings=settings;self.runner=runner
        self.store=Store(settings.work_dir/'jobs.sqlite3')
        self.stop=threading.Event();self.wake=threading.Event();self.submit_lock=threading.Lock();self.thread=None;self.leader=None

    def start(self):
        self.leader=file_lock(self.settings.work_dir/'.worker.lock');self.leader.__enter__()
        self.store.reconcile()
        self.thread=threading.Thread(target=self.loop,name='mt5-worker',daemon=True);self.thread.start()

    def close(self):
        self.stop.set();self.wake.set()
        if self.thread:self.thread.join(timeout=10)
        if self.leader and (self.thread is None or not self.thread.is_alive()):self.leader.__exit__(None,None,None)

    def submit(self,kind,request:JobRequest):
        if request.symbol not in self.settings.symbols or request.currency not in self.settings.currencies:
            raise BridgeError('NOT_AUTHORIZED','Símbolo ou moeda não autorizados no servidor.')
        raw,values,ranges,digest=parse_set(request.set_base64,self.settings.max_set_bytes)
        if kind=='optimize' and not ranges:raise BridgeError('NO_OPTIMIZATION_RANGE','Selecione ao menos um intervalo Y no .set.')
        combinations=math.prod(ranges.values()) if kind=='optimize' else None
        total=combinations if request.optimization==1 and request.forward_mode==0 else None
        if combinations is not None and combinations>self.settings.max_passes:raise BridgeError('PASS_LIMIT','Espaço de combinações excede o limite autorizado do servidor.')
        if hasattr(self.runner,'ensure_queueable'):
            self.runner.ensure_queueable(self.store.active_owner())
        else:self.runner.ensure_ready()
        config=request.model_dump(mode='json');config['set_base64']=''
        with self.submit_lock:
            job=self.store.create(kind,config,digest,self.settings.max_queue)
            path=self.settings.work_dir/job['id'];path.mkdir()
            try:
                (path/'original.set').write_bytes(raw)
                (path/'inputs.json').write_text(json.dumps(values,ensure_ascii=False),encoding='utf-8')
                progress=dict(job['progress'],total_passes=total)
                job=self.store.update(job['id'],progress=progress,artifacts=self.artifacts(path))
            except OSError:
                self.store.update(job['id'],state='failed',finished_at=now(),error={'code':'FILE_ERROR','message':'Falha ao preservar o .set.'})
                raise BridgeError('FILE_ERROR','Falha ao gravar tarefa.',500)
        self.wake.set()
        return job

    def artifacts(self,path):
        allowed={'.set','.ini','.htm','.html','.xml','.png','.gif','.json','.log'}
        return [{'id':p.name,'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(path.iterdir()) if p.is_file() and p.suffix in allowed and p.stat().st_size<=50*1024*1024]

    def cancel(self,job_id):
        with self.submit_lock:
            job=self.store.get(job_id)
            if job['state'] in TERMINAL_STATES:raise BridgeError('TERMINAL_JOB','Tarefa já encerrada.',409)
            changes={'cancel_requested':True}
            if job['state']=='queued':changes.update(state='cancelled',finished_at=now())
            self.wake.set();return self.store.update(job_id,**changes)

    def loop(self):
        while not self.stop.is_set():
            with self.submit_lock:
                job=self.store.next_queued()
                if job:job=self.store.update(job['id'],state='preparing',started_at=now())
            if not job:
                self.wake.wait(1);self.wake.clear();continue
            self.run_job(job)

    def run_job(self,job):
        path=self.settings.work_dir/job['id']
        def cancelled():return self.stop.is_set() or self.store.get(job['id'])['cancel_requested']
        def callback(stage,**updates):
            latest=self.store.get(job['id']);progress=dict(latest['progress'],stage=stage)
            count=updates.pop('completed_passes',None)
            if count is not None:
                progress['completed_passes']=count
                total=progress['total_passes'];progress['percent']=round(100*count/total,2) if total and count<=total else None
            self.store.update(job['id'],state=stage,progress=progress,**updates)
        try:
            values=json.loads((path/'inputs.json').read_text(encoding='utf-8'))
            # Restore only the locally preserved payload; never accept client paths.
            result,files=self.runner.execute(job,values,callback,cancelled)
            if cancelled():raise BridgeError('CANCELLED','Cancelada antes da publicação de resultados.')
            self.store.update(job['id'],state='completed',finished_at=now(),results=result,artifacts=self.artifacts(path),
                              progress=dict(self.store.get(job['id'])['progress'],stage='completed'))
        except BridgeError as exc:
            self.store.update(job['id'],state='cancelled' if exc.code=='CANCELLED' else 'failed',finished_at=now(),
                              error={'code':exc.code,'message':exc.message})
        except PermissionError:
            self.store.update(job['id'],state='failed',finished_at=now(),error={
                'code':'FILE_PERMISSION','message':'Sem permissão para gravar arquivos de teste. Confira o diretório de dados e relatórios do MT5.'})
        except Exception as exc:
            logger.error(json.dumps({'event':'job_error','job_id':job['id'],'type':type(exc).__name__}))
            self.store.update(job['id'],state='failed',finished_at=now(),error={'code':'INTERNAL_ERROR','message':'Falha interna; consulte o log local do bridge.'})
        finally:
            final=self.store.get(job['id'])
            try:
                (path/'journal.log').write_text('\n'.join(final['messages']),encoding='utf-8')
                self.store.update(job['id'],artifacts=self.artifacts(path))
            except OSError:logger.error(json.dumps({'event':'artifact_write_failed','job_id':job['id']}))
            logger.info(json.dumps({'event':'job_finished','job_id':job['id'],'state':self.store.get(job['id'])['state']}))
