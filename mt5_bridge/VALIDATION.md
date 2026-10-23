# Validação — 20/10/2026

## Automatizada

29 testes Python passaram: API/autenticação, validação, fila inclusive durante execução própria, persistência e recuperação, cancelamento, exclusão mútua, identidade de processo, preparação INI, falhas de inicialização/timeout/relatório, leitura HTML/XML e proxy Flask/CSRF. Esses testes usam terminais simulados e relatórios de fixture.

70 testes JavaScript existentes passaram, preservando exportação/importação, sinais e gestão. Essa suíte não comprova execução real do testador.

O smoke test iniciou Uvicorn em loopback e consultou a API através do cliente HTTP real do Flask. Confirmou worker ativo, rejeição 401 sem token e instalação pessoal ocupada/protegida. O serviço temporário foi encerrado após o teste.

## Tentativa real, sem simulação

Preparada instalação portátil isolada com terminal e metatester build 6274 e cópia do EA atual. Não foram copiados arquivos de contas ou senhas. O cache de histórico estava bloqueado pelo terminal pessoal; não foi forçado o acesso nem encerrado esse terminal.

O Bridge lançou o executável real com seu INI, preservou os journals e registrou corretamente falha, sem publicar resultados:

| Job | Tipo | Resultado |
|---|---|---|
| `29dbde19-b12b-4246-b8a2-86f75b8ae63f` | Backtest | `failed / ACCOUNT_REQUIRED` |
| `91d1452b-9a69-4cf6-abe0-3ebaa21a3051` | Otimização completa, dois valores de lote | `failed / ACCOUNT_REQUIRED` |

Mensagem do terminal: `tester not started because the account is not specified`. Também houve aviso de porta MCP ocupada pela outra instância; o executor não depende de MCP. O terminal pessoal, PID 3008, permaneceu aberto.

SHA-256 do EA usado: `b8eeaf22fdcf297eb9f51982f959d061a1bbf173e060b7ea2bbe8c05a1c9fee1`.

Evidências locais (ignoradas pelo Git): `mt5_bridge/data/real-check-summary.json`, banco e diretórios UUID em `mt5_bridge/data/real-check/`, logs em `mt5_bridge/data/terminal-isolado/logs/`. Não são fixtures nem resultados aprovados.

## Validação real posterior com o MT5 habitual

Em 20/10/2026, o iniciador foi corrigido para usar o terminal habitual não portátil e descobrir sua pasta de dados por `origin.txt`. A tentativa anterior no isolado foi cancelada pelo Bridge. O EA não foi alterado.

O caminho relativo de relatórios foi corrigido para a pasta de dados, conforme observado no terminal instalado, build 6276. Travas ficam na pasta temporária do usuário; não há gravação de relatórios ou travas em Program Files.

| Job real | Execução | Resultado |
|---|---|---|
| `1301d30b-7639-4deb-bdf7-9f51b7d5ee67` | Backtest do set recebido, EURUSD M5, 15–20/10/2026 | `completed`, HTML e quatro imagens coletados; 1 operação, líquido −73,70 USD |
| `ab2d14fa-691b-43af-b404-21a123994116` | Cópia do mesmo set, otimização completa com dois valores de lote | `completed`, XML coletado com 2 passes; journal confirma 2 tarefas locais, sem cloud/remotos |

Os arquivos originais e de execução estão em `mt5_bridge/data/<UUID>/`, com hashes no manifesto e configuração persistida. A cópia de otimização não altera o setup do navegador. Os números acima descrevem o teste, sem julgamento da qualidade da estratégia. A suíte atual tem 31 testes Python aprovados, incluindo pasta de instalação separada dos dados.

## Verificações adicionais

Forward, algoritmo genético, outros símbolos e equivalência detalhada contra execução manual ainda exigem verificação própria. As tentativas anteriores no isolado foram preservadas e não substituem a evidência real posterior acima.

Não foi alterado o EA de produção nem reivindicada equivalência numérica com uma execução manual independente.


# Etapa 5 — validação parcial em 22/10/2026

**Estado: bloqueada; ciclo completo não aprovado.** Evidências desta tentativa são separadas dos jobs históricos. Nenhum backtest novo concluiu; não há conclusão financeira.

## Ambiente e preservação

O Fly.io respondeu HTTP 200 via cliente autenticado com credenciais locais existentes, sem exibi-las. O navegador integrado retornou `net::ERR_INVALID_AUTH_CREDENTIALS`. Seis assets publicados diferem dos locais: signal.js, app.js, export.js, import.js, visual-shortcuts.js e bridge.js. Isso comprova divergência de conteúdo, sem identificar um commit publicado. `/bridge/status` remoto respondeu 503/BRIDGE_UNAVAILABLE: `PC de casa desconectado. Confira o agente remoto.` Não houve deploy; o usuário optou por seguir localmente.

