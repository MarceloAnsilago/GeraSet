const bridgeSettingsKey='geraset.bridge.test-settings.v1';
const bridgeVisualIntentKey='geraset.bridge.visual-intent';

function bindVisualShortcuts(){
    const page=document.querySelector('main[data-page]');
    if(!page||!['inicio','indicadores','gestao'].includes(page.dataset.page))return;
    page.querySelectorAll('.card').forEach(card=>{
        const parameters=card.matches('.indicator-card,.conditions-card')||
            [...card.querySelectorAll('.tab-button')].some(tab=>tab.textContent.trim()==='Parâmetros');
        if(!parameters)return;
        const actions=document.createElement('div');actions.className='card-visual-actions';
        const button=document.createElement('button');button.type='button';button.className='card-visual-shortcut';
        button.textContent='Abrir teste visual';
        button.title='Testar o setup completo com as últimas configurações de teste salvas';
        button.addEventListener('click',()=>{
            try{sessionStorage.setItem(bridgeVisualIntentKey,'1');}
            catch{window.location.assign('/revisao#teste-mt5');return;}
            window.location.assign('/revisao#teste-mt5');
        });
        actions.appendChild(button);card.appendChild(actions);
    });
}
document.addEventListener('DOMContentLoaded',bindVisualShortcuts);
