from contextlib import contextmanager
import hashlib
import base64
import os
from pathlib import Path
import shutil
import subprocess
import time
import tempfile
import psutil
from .errors import BridgeError
from .ini import build_ini
from .models import JobRequest
from .monitor import LogMonitor
from .presets import execution_set
from .reports import read_report
from .visual import VisualPause


@contextmanager
def file_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    handle=path.open('a+b')
    if handle.tell()==0:handle.write(b'0');handle.flush()
    handle.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise BridgeError('TERMINAL_BUSY','Instalação ou worker já reservado.',409) from exc
    try:yield
    finally:
        if os.name=='nt':
            import msvcrt
            handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_UN)
        handle.close()


class MT5Runner:
    def __init__(self, settings):self.settings=settings

    def status(self):
        s=self.settings;errors=[]
        if not s.terminal.is_file():errors.append('MT5_NOT_FOUND')
        if not s.expert.is_file() or s.expert.suffix.lower()!='.ex5':errors.append('EA_NOT_FOUND')
        try:s.expert.relative_to(s.data_dir/'MQL5/Experts')
        except ValueError:errors.append('EA_OUTSIDE_DATA_DIRECTORY')
        if s.portable and s.data_dir!=s.terminal.parent:errors.append('PORTABLE_DATA_MISMATCH')
        busy=False
        for process in psutil.process_iter(['exe']):
            try:
                if process.info['exe'] and os.path.normcase(process.info['exe'])==os.path.normcase(str(s.terminal)):
                    busy=True
            except (psutil.Error,OSError):continue
        return {'ready':not errors and not busy,'busy':busy,'errors':errors,
                'terminal_found':s.terminal.is_file(),'ea_found':s.expert.is_file(),
                'installation_id':'default','symbols_authorized':s.symbols,
                'symbol_availability_verified':False,'portable':s.portable,
                'ea_sha256':hashlib.sha256(s.expert.read_bytes()).hexdigest() if s.expert.is_file() else None,
                'mcp':'not_verified_not_required','live_trading':False}

    def ensure_ready(self):
        status=self.status()
        if status['errors']:raise BridgeError(status['errors'][0],'Confira os caminhos autorizados do terminal, dados e EA.',503)
        if status['busy']:raise BridgeError('TERMINAL_BUSY','Terminal já aberto. Use uma instalação dedicada e fechada.',409)

    def ensure_queueable(self, owner):
        # An owned execution may occupy the installation while later jobs queue.
        if owner and os.path.normcase(owner['exe'])==os.path.normcase(str(self.settings.terminal)):
            try:
                process=psutil.Process(owner['pid'])
                if abs(process.create_time()-owner['created'])<0.01 and os.path.normcase(process.exe())==os.path.normcase(owner['exe']):
                    if not self.status()['errors']:return
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        self.ensure_ready()

    def execute(self, job, values, callback, cancelled):
        s=self.settings;self.ensure_ready()
        installation_hash=hashlib.sha256(os.path.normcase(str(s.terminal)).encode()).hexdigest()
        with file_lock(Path(tempfile.gettempdir())/'geraset-mt5-locks'/f'{installation_hash}.lock'):
            self.ensure_ready()
            work=s.work_dir/job['id']
            original=(work/'original.set').read_bytes()
            if hashlib.sha256(original).hexdigest()!=job['set_hash']:
                raise BridgeError('SET_HASH_MISMATCH','O arquivo preservado foi alterado.')
            request=JobRequest(**dict(job['config'],set_base64=base64.b64encode(original).decode()))
            preset_dir=s.data_dir/'MQL5/Profiles/Tester';preset_dir.mkdir(parents=True,exist_ok=True)
            preset_name=f'geraset_{job["id"]}.set';preset_path=preset_dir/preset_name
            preset_path.write_bytes(execution_set(values,request.enable_test_entries))
            shutil.copy2(preset_path,work/'execution.set')
            report_dir=s.data_dir/'geraset_reports'/job['id'];report_dir.mkdir(parents=True,exist_ok=True)
            report=report_dir/('report.xml' if job['kind']=='optimize' else 'report.htm')
            # Non-portable MT5 resolves tester report paths under its user data folder.
            relative=str(report.relative_to(s.data_dir))
            config=work/'tester.ini'
            config.write_text(build_ini(s,request,job['kind'],preset_name,relative),encoding='utf-16')
            monitor=LogMonitor(s.data_dir)
            command=[str(s.terminal),f'/config:{config}']
            if s.portable:command.append('/portable')
            # Empty profile prevents attaching existing chart EAs; trading is disabled in INI.
            (s.data_dir/'MQL5/Profiles/Charts/GeraSetTester').mkdir(parents=True,exist_ok=True)
            command.append('/profile:GeraSetTester')
            startup=None
            if os.name=='nt' and job['kind'] != 'visual':
                startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
            process=None;owner=None
            try:
                if cancelled():raise BridgeError('CANCELLED','Cancelada antes de iniciar.')
                try:process=subprocess.Popen(command,cwd=s.terminal.parent,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,startupinfo=startup)
                except OSError as exc:raise BridgeError('START_FAILED','Não foi possível iniciar o terminal.') from exc
                try:owner={'pid':process.pid,'created':psutil.Process(process.pid).create_time(),'exe':str(s.terminal)}
                except psutil.NoSuchProcess:
                    # A fast startup failure can exit before identity capture.
                    if process.poll() is None:raise BridgeError('PROCESS_IDENTITY','Não foi possível confirmar o processo iniciado.')
                callback('running',owner=owner)
                start=time.monotonic()
                visual = job['kind'] == 'visual'
                timeout = s.optimization_timeout_seconds if job['kind'] == 'optimize' else s.timeout_seconds
                pause = VisualPause(process.pid, s.terminal) if visual else None
                pause_state = None
                while process.poll() is None:
                    if cancelled():raise BridgeError('CANCELLED','Cancelamento solicitado; encerrando somente o terminal desta tarefa.')
                    if not visual and timeout and time.monotonic()-start>timeout:
                        raise BridgeError('TIMEOUT',f'Tempo limite de {timeout:g} segundos excedido.')
                    messages=monitor.poll()
                    if visual and pause_state not in ('paused','pause_unconfirmed','unsupported'):
                        if time.monotonic()-start < 60:
                            try:pause_state=pause.poll()
                            except (OSError,psutil.Error):pause_state='pause_unconfirmed'
                        else:pause_state='pause_unconfirmed'
                    callback('running',messages=messages,completed_passes=len(monitor.passes) or None,
                             visual_pause=pause_state,reported_percent=monitor.percent)
                    time.sleep(.1 if visual and pause_state in ('waiting_window','pause_requested') else s.poll_seconds)
                monitor.poll()
                if cancelled():raise BridgeError('CANCELLED','Cancelada antes da coleta.')
                callback('collecting_results',messages=monitor.messages)
                files=[]
                for source in sorted(report_dir.iterdir()):
                    if source.is_file() and source.suffix.lower() in ('.htm','.html','.xml','.png','.gif'):
                        target=work/source.name;shutil.copy2(source,target);files.append(target.name)
                if visual:
                    if process.returncode != 0:
                        raise BridgeError('TERMINAL_EXIT','A sessão visual encerrou com código de erro. Confira o journal.')
                    return {'session':'visual','closed_by_user':True,'report_available':report.is_file(),
                            'terminal_exit_code':process.returncode}, files
                if not report.is_file():
                    if monitor.error:raise BridgeError(monitor.error['code'],monitor.error['message'])
                    raise BridgeError('REPORT_MISSING','Terminal encerrou sem o relatório esperado. Confira journal da tarefa.')
                result=read_report(work/report.name)
                if request.forward_mode:
                    forward=work/(report.stem+'.forward'+report.suffix)
                    if not forward.is_file():raise BridgeError('FORWARD_REPORT_MISSING','Teste forward solicitado, mas seu relatório não foi gerado.')
                    result['forward']=read_report(forward)
                result['effective_inputs']=dict(values,InpAutoStart='false',InpTesterAutoStart=str(request.enable_test_entries).lower())
                result['terminal_exit_code']=process.returncode
                if process.returncode!=0:raise BridgeError('TERMINAL_EXIT','Terminal encerrou com código de erro; relatório preservado.')
                return result,files
            finally:
                if process and process.poll() is None:
                    self.stop_owned(owner)
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:pass
                # Only the UUID-named preset created for this task is removed.
                preset_path.unlink(missing_ok=True)

    def stop_owned(self, owner):
        if not owner:return
        try:
            process=psutil.Process(owner['pid'])
            if abs(process.create_time()-owner['created'])<0.01 and os.path.normcase(process.exe())==os.path.normcase(owner['exe']):
                process.terminate()
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
