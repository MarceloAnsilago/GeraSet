# GeraSet MT5 Bridge

Serviço local independente do Flask. Executa tarefas em uma instalação dedicada do MT5 por arquivos INI, preserva o `.set` recebido, mantém fila SQLite e publica resultados e artefatos. Não executa operações em conta real.

## Instalação no Windows

Use Python 3.11 ou posterior. Na raiz do GeraSet:

```powershell
python -m venv mt5_bridge/.venv
./mt5_bridge/.venv/Scripts/Activate.ps1
python -m pip install -r mt5_bridge/requirements.txt
```

Prepare uma instalação **separada** do MT5, com permissão de escrita, histórico e símbolo disponíveis e `MQL5/Experts/Uni/UniEA.ex5` atualizado. Configure a conta de demonstração nessa instalação pelo próprio MT5, feche o terminal e reserve essa instalação ao Bridge. A instalação pessoal aberta não pode ser usada simultaneamente. Não copie credenciais entre instalações.

O exemplo `.env.example` documenta as variáveis; o serviço não carrega `.env` automaticamente. Defina-as no ambiente do processo. Gere um segredo com `python -c "import secrets; print(secrets.token_urlsafe(48))"` e mantenha-o privado:

```powershell
$env:BRIDGE_TOKEN = '<segredo aleatório com pelo menos 32 caracteres>'
$env:MT5_TERMINAL_PATH = 'D:\MT5-Bridge\terminal64.exe'
$env:MT5_DATA_DIR = 'D:\MT5-Bridge'
$env:MT5_EA_PATH = 'D:\MT5-Bridge\MQL5\Experts\Uni\UniEA.ex5'
$env:MT5_PORTABLE = 'true'
$env:MT5_ALLOWED_SYMBOLS = 'EURUSD'
$env:MT5_ALLOWED_CURRENCIES = 'USD,BRL,EUR'
$env:MT5_SERVER = 'nome exato do servidor configurado'
./mt5_bridge/iniciar-bridge.ps1
```

O processo usa `127.0.0.1:8765`, um worker e token Bearer obrigatório. Para instalação não portátil, use `MT5_PORTABLE=false` e o diretório de dados correto do terminal. Não use a instalação pessoal como diretório de testes. A descoberta verifica os caminhos autorizados, existência do EA e processos abertos; não comprova disponibilidade de cotação, conta ou histórico.

No processo Flask, configure `GERASET_BRIDGE_URL=http://127.0.0.1:8765`, `GERASET_BRIDGE_TOKEN` com o mesmo segredo e `GERASET_FLASK_SECRET` persistente. Abra **Revisão**, configure o teste e clique em executar. O Flask continua abrindo páginas e exportando `.set` quando o Bridge está desligado. Nenhum token é enviado ao JavaScript.

## API

O limite de duração do backtest é `BRIDGE_TIMEOUT_SECONDS` (padrão: 1800 segundos).
A otimização usa um limite separado, `BRIDGE_OPTIMIZATION_TIMEOUT_SECONDS`:
o padrão `0` permite executar até terminar ou até o usuário cancelar. Um valor
positivo configura o limite em segundos. Alterações de ambiente exigem reiniciar
o Bridge. O limite de 10.000 combinações continua independente da duração.

### Sessão visual

Em **Revisão**, preencha símbolo, timeframe, datas e condições do teste e clique em
**Abrir teste visual**. O botão usa o set atual, desativa otimização e forward e
abre o MT5 visível (`Visual=1`, `ShutdownTerminal=0`). A API correspondente é
`POST /api/v1/jobs/visual`, com o mesmo corpo do backtest.

No Windows, o Bridge procura a janela visual de um agente descendente do terminal
que ele iniciou e solicita a pausa pelo menu nativo. Confirma a pausa quando
**Iniciar** e **Parar** estão habilitados. O comando é enviado uma única vez;
o usuário retoma pelo **Iniciar** do MT5. A mensagem no GeraSet registra a
confirmação da pausa inicial, não acompanha pausas e retomadas posteriores.