O Bridge local respondeu health=ok, worker_alive=true, ready=true, busy=false, live_trading=false. Somente EURUSD autorizado. Esse estado não comprovou acesso de escrita, conta ou histórico. As evidências iniciais estão em `C:\Users\User\Documents\Codex\2026-10-22\estamos-desenvolvendo-o-geraset-aplicativo-flask\outputs\preflight.json` e `../bridge-status.json`.

O rascunho pessoal do Fly.io não pôde ser lido nem exportado. Ele não foi alterado. O teste usou uma origem separada, `http://localhost:5000`, inicialmente com os defaults, sem substituir esse rascunho. A tentativa de exportar pelo seletor de arquivo em `127.0.0.1` ficou pendente; não se afirma que um backup atual do usuário tenha sido exportado. O `.set` técnico foi obtido do arquivo original preservado pelo Bridge, gerado pelo serializador real da interface. Os campos visíveis da sessão técnica e o contexto do teste foram restaurados aos defaults observados; evidências `restauracao-local.txt` e `restauracao-local.png`. Isso não constitui comparação byte a byte do armazenamento completo do navegador pessoal.

O EA não foi editado nem recompilado. SHA-256 inicial e final do UniEA.ex5: `fbcb1de050168a3e134e0e16be60b7a8e236d682de0ee052913e7606c5ea74c5`.

## Setup técnico efetivamente serializado pela interface

Nome `TESTE TECNICO ETAPA5 20261022`; Magic `2130617994`; Forex; Day trade; lote 0,01; direção permitida compra e venda; janela 00:00–23:55 do servidor; ordem a mercado; filtro de candle desativado. Há somente condição de compra: MA do slot 1 > MA do slot 2, ambas na vela anterior. As duas MAs são EMA/20/Close/shift 0. Slot 1 corrente (enum 0), slot 2 M15 (enum 9); slots 3/4 desativados. SL fixo 150 pontos; TP 2×SL; BE/trailing/stop móvel desativados no cenário base. Histograma e painel habilitados, 300 barras.

Contexto solicitado: EURUSD/M5, 15/10/2026 a 17/10/2026 (fim exclusivo), todos os ticks gerados (Model=0, não ticks reais), depósito 10000 USD, alavancagem 1:100, atraso 0, entradas habilitadas exclusivamente no Testador. Disponibilidade do histórico nessa tentativa não foi comprovada.

O preset não contém símbolo nem timeframe base. O INI preparado contém Symbol=EURUSD e Period=M5. Preservação de corrente/M15 no arquivo foi conferida; herança efetiva no motor e troca para base H1 permanecem sem execução.

## Jobs desta tentativa

| ID | Execução | Observado |
|---|---|---|
| 8b6efd4b-359d-44ef-aec6-4eee12128d4b | Interface → Bridge existente | failed/FILE_PERMISSION antes de preparar o MT5; journal vazio |
| 2167699f-7c28-463a-8734-d1bcedc4a86d | Reimportação na interface → Bridge existente | failed/FILE_PERMISSION; original.set idêntico ao anterior |
| 09da53bc-31e0-4400-818c-5d86720ca92c | Executor temporário com Manager/Runner do projeto e banco separado | failed/REPORT_MISSING; preset e INI gravados; sem journal novo |
| b4b39c5e-92d3-4423-a163-2bdcb99c6c07 | Mesmo executor após permissão às pastas do terminal/agente | failed/ACCOUNT_REQUIRED; MT5 build 6281 iniciou e recusou o Testador |

O executor temporário não substituiu nem encerrou o Bridge existente. Usou o mesmo terminal não portátil, mesma exclusão mútua, mesmo EA, mesmos parâmetros e somente EURUSD. Seus registros estão em `direct/<UUID>/`, com banco `direct/jobs.sqlite3`. Os dois primeiros jobs permanecem também no histórico original do Bridge; cópias conferidas por hash estão em `<UUID>/`. Datas e horários UTC completos constam nos respectivos job.json; 18h UTC corresponde a 15h em São Paulo.

O journal final registra `Accounts — deleted due security reason`, seguido de `tester not started because the account is not specified`. Após essa inicialização, `config/accounts.dat` não foi encontrado. Não foi feito backup desse arquivo antes do lançamento, portanto não se afirma seu estado anterior. Não houve alteração manual de credenciais ou segurança; a mensagem foi emitida pelo próprio MT5. Nenhuma nova inicialização foi feita após essa descoberta. O usuário precisa conferir a conta no próprio MT5 e a possibilidade de execução pelo contexto do processo; não contornar o mecanismo de proteção nem copiar credenciais.

O INI gerado desativa Experts/AllowLiveTrading/DLL, usa perfil GeraSetTester vazio, UseLocal=1, UseRemote=0, UseCloud=0 e ShutdownTerminal=1. Nenhum processo pessoal foi encerrado pelo agente. Como o Testador não iniciou a simulação, não existem operações novas ou relatórios desta tentativa para avaliar.

