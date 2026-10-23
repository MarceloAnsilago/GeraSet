// Staged migration: the original exporter remains independent. This opt-in
// action compares its snapshot against Python before downloading any file.
async function bindPythonExport() {
    const button = document.querySelector('[data-python-export]');
    const status = document.querySelector('[data-python-export-status]');
    if (!button || !status) return;
    const jsonRequest = async (path, options = {}) => {
        const response = await fetch('/strategies'+path, options);
        let body;
        try { body = await response.json(); }
        catch { throw new Error('O serviço Python não está disponível nesta versão do servidor. O exportador atual continua disponível.'); }
        if (!response.ok) throw new Error(body.data?.errors?.map(error => error.message).join(' ') || body.error?.message || 'Falha na exportação Python.');
        return body.data;
    };
    button.addEventListener('click', async () => {
        button.disabled = true;
        try {
            status.textContent = 'Preparando configuração e comparando com o Python...';
            const roots = new Map(await Promise.all(['inicio','indicadores','gestao','configuracoes'].map(async page => {
                const response = await fetch('/'+page);
                if (!response.ok) throw new Error('Não foi possível carregar a configuração atual.');
                const root = new DOMParser().parseFromString(await response.text(), 'text/html');
                if (!root.querySelector(`[data-page="${page}"]`)) throw new Error('Página de configuração inválida.');
                return [page, root];
            })));
            const original = serializeSetupSet(roots);
            let binary = '';
            for (const byte of original.contents) binary += String.fromCharCode(byte);
            const encoded = btoa(binary);
            const {csrf} = await jsonRequest('/session');
            const headers = {'Content-Type': 'application/json', 'X-GeraSet-Strategy-CSRF': csrf};
            const comparison = await jsonRequest('/compare', {method: 'POST', headers, body: JSON.stringify({set_base64: encoded})});
            if (!comparison.equivalent) throw new Error('Exportação bloqueada por divergência em: '+comparison.differences.map(item => item.input).join(', '));
            const response = await fetch('/strategies/export', {method: 'POST', headers, body: JSON.stringify({
                strategy: comparison.configuration.strategy, options: comparison.export_options, legacy_set_base64: encoded,
            })});
            if (!response.ok) {
                const body = await response.json();
                throw new Error(body.data?.errors?.map(error => error.message).join(' ') || 'O Python recusou a exportação.');
            }
            const contents = new Uint8Array(await response.arrayBuffer());
            downloadSetupSet({filename: original.filename, contents});
            status.textContent = 'Inputs e otimizações equivalentes. Download gerado pelo fluxo Python com os metadados e campos anteriores preservados. '
                + comparison.configuration.warnings.map(warning => warning.message).join(' ');
        } catch (error) {
            status.textContent = error.message+' O botão Exportar set mantém o fluxo atual.';
        } finally {
            button.disabled = false;
        }
    });
}

document.addEventListener('DOMContentLoaded', bindPythonExport);
