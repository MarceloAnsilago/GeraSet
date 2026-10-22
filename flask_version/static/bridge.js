function renderBridgeProgress(progress,documentRef=document) {
    const block=documentRef.createElement('div');block.className='bridge-progress';
    const states={queued:'Na fila',preparing:'Preparando teste',running:'Em execução',collecting_results:'Coletando resultados',completed:'Concluído',failed:'Falhou',cancelled:'Cancelado'};
    const ended=['completed','failed','cancelled'].includes(progress.state);
    const percent=progress.state==='completed'?100
        :typeof progress.percent==='number'&&Number.isFinite(progress.percent)&&progress.percent>=0&&progress.percent<=100?progress.percent:null;
    const label=documentRef.createElement('p');
    const seconds=Math.max(0,Math.floor(progress.elapsed_seconds||0));
    const elapsed=seconds>=3600?`${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}min` : seconds>=60?`${Math.floor(seconds/60)}min ${seconds%60}s`:`${seconds}s`;
    label.textContent=`${states[progress.state]||progress.state} · ${elapsed}${percent!==null?' · '+percent.toLocaleString('pt-BR')+'%':''}`;
    const bar=documentRef.createElement('progress');bar.max=100;bar.setAttribute('aria-label','Progresso da tarefa');
    if(percent!==null)bar.value=percent;
    else if(ended)bar.value=0;
    if(progress.state==='failed'||progress.state==='cancelled')block.className+=' bridge-progress-stopped';
    const hint=documentRef.createElement('p');hint.className='muted';
    hint.textContent=progress.state==='completed'?'Execução concluída.'
        :progress.state==='failed'?(progress.error?.message||'A execução falhou. Confira o erro da tarefa.')
        :progress.state==='cancelled'?'Execução cancelada.'
        :ended?(percent===null?'Execução encerrada sem porcentagem informada.':`Execução encerrada em ${percent.toLocaleString('pt-BR')}%.`)
        :percent===null?'Aguardando o MT5 informar o progresso...':'Progresso informado pelo testador.';
    block.append(label,bar,hint);
    if(progress.total_passes!=null){
        const passes=documentRef.createElement('p');passes.className='muted';
        passes.textContent=progress.completed_passes!=null?`Passes observados: ${progress.completed_passes} / ${progress.total_passes}`:`Combinações previstas: ${progress.total_passes.toLocaleString('pt-BR')}`;
        block.appendChild(passes);
    }
    return block;
}

function bridgeExecutionContextText(config) {
    const value = key => String(config?.[key] ?? '').trim() || 'não informado';
    return `Ativo: ${value('symbol')} · timeframe base: ${value('timeframe')} · datas: ${value('date_from')} a ${value('date_to')} (fim exclusivo)`;
}

