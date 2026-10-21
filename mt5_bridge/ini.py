from pathlib import Path
from .models import JobRequest
from .settings import Settings


def build_ini(settings: Settings, request: JobRequest, kind: str, preset_name: str, report_relative: str):
    expert = settings.expert.relative_to(settings.data_dir/'MQL5/Experts').as_posix().replace('/', '\\')
    common = '[Common]\nKeepPrivate=0\n'
    if settings.server:
        common += f'Server={settings.server}\n'
    if settings.login is not None:
        common += f'Login={settings.login}\n'
    values = dict(Expert=expert, ExpertParameters=preset_name, Symbol=request.symbol, Period=request.timeframe,
                  Model=request.tick_model, ExecutionMode=request.execution_delay_ms,
                  Optimization=request.optimization if kind == 'optimize' else 0,
                  OptimizationCriterion=request.optimization_criterion,
                  FromDate=request.date_from.strftime('%Y.%m.%d'), ToDate=request.date_to.strftime('%Y.%m.%d'),
                  ForwardMode=0 if kind == 'visual' else request.forward_mode, Deposit=str(request.deposit), Currency=request.currency,
                  Leverage=f'1:{request.leverage}', UseLocal=1, UseRemote=0, UseCloud=0,
                  Visual=int(kind == 'visual'), Report=report_relative.replace('/', '\\'), ReplaceReport=1,
                  ShutdownTerminal=0 if kind == 'visual' else 1)
    if request.forward_mode == 4 and kind != 'visual':
        values['ForwardDate'] = request.forward_date.strftime('%Y.%m.%d')
    # Never attach the EA to a live chart. No DLLs, startup scripts or cloud charges.
    return common+'\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n\n[StartUp]\nExpert=\nScript=\n\n[Tester]\n'+''.join(f'{k}={v}\n' for k,v in values.items())
