from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hmac
import mimetypes
import threading
import time
from typing import Annotated
from uuid import UUID
from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .errors import BridgeError
from .manager import Manager
from .models import JobRequest
from .monitor import reported_percent
from .runner import MT5Runner
from .settings import Settings


class BodyLimit:
    def __init__(self,app,limit=1500000):self.app,self.limit=app,limit
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        data=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            data.extend(message.get('body',b''))
            if len(data)>self.limit:
                return await JSONResponse({'error':{'code':'BODY_TOO_LARGE','message':'Requisição excede o limite.'}},status_code=413)(scope,receive,send)
            if not message.get('more_body'):break
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:delivered=True;return {'type':'http.request','body':bytes(data),'more_body':False}
            return await receive()
        return await self.app(scope,replay,send)


def create_app(settings:Settings|None=None,runner=None,start_worker=True):
    settings=settings or Settings.from_env()
    runner=runner or MT5Runner(settings)
    manager=Manager(settings,runner)
    bearer=HTTPBearer(auto_error=False)
    calls=defaultdict(deque);rate_lock=threading.Lock()

    def auth(request:Request,credentials:Annotated[HTTPAuthorizationCredentials|None,Depends(bearer)]):
        if not credentials or credentials.scheme.lower()!='bearer' or not hmac.compare_digest(credentials.credentials,settings.token):
            raise BridgeError('UNAUTHORIZED','Token de serviço ausente ou inválido.',401)
        key=request.client.host if request.client else 'unknown';now=time.monotonic()
        with rate_lock:
            if key not in calls and len(calls)>=1024:calls.pop(next(iter(calls)))
            queue=calls[key]
            while queue and queue[0]<now-60:queue.popleft()
            if len(queue)>=180:raise BridgeError('RATE_LIMIT','Limite de requisições excedido.',429)
            queue.append(now)

    @asynccontextmanager
    async def lifespan(app):
        if start_worker:manager.start()
        yield
        if start_worker:manager.close()

    app=FastAPI(title='GeraSet MT5 Bridge',version='1.0.0',lifespan=lifespan,dependencies=[Depends(auth)])
    app.state.manager=manager
    app.add_middleware(BodyLimit)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])

    @app.exception_handler(BridgeError)
    async def error(request,exc):return JSONResponse({'error':{'code':exc.code,'message':exc.message}},status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid(request,exc):
        return JSONResponse({'error':{'code':'VALIDATION_ERROR','message':'Confira os campos da solicitação.',
                                     'fields':[{'loc':list(e['loc']),'type':e['type'],'message':e['msg']} for e in exc.errors()]}},status_code=422)

    def data(value):return {'data':value}
    def public(job):
        return {k:v for k,v in job.items() if k!='owner'}

    @app.get('/api/v1/health')
    def health():return data({'status':'ok','service':'geraset-mt5-bridge','worker_alive':bool(manager.thread and manager.thread.is_alive())})

    @app.get('/api/v1/mt5/status')
    def status():return data(runner.status())

    @app.get('/api/v1/mt5/capabilities')
    def capabilities():
        return data({'installation_id':'default','symbols_authorized':settings.symbols,'currencies':settings.currencies,
                     'tick_models':[0,1,2,4],'optimization_modes':[1,2],'optimization_criteria':list(range(8)),
                     'forward_modes':list(range(5)),'max_queue':settings.max_queue,'max_passes':settings.max_passes,
                     'visual_sessions':True,'visual_initial_pause':'native_menu_confirmed_when_available',
                     'backtest_timeout_seconds':settings.timeout_seconds,
                     'optimization_timeout_seconds':settings.optimization_timeout_seconds,
                     'max_set_bytes':settings.max_set_bytes,'transport':'terminal_ini','progress_source':'bounded incremental journals',
                     'live_trading':False,'partial_metrics':False,'mcp_availability':'not_verified'})

    @app.post('/api/v1/jobs/backtest',status_code=202)
    def backtest(body:JobRequest):return data(public(manager.submit('backtest',body)))

    @app.post('/api/v1/jobs/optimize',status_code=202)
    def optimize(body:JobRequest):return data(public(manager.submit('optimize',body)))

    @app.post('/api/v1/jobs/visual',status_code=202)
    def visual(body:JobRequest):return data(public(manager.submit('visual',body)))

    @app.get('/api/v1/jobs')
    def jobs(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):
        return data([public(job) for job in manager.store.list(limit,offset)])

    @app.get('/api/v1/jobs/{job_id}')
    def job(job_id:UUID):return data(public(manager.store.get(str(job_id))))

    @app.get('/api/v1/jobs/{job_id}/progress')
    def progress(job_id:UUID):
        job=manager.store.get(str(job_id))
        start=datetime.fromisoformat(job['started_at'] or job['created_at'])
        end=datetime.fromisoformat(job['finished_at']) if job['finished_at'] else datetime.now(timezone.utc)
        observed=dict(job['progress'])
        if observed.get('percent') is None:
            observed['percent']=reported_percent(job['messages'])
            if observed['percent'] is not None:observed['source']='mt5_journal'
        return data(dict(observed,state=job['state'],elapsed_seconds=round((end-start).total_seconds(),1),messages=job['messages'],error=job['error']))

    @app.get('/api/v1/jobs/{job_id}/results')
    def results(job_id:UUID):
        job=manager.store.get(str(job_id))
        if job['state']!='completed':raise BridgeError('RESULTS_NOT_READY','Resultados ainda não disponíveis; consulte o estado.',409)
        return data(job['results'])

    @app.get('/api/v1/jobs/{job_id}/artifacts')
    def artifacts(job_id:UUID):return data(manager.store.get(str(job_id))['artifacts'])

    @app.get('/api/v1/jobs/{job_id}/artifacts/{artifact_id}')
    def download(job_id:UUID,artifact_id:str):
        job=manager.store.get(str(job_id))
        if artifact_id not in {a['id'] for a in job['artifacts']}:raise BridgeError('ARTIFACT_NOT_FOUND','Artefato não encontrado.',404)
        path=settings.work_dir/str(job_id)/artifact_id
        if path.resolve().parent!=(settings.work_dir/str(job_id)).resolve() or not path.is_file():
            raise BridgeError('ARTIFACT_NOT_FOUND','Artefato indisponível.',404)
        return FileResponse(path,filename=artifact_id,media_type=mimetypes.guess_type(artifact_id)[0] or 'application/octet-stream',headers={'X-Content-Type-Options':'nosniff'})

    @app.post('/api/v1/jobs/{job_id}/cancel')
    def cancel(job_id:UUID):return data(public(manager.cancel(str(job_id))))
    return app
