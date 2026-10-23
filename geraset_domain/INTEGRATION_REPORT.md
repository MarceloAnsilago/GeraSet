# Relatório — integração dos serviços, 22/10/2026

## Arquivos e responsabilidades

| Arquivos | Mudança |
|---|---|
| `geraset_domain/services.py` | Configuração JSON, diagnósticos, exportação offline, comparação e envelope compatível |
| `geraset_domain/configuration.py` | Inputs nativos → modelo v1.0; usa bindings existentes para otimização |
| `geraset_domain/strategy.py` | Campos opcionais para display, posição dos sinais, slots desativados e preferência de referência de venda |
| `geraset_domain/uni_mapping.py` | Projeção desses campos sem perder slots ou preferências; expõe bindings ao adaptador |
| `geraset_domain/strategy-v1.schema.json` | Schema regenerado a partir do Python |
| `flask_version/strategy_routes.py`, `app.py` | Adaptadores HTTP, CSRF, respostas privadas e suporte ao entrypoint standalone |
| `flask_version/static/python-export.js`, `templates/page.html` | Ação paralela explícita com comparação antes do download; botão antigo preservado |
| `geraset_domain/tests/test_strategy_services.py` | Testes offline, classificação de erros, round-trip e equivalência |
| `flask_version/tests/helpers/legacy-export-fixture.cjs` | Executa serializer/validadores JS reais com snapshots controlados |
| `flask_version/tests/python-export.test.cjs` | Ordem comparação/exportação, bloqueio por divergência e independência do fluxo antigo |
| `flask_version/tests/test_strategy_routes.py` | API sem Bridge, CSRF, exportação e bloqueio por inconsistência |
| READMEs e `SERVICES.md` | Fluxos, formatos, API e limitações |

O exportador JS anterior e o importador visual não foram removidos ou substituídos.
Não houve instalação de dependências, implementação de agente, publicação no Fly.io
ou alteração no código do Uni. As regras Python de validação existentes foram
reutilizadas; não foi criado outro conjunto de regras de negócio.

## Funcionalidades conferidas

20 cenários originados no exportador JS: mercado, quatro referências OHLC pendentes,
espelhamento (inclusive preferência inativa em mercado), candle de referência,
SL fixo/candle/corpo, TP fixo/múltiplo, unidades pontos/percentual, horários noturnos,
BE, trailing, móvel, preço/método/período/shift, RSI/ADX, timeframes por slot,
otimizações, fontes DI/níveis RSI, cruzamentos, distância de sinal, inversão de lado,
lacunas na grade, visualização e ativação exclusiva de teste.

Em cada cenário foram conferidos os valores nativos e os intervalos ativos do
arquivo Python independente. No envelope compatível, os bytes e o hash do arquivo
anterior permanecem idênticos após validação, preservando comentários e ajustes
inativos. Testes com mutações e parâmetros não representados comprovam bloqueio
de divergências, não apenas retorno incondicional do original.

## Verificação

- 223 testes Python aprovados.
- 116 testes JavaScript aprovados.
- Schema JSON conferido contra o modelo Python.
- Serviços e API executados sem MT5/Bridge; o teste HTTP usa transporte que falha
  caso seja chamado indevidamente.
- Uma advertência de depreciação já existente em Starlette/AnyIO, sem falha.

Não houve teste visual no navegador nem novo backtest real. Esta entrega valida
conversão e geração, não comportamento de negociação ou desempenho financeiro.
As limitações de rascunhos, formato canônico v1.0 no importador visual e subconjunto
de otimizações estão explicitadas em `SERVICES.md`.