## Matriz de validação

| Cenário | Resultado esperado | Resultado observado | Evidência | Pendência |
|---|---|---|---|---|
| Suítes automatizadas | Sem regressões | 143 Python e 113 JavaScript passaram; 1 aviso de depreciação Python | ../python-tests.txt; ../javascript-tests.txt | Não substituem MT5 |
| Versão e conexão remotas | Conteúdo atual e conector disponível | Assets divergentes; conector 503 | C:\Users\User\Documents\Codex\2026-10-22\estamos-desenvolvendo-o-geraset-aplicativo-flask\outputs\preflight.json | Publicação/conector fora da rota local escolhida |
| Backup pessoal | Exportar setup atual antes de editar | Rascunho remoto inacessível e intocado; sessão técnica separada | Este registro | Backup atual do navegador pessoal não obtido |
| Interface → .set → interface | Valores preservados | Reimportado com sucesso; segunda serialização idêntica byte a byte | reimportacao-local.png; offline-checks.json; original.set dos dois primeiros jobs | Seletor manual de exportação não concluído |
| Mercado/lote/direção/horários/condição/SL/TP | Correspondência com Uni | Inputs nativos conferidos no .set; ainda não carregados pelo agente de teste | 8b6efd4b-359d-44ef-aec6-4eee12128d4b/inputs.json | Conferir inputs carregados, compras, saídas e horários no Testador |
| Base M5/H1 e M15 independente | Corrente herda base; explícito continua M15 | Arquivo e INI corretos para M5; nenhuma simulação | direct/b4b39c5e-92d3-4423-a163-2bdcb99c6c07/tester.ini; inputs.json | Executar M5 e H1 com o mesmo preset |
| Backtest curto | Simular e produzir relatório | MT5 iniciou, recusou por conta ausente | direct/b4b39c5e-92d3-4423-a163-2bdcb99c6c07/journal.log | Conta/contexto de execução; depois histórico |
| Breakeven isolado | Ativar em 60 e proteger 10 pontos | Exportador atual preparou arquivo válido, somente offline | breakeven.set; offline-checks.json | Carregar, reimportar este cenário e observar modificação de SL |
| Trailing isolado | Ativar 60, distância 40, passo 10 por tick | Arquivo aceito pelo validador, somente offline | trailing.set; offline-checks.json | Conferir ticks e preços de SL/TP |
| Stop móvel isolado | Ativar 60, distância 40, passo 10 na nova vela base | Arquivo aceito pelo validador, somente offline | moving.set; offline-checks.json | Conferir instantes de nova vela e preços |
| Otimização pequena | Dois passes válidos, ativação trailing 60/80 | Dois valores enumerados e validados offline; nenhum job de otimização submetido | optimize2.set; offline-checks.json | Executar otimização e conferir XML, inputs e curvas |
| Relações incompatíveis | Recusar take sem SL e trailing habilitado com zero | Ambas recusadas pelo validador real do Bridge | offline-checks.json | Cobertura real de rejeição pelo serviço em execução não acrescentada |
| Restauração | Preservar setup do usuário | Fly.io intocado; campos da sessão técnica retornados aos defaults observados | restauracao-local.txt/png | Comparação completa do rascunho pessoal indisponível |

## Integridade e limites

SHA-256 do `.set` da interface antes e depois de reimportar: `5465cf35f2e2b42c42ec011703edbf9ca570cc78b0c7d111732c88cc1a016570`.

Os quatro cenários de gestão foram preparados **offline**, usando breakevenSetLines/managedStopSetLines do export.js atual, sobre a cópia técnica exportada. Não são novos exports manuais do navegador nem testes de comportamento. `offline-checks.json` contém hashes e validação dos dois passes, sem execução simulada apresentada como real.

`manifest.json` registra hashes dos arquivos de evidência. Resultados históricos anteriores à tentativa não foram promovidos a aprovação da configuração atual. Também não foram verificados B3, ordens pendentes, sinais de saída por indicador, RSI/ADX em execução, percentuais de gestão, forward ou algoritmo genético nesta tentativa.

Próxima ação necessária: o usuário conferir autenticação/conta no MT5 habitual, sem compartilhar a senha, e permitir execução em um contexto que preserve o acesso autorizado dessa conta. Depois retomar os cenários acima e coletar relatórios/journals e inputs efetivamente carregados. Não há evidência suficiente para concluir a etapa 5.


Diretório absoluto das evidências: C:\Users\User\Documents\Codex\2026-10-22\estamos-desenvolvendo-o-geraset-aplicativo-flask\outputs\etapa5. Caminhos relativos nesta seção referem-se a esse diretório, não à pasta do Bridge.