async function bindBridge() {
    const card=document.querySelector('[data-bridge]');
    if(!card)return;
    const testForm=card.querySelector('[data-bridge-form]');
    const settingsKey='geraset.bridge.test-settings.v1';
    let savedTestSettings=null,visualShortcut=false;
    try{
        savedTestSettings=JSON.parse(localStorage.getItem(settingsKey)||'null');
        visualShortcut=sessionStorage.getItem('geraset.bridge.visual-intent')==='1';
        sessionStorage.removeItem('geraset.bridge.visual-intent');
    }catch{}
    if(savedTestSettings&&typeof savedTestSettings==='object'){
        for(const control of testForm.querySelectorAll('[name^="bridge-"]')){
            const value=savedTestSettings[control.name];
            if(control.type==='checkbox'&&typeof value==='boolean')control.checked=value;
            else if(typeof value==='string')control.value=value;
        }
        const period=testForm.querySelector('[name="bridge-period"]');
        if(period&&period.value!=='custom')period.dispatchEvent(new Event('change'));
    }
    const saveTestSettings=()=>{
        const values={};
        for(const control of testForm.querySelectorAll('[name^="bridge-"]'))values[control.name]=control.type==='checkbox'?control.checked:control.value;
        try{localStorage.setItem(settingsKey,JSON.stringify(values));}catch{}
    };
    testForm.addEventListener('change',saveTestSettings);
    const status=card.querySelector('[data-bridge-status]'), current=card.querySelector('[data-bridge-current]');
    const results=card.querySelector('[data-bridge-results]'), history=card.querySelector('[data-bridge-history]');
    let csrf='',active=null,activeConfig=null,polling=false,stopped=false;
    let curveJob=null,curveOffset=0,curvePlot=null;
    const curveRoot=card.querySelector('[data-bridge-curves]');
    async function updateCurves(id,progress){
        if(curveJob!==id){
            curvePlot?.destroy();curvePlot=null;curveOffset=0;curveJob=id;curveRoot.replaceChildren();
        }
        curveRoot.hidden=progress.kind!=='optimize';
        if(curveRoot.hidden)return false;
        let page;
        try{
            for(let batch=0;batch<4;batch++){
                page=await request(`/jobs/${id}/curves?offset=${curveOffset}&limit=500`);
                if(!curvePlot)curvePlot=new GeraSetCurvePlot(curveRoot);
                curvePlot.add(page.curves);curveOffset=page.offset;
                if(!page.more)break;
            }
            if(terminal.has(progress.state)&&(!page.available||curveOffset===0)){
                curvePlot?.destroy();curvePlot=null;
                curveRoot.replaceChildren(message('Esta tarefa não possui curvas por passe. A coleta está disponível nas novas otimizações com o UniEA atualizado.'));
            }
            return page.more;
        }catch(error){
            if(!curvePlot)curveRoot.replaceChildren(message(`Curvas indisponíveis: ${error.message}`));
            return false;
        }
    }
    const terminal=new Set(['completed','failed','cancelled']);
    const field=name=>card.querySelector(`[name="bridge-${name}"]`);
    const executionContext=card.querySelector('[data-bridge-execution-context]');
    const updateExecutionContext=()=>{
        if(executionContext)executionContext.textContent='Próximo teste — '+bridgeExecutionContextText({
            symbol:field('symbol').value,timeframe:field('timeframe').value,
            date_from:field('from').value,date_to:field('to').value,
        });
    };
    testForm.addEventListener('input',updateExecutionContext);
    testForm.addEventListener('change',updateExecutionContext);
    updateExecutionContext();
    const runButton=card.querySelector('[data-bridge-run]');
    function updateRunLabel(){runButton.textContent=field('operation').value==='optimize'
        ? 'Executar otimização de combinações' : 'Executar backtest (valores fixos)';}
    field('operation').addEventListener('change',updateRunLabel);updateRunLabel();
    const request=async(path,options={})=>{
        const response=await fetch('/bridge'+path,{...options,headers:{'Content-Type':'application/json','X-GeraSet-CSRF':csrf,...options.headers}});
        if(!response.headers.get('content-type')?.includes('application/json')){
            throw new Error(response.status===404
                ? 'A integração do Bridge não está carregada no Flask. Reinicie o servidor GeraSet e atualize a página.'
                : `O servidor retornou uma resposta inesperada (HTTP ${response.status}). Confira o servidor GeraSet.`);
        }
        let body;
        try{body=await response.json();}
        catch{throw new Error('O servidor retornou JSON inválido. Confira os logs do GeraSet.');}
        if(!response.ok)throw new Error(body.error?.message||'Falha de comunicação com o Bridge.');
        return body.data;
    };
    function message(text){const p=document.createElement('p');p.textContent=text;return p;}
    async function showResult(id){
        const [value,artifacts]=await Promise.all([request(`/jobs/${id}/results`),request(`/jobs/${id}/artifacts`)]);
        results.replaceChildren(message(value.session==='visual'
            ? 'Sessão visual encerrada. Os arquivos disponíveis estão abaixo.'
            : 'Resultados disponíveis. Valores ausentes não foram estimados.'));
        const reports=artifacts.filter(artifact=>/\.html?$/i.test(artifact.name));
        reports.forEach(artifact=>{
            const heading=document.createElement('h3');heading.textContent=artifact.name;results.appendChild(heading);
            const frame=document.createElement('iframe');
            frame.title=`Relatório MT5: ${artifact.name}`;frame.className='bridge-report';
            frame.setAttribute('sandbox','');
            frame.src=`/bridge/jobs/${id}/preview/${encodeURIComponent(artifact.id)}`;
            results.appendChild(frame);
        });
        function showPasses(report,label){
            (report?.worksheets||[]).forEach((sheet,index)=>{
                const heading=document.createElement('h3');heading.textContent=`${label} · ${sheet.passes.length} passes`;results.appendChild(heading);
                const wrap=document.createElement('div');wrap.className='bridge-table-wrap';
                const table=document.createElement('table');table.className='bridge-pass-table';
                const head=document.createElement('thead'), row=document.createElement('tr');
                sheet.columns.forEach(column=>{const th=document.createElement('th');th.textContent=column;row.appendChild(th);});
                head.appendChild(row);table.appendChild(head);
                const body=document.createElement('tbody');table.appendChild(body);wrap.appendChild(table);results.appendChild(wrap);
                const controls=document.createElement('div');controls.className='bridge-report-pages';
                const previous=document.createElement('button'),next=document.createElement('button'),info=document.createElement('span');
                previous.type=next.type='button';previous.className=next.className='btn';previous.textContent='Anterior';next.textContent='Próxima';
                let page=0;
                function render(){
                    body.replaceChildren();
                    sheet.passes.slice(page*100,(page+1)*100).forEach(pass=>{
                        const tr=document.createElement('tr');
                        sheet.columns.forEach(column=>{const td=document.createElement('td');td.textContent=pass[column]??'';tr.appendChild(td);});
                        body.appendChild(tr);
                    });
                    previous.disabled=page===0;next.disabled=(page+1)*100>=sheet.passes.length;
                    info.textContent=`Página ${page+1} de ${Math.max(1,Math.ceil(sheet.passes.length/100))}`;
                }
                previous.addEventListener('click',()=>{page--;render();});next.addEventListener('click',()=>{page++;render();});
                controls.append(previous,info,next);results.appendChild(controls);render();
            });
        }
        showPasses(value,'Otimização');showPasses(value.forward,'Forward');
        if(!reports.length&&!value.worksheets?.length){
            results.appendChild(message(value.session==='visual'?'Esta sessão não gerou relatório para exibir.':'Relatório original indisponível para visualização. Consulte os detalhes abaixo.'));
        }
        const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Detalhes dos resultados';
        const pre=document.createElement('pre');pre.textContent=JSON.stringify(value,null,2);details.append(summary,pre);results.appendChild(details);
        const downloads=document.createElement('details'),downloadSummary=document.createElement('summary');downloadSummary.textContent='Baixar relatórios e arquivos';
        downloads.appendChild(downloadSummary);results.appendChild(downloads);
        artifacts.forEach(artifact=>{
            const link=document.createElement('a');link.textContent=`Baixar ${artifact.name}`;
            link.href=`/bridge/jobs/${id}/artifacts/${encodeURIComponent(artifact.id)}`;link.className='btn';downloads.appendChild(link);
        });
    }
    async function refreshHistory(){
        const jobs=await request('/jobs');history.replaceChildren();
        jobs.forEach(job=>{
            const row=message(`${job.config.setup_id} · ${job.kind} · ${job.state} · ${bridgeExecutionContextText(job.config)}`);
            const button=document.createElement('button');button.type='button';button.className='btn';button.textContent='Consultar';
            button.addEventListener('click',()=>{active=job.id;activeConfig=job.config;results.replaceChildren();poll();});row.appendChild(button);history.appendChild(row);
        });
        const running=jobs.find(job=>!terminal.has(job.state));
        if(!active&&running){active=running.id;activeConfig=running.config;poll();}
    }
    async function poll(){
        if(polling||!active||stopped)return;
        polling=true;
        try{
            const progress=await request(`/jobs/${active}/progress`);
            current.replaceChildren(renderBridgeProgress(progress));
            if(activeConfig)current.appendChild(message('Contexto registrado da tarefa — '+bridgeExecutionContextText(activeConfig)));
            if(progress.visual_pause){
                const labels={waiting_window:'Aguardando a janela visual do MT5...',pause_requested:'Pausa inicial solicitada; aguardando confirmação.',
                    paused:'Pausa inicial confirmada. Vá ao MT5 e clique em Iniciar para acompanhar a estratégia.',
                    pause_unconfirmed:'Não foi possível confirmar a pausa inicial. Confira os controles na janela do MT5.',
                    unsupported:'Pausa automática indisponível neste sistema. Use os controles do MT5.',
                    window_closed:'A janela visual foi fechada. Feche o terminal para liberar a próxima tarefa.'};
                current.appendChild(message(labels[progress.visual_pause]||progress.visual_pause));
            }
            if(progress.messages.length){
                const log=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Diário do testador';
                log.appendChild(summary);progress.messages.slice(-5).forEach(text=>log.appendChild(message(text)));current.appendChild(log);
            }
            if(progress.error)current.appendChild(message(`${progress.error.code}: ${progress.error.message}`));
            const moreCurves=await updateCurves(active,progress);
            card.querySelector('[data-bridge-cancel]').disabled=terminal.has(progress.state);
            if(progress.state==='completed')await showResult(active);
            if(terminal.has(progress.state))await refreshHistory();
            else setTimeout(poll,2000);
            if(terminal.has(progress.state)&&moreCurves)setTimeout(poll,2000);
        }catch(error){status.textContent=error.message;setTimeout(poll,5000);}
        finally{polling=false;}
    }
    async function connect(){
        try{
            csrf=(await request('/session')).csrf;
            const value=await request('/status');
            status.textContent=value.mt5.ready?'Bridge conectado. MT5 disponível.':value.mt5.busy?'Bridge conectado. Instalação MT5 ocupada.':`Bridge conectado. Confira o MT5: ${value.mt5.errors.join(', ')}.`;
            await refreshHistory();
        }catch(error){status.textContent=error.message;}
    }
    card.querySelector('[data-bridge-connect]').addEventListener('click',connect);
    card.querySelector('[data-bridge-cancel]').addEventListener('click',async()=>{
        if(!active)return;
        try{await request(`/jobs/${active}/cancel`,{method:'POST'});poll();}catch(error){status.textContent=error.message;}
    });
    card.querySelector('[data-bridge-form]').addEventListener('submit',async event=>{
        saveTestSettings();
        event.preventDefault();const buttons=[runButton,card.querySelector('[data-bridge-visual]'),card.querySelector('[data-bridge-optimize]')];
        buttons.forEach(button=>button.disabled=true);
        try{
            if(!csrf)csrf=(await request('/session')).csrf;
            const roots=new Map(await Promise.all(['inicio','indicadores','gestao','configuracoes'].map(async page=>{
                const response=await fetch('/'+page);if(!response.ok)throw new Error('Falha ao preparar o set atual.');
                return [page,new DOMParser().parseFromString(await response.text(),'text/html')];
            })));
            const file=serializeSetupSet(roots);
            let binary='';for(const byte of file.contents)binary+=String.fromCharCode(byte);
            const operation=event.submitter?.hasAttribute('data-bridge-visual')?'visual'
                :event.submitter?.hasAttribute('data-bridge-optimize')?'optimize':field('operation').value;
            if(operation==='optimize'){field('operation').value='optimize';updateRunLabel();}
            const payload={operation,setup_id:file.filename.replace(/\.set$/i,''),set_name:file.filename,set_base64:btoa(binary),
                symbol:field('symbol').value,timeframe:field('timeframe').value,date_from:field('from').value,date_to:field('to').value,
                tick_model:Number(field('model').value),deposit:field('deposit').value,currency:field('currency').value,
                leverage:Number(field('leverage').value),execution_delay_ms:Number(field('delay').value),
                optimization:Number(field('optimization').value),optimization_criterion:Number(field('criterion').value),
                forward_mode:operation==='visual'?0:Number(field('forward').value),enable_test_entries:field('entries').checked};
            if(payload.forward_mode===4)payload.forward_date=field('forward-date').value;
            const job=await request('/jobs',{method:'POST',body:JSON.stringify(payload)});
            active=job.id;activeConfig=job.config;results.replaceChildren();status.textContent=operation==='visual'
                ? 'Sessão visual solicitada. Aguarde a janela do MT5.'
                : operation==='optimize' ? `Otimização recebida: ${active}. O MT5 testará os intervalos configurados.`
                : `Backtest recebido: ${active}. Executa somente os valores fixos.`;poll();
        }catch(error){status.textContent=error.message;}
        finally{buttons.forEach(button=>button.disabled=false);}
    });
    window.addEventListener('pagehide',()=>{stopped=true;curvePlot?.destroy();});
    await connect();
    if(visualShortcut){
        if(savedTestSettings&&testForm.checkValidity()){
            testForm.requestSubmit(card.querySelector('[data-bridge-visual]'));
        }else{
            status.textContent='Defina o ativo, timeframe base, intervalo de datas e demais configurações e clique em Abrir teste visual. Os próximos atalhos usarão essas configurações.';
            testForm.querySelector('[name="bridge-symbol"]').focus();
        }
    }
}
document.addEventListener('DOMContentLoaded',bindBridge);
