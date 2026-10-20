async function bindBridge() {
    const card=document.querySelector('[data-bridge]');
    if(!card)return;
    const status=card.querySelector('[data-bridge-status]'), current=card.querySelector('[data-bridge-current]');
    const results=card.querySelector('[data-bridge-results]'), history=card.querySelector('[data-bridge-history]');
    let csrf='',active=null,polling=false,stopped=false;
    const terminal=new Set(['completed','failed','cancelled']);
    const field=name=>card.querySelector(`[name="bridge-${name}"]`);
    const request=async(path,options={})=>{
        const response=await fetch('/bridge'+path,{...options,headers:{'Content-Type':'application/json','X-GeraSet-CSRF':csrf,...options.headers}});
        const body=await response.json();
        if(!response.ok)throw new Error(body.error?.message||'Falha de comunicação com o Bridge.');
        return body.data;
    };
    function message(text){const p=document.createElement('p');p.textContent=text;return p;}
    async function showResult(id){
        const [value,artifacts]=await Promise.all([request(`/jobs/${id}/results`),request(`/jobs/${id}/artifacts`)]);
        results.replaceChildren(message('Resultados disponíveis. Valores ausentes não foram estimados.'));
        const pre=document.createElement('pre');pre.textContent=JSON.stringify(value,null,2);results.appendChild(pre);
        artifacts.forEach(artifact=>{
            const link=document.createElement('a');link.textContent=`Baixar ${artifact.name}`;
            link.href=`/bridge/jobs/${id}/artifacts/${encodeURIComponent(artifact.id)}`;link.className='btn';results.appendChild(link);
        });
    }
    async function refreshHistory(){
        const jobs=await request('/jobs');history.replaceChildren();
        jobs.forEach(job=>{
            const row=message(`${job.config.setup_id} · ${job.kind} · ${job.state}`);
            const button=document.createElement('button');button.type='button';button.className='btn';button.textContent='Consultar';
            button.addEventListener('click',()=>{active=job.id;results.replaceChildren();poll();});row.appendChild(button);history.appendChild(row);
        });
        const running=jobs.find(job=>!terminal.has(job.state));
        if(!active&&running){active=running.id;poll();}
    }
    async function poll(){
        if(polling||!active||stopped)return;
        polling=true;
        try{
            const progress=await request(`/jobs/${active}/progress`);
            current.replaceChildren(message(`${progress.state} · ${progress.elapsed_seconds}s · etapa: ${progress.stage}`));
            if(progress.completed_passes!=null)current.appendChild(message(`Passes observados: ${progress.completed_passes}${progress.total_passes!=null?' / '+progress.total_passes:''}`));
            if(progress.percent!=null)current.appendChild(message(`Progresso observado: ${progress.percent}%`));
            progress.messages.slice(-5).forEach(text=>current.appendChild(message(text)));
            if(progress.error)current.appendChild(message(`${progress.error.code}: ${progress.error.message}`));
            card.querySelector('[data-bridge-cancel]').disabled=terminal.has(progress.state);
            if(progress.state==='completed')await showResult(active);
            if(terminal.has(progress.state))await refreshHistory();
            else setTimeout(poll,2000);
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
        event.preventDefault();const button=card.querySelector('[data-bridge-run]');button.disabled=true;
        try{
            if(!csrf)csrf=(await request('/session')).csrf;
            const roots=new Map(await Promise.all(['inicio','indicadores','gestao','configuracoes'].map(async page=>{
                const response=await fetch('/'+page);if(!response.ok)throw new Error('Falha ao preparar o set atual.');
                return [page,new DOMParser().parseFromString(await response.text(),'text/html')];
            })));
            const file=serializeSetupSet(roots);
            let binary='';for(const byte of file.contents)binary+=String.fromCharCode(byte);
            const operation=field('operation').value;
            const payload={operation,setup_id:file.filename.replace(/\.set$/i,''),set_name:file.filename,set_base64:btoa(binary),
                symbol:field('symbol').value,timeframe:field('timeframe').value,date_from:field('from').value,date_to:field('to').value,
                tick_model:Number(field('model').value),deposit:field('deposit').value,currency:field('currency').value,
                leverage:Number(field('leverage').value),execution_delay_ms:Number(field('delay').value),
                optimization:Number(field('optimization').value),optimization_criterion:Number(field('criterion').value),
                forward_mode:Number(field('forward').value),enable_test_entries:field('entries').checked};
            if(payload.forward_mode===4)payload.forward_date=field('forward-date').value;
            const job=await request('/jobs',{method:'POST',body:JSON.stringify(payload)});
            active=job.id;results.replaceChildren();status.textContent=`Tarefa recebida: ${active}`;poll();
        }catch(error){status.textContent=error.message;}
        finally{button.disabled=false;}
    });
    window.addEventListener('pagehide',()=>{stopped=true;});
    connect();
}
document.addEventListener('DOMContentLoaded',bindBridge);