A pausa ocorre assim que o controle fica disponível: não existe garantia de zero
ticks antes dela. Menus em português e inglês são reconhecidos. Após 60 segundos
sem confirmação, o GeraSet informa que a pausa não foi confirmada, mantendo a
sessão aberta para controle manual. A sessão requer uma área de trabalho Windows
interativa; não deve ser executada como serviço sem desktop.

Não há timeout da sessão visual. A instalação fica ocupada até fechar o terminal
ou cancelar a tarefa no GeraSet. Fechar só a janela de visualização não libera a
fila. A conclusão significa encerramento da sessão e não exige relatório nem
presume sucesso financeiro. Relatórios existentes são preservados como artefatos.

Validação local em 21/10/2026, MT5 build 6276: EURUSD/M5, 15 a 20/10/2026,
todos os ticks. A pausa foi confirmada na tela às 00:00 de 15/10, com Iniciar
habilitado, Pausar desabilitado e nenhuma posição aberta. A retomada executou
o teste e o fechamento do terminal concluiu a sessão com relatório preservado.
As evidências locais estão em `data/visual-acceptance/`, tarefa
`25bc25e2-a1f2-4ce7-99a3-deb10c838977`.

Documentação interativa: `http://127.0.0.1:8765/docs`; use Authorize. Todas as rotas `/api/v1` exigem Bearer, inclusive health.

| Método | Rota | Uso |
|---|---|---|
| GET | `/api/v1/health` | Serviço e worker |
| GET | `/api/v1/mt5/status` | Instalação, EA e ocupação |
| GET | `/api/v1/mt5/capabilities` | Valores e limites autorizados |
| POST | `/api/v1/jobs/backtest` | Enfileirar teste |
| POST | `/api/v1/jobs/optimize` | Enfileirar otimização |
| GET | `/api/v1/jobs?limit=50&offset=0` | Histórico paginado |
| GET | `/api/v1/jobs/{id}` | Estado e configuração |
| GET | `/api/v1/jobs/{id}/progress` | Etapa, tempo e progresso observado |
| GET | `/api/v1/jobs/{id}/results` | Resultados concluídos |
| GET | `/api/v1/jobs/{id}/artifacts` | Arquivos e hashes |
| GET | `/api/v1/jobs/{id}/artifacts/{artifact_id}` | Download |
| POST | `/api/v1/jobs/{id}/cancel` | Solicitar cancelamento |

Exemplo Python, executado com o token já no ambiente:

```python
import base64, os, time
from pathlib import Path
import httpx

with httpx.Client(base_url='http://127.0.0.1:8765',
                  headers={'Authorization': 'Bearer '+os.environ['BRIDGE_TOKEN']}) as client:
    payload = {
        'setup_id': 'Meu setup', 'set_name': 'Meu setup.set',
        'set_base64': base64.b64encode(Path('Meu setup.set').read_bytes()).decode(),
        'symbol': 'EURUSD', 'timeframe': 'M5',
        'date_from': '2026-10-01', 'date_to': '2026-10-17',
        'tick_model': 1, 'deposit': '10000', 'currency': 'USD', 'leverage': 100,
        'execution_delay_ms': 0, 'enable_test_entries': True,
        'optimization': 1, 'optimization_criterion': 0, 'forward_mode': 0,
    }
    response = client.post('/api/v1/jobs/backtest', json=payload)
    response.raise_for_status()
    job = response.json()['data']
    while job['state'] not in ('completed', 'failed', 'cancelled'):
        time.sleep(2)
        job = client.get('/api/v1/jobs/'+job['id']).json()['data']
    print(job['state'], job.get('error'))
```

