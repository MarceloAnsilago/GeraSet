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

## Aceitação ainda pendente

Configurar uma conta de demonstração e histórico válido na instalação dedicada, fechar o terminal e repetir pelo Bridge: um backtest e uma otimização curta. Conferir relatórios HTML/XML originais, entradas efetivas, operações e passes contra o MT5. Depois verificar forward, genética e símbolos adicionais conforme necessidade. O sucesso dos testes simulados e da inicialização real não substitui essa aceitação.

Não foi alterado o EA de produção nem reivindicada equivalência numérica de resultados reais nesta etapa.