Para otimização, use `/jobs/optimize` com o mesmo corpo e um `.set` atual contendo pelo menos um intervalo `valor||início||passo||fim||Y`. `optimization=1` é completa e `2` genética. `optimization_criterion` vai de 0 a 7 conforme MT5. Consulte capabilities para limites. A versão inicial limita também o espaço de busca genética a `BRIDGE_MAX_PASSES`; não promete que o algoritmo executará todas as combinações. Forward: 0 desativado, 1 metade, 2 terço, 3 quarto, 4 data personalizada (`forward_date`).

## Integridade e comportamento

- UUID por tarefa, hash SHA-256 do `.set`, configuração, timestamps, journal e artefatos preservados em `BRIDGE_DATA_DIR` (padrão `mt5_bridge/data`). Backups exigem banco SQLite e diretórios das tarefas. Sem exclusão automática de histórico.
- O arquivo original não é alterado. Uma cópia de execução força `InpAutoStart=false` e `InpTesterAutoStart` conforme o pedido; a cópia também fica disponível. Fora do testador, operações e DLL ficam desativadas no INI. Perfil vazio evita carregar EAs de gráficos existentes.
- Caminhos do executável, EA e dados são definidos no servidor. O cliente não fornece caminhos nem comandos. Entradas desconhecidas são rejeitadas pelo contrato em `contracts/uni_inputs.json`; atualize esse contrato quando o EA mudar. Não há conversão de sets legados.
- Um terminal por vez, trava de instalação e worker, fila limitada. Instância externa aberta retorna `TERMINAL_BUSY`; o Bridge não a fecha. Cancelamento verifica PID, horário de criação e executável antes de terminar seu processo.
- Ao reiniciar, tarefas interrompidas viram `failed/BRIDGE_RESTARTED`; processos antigos não são assumidos nem encerrados. Se algum terminal permanecer aberto, feche-o manualmente após verificar a origem. Tarefas ainda na fila são preservadas.
- Não há porcentagem estimada por tempo. Passes só são contados quando observados nos journals; percentual só existe com total conhecido. Histórico/carregamento e backtests podem ficar sem percentual até o fim.
- Relatórios originais HTML/XML são preservados. Números usam strings decimais; métrica ausente é `null`. HTML reconhece rótulos em português/inglês. XML conserva colunas e valores de cada passe. Outros idiomas/formats podem exigir adaptação. Nenhuma rentabilidade é presumida a partir do estado do processo.
- Limites: corpo 1,5 MB, `.set` 1 MB, relatório/artefato 50 MB, 180 chamadas/minuto/IP autenticado. Valores padrão de fila, tempo e combinações estão no `.env.example`. Timeout e cancelamento são terminais com erro explícito; resultados incompletos não são publicados como completos.
- Sem senha na API ou logs intencionais. Proteja diretórios de dados com permissões Windows: relatórios e configurações podem conter informações da estratégia. O serviço não é destinado à exposição direta na rede.

## Verificação

```powershell
python -m pytest mt5_bridge/tests flask_version/tests/test_bridge_routes.py -q
node --test flask_version/tests/*.test.cjs
```

Os testes automatizados usam processos simulados e fixtures de relatórios. **Eles não substituem prova real do MT5.** Para aceitar uma instalação: execute um backtest curto e uma otimização completa com dois ou três passes; confira símbolos/datas/EA, relatórios originais, entradas efetivas, operações, métricas e os passes no MT5. Em seguida teste cancelamento e reinício. Registre hashes, IDs e resultado; lucro não é critério de sucesso técnico.

A tentativa real desta implementação e suas limitações estão em `VALIDATION.md`. Dependências Python não fornecem histórico nem autorização de conta. B3, sufixos Forex, moedas, sessões e ticks dependem da corretora; adicione símbolos à lista autorizada apenas após confirmar a instalação.

Mecanismo oficial: [inicialização e configuração do MT5](https://www.metatrader5.com/en/terminal/help/start_advanced/start). A disponibilidade do MCP recente do terminal não foi comprovada nesta instalação; não é uma dependência desta versão. Consulte também [BRIDGE_ARCHITECTURE.md](../BRIDGE_ARCHITECTURE.md).
