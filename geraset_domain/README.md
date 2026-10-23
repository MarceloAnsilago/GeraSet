# Modelo de estratégias — schema 1.0

Este pacote define a estratégia sem depender de Flask, HTML, localStorage,
provedor de IA, terminal ou conexão com o MT5. Não altera o setup do usuário,
não cria endpoints, não salva estratégias e não executa testes/negociações.
A interface e a exportação JavaScript atuais permanecem em uso.

## Uso

Na raiz do GeraSet, usando o ambiente Python existente:

```python
import json
from pathlib import Path
from geraset_domain.strategy import StrategySpec, validate_strategy

payload = json.loads(Path('geraset_domain/examples/rsi-v1.json').read_text(encoding='utf-8'))
report = validate_strategy(payload)
print(report.state, report.issues)
if report.strategy is not None:
    normalized = report.strategy.model_dump_json(indent=2)
    restored = StrategySpec.model_validate_json(normalized)
```

`strategy-v1.schema.json` é gerado pelo modelo Pydantic, sem manutenção manual:

```powershell
.\.venv\Scripts\python.exe -m geraset_domain.schema --check
```

Sem `--check`, o comando atualiza o artefato. O JSON Schema descreve a estrutura;
regras entre campos e compatibilidade exigem `validate_strategy()`, não apenas
um validador JSON Schema genérico. Dependência: Pydantic 2.12 ou superior da série 2,
já disponível no ambiente local e declarada nas dependências Flask.

## Estrutura

| Campo | Significado |
|---|---|
| `schema_version` | Versão do formato; apenas `1.0` é aceita nesta implementação |
| `strategy_id`, `revision`, `parent_revision` | Identidade e revisão da estratégia; não são versão do schema nem comprovação de histórico persistido |
| `name`, `magic` | Identificação nativa; o modelo exige Magic explícito |
| `metadata` | Origem, data com fuso, autoria declarada, pedido original e referência do modelo |
| `execution_hint` | Ativo e timeframe base sugeridos; opcionais, não alteram inputs nem vinculam uma execução |
| `operation` | Forex/B3, day/swing, direção e lote |
| `session` | Janela de entradas no relógio do servidor, em passos de cinco minutos |
| `order` | Mercado ou pendente OHLC, candle e espelhamento na venda |
| `indicators` | Até quatro slots identificados por número, com MA, RSI ou ADX e parâmetros próprios |
| `entry_rules`, `exit_rules` | De uma a dez condições no total, preservando sua ordem por finalidade |
| `risk` | SL/TP, unidade dos alvos, breakeven, trailing e stop móvel |
| `optimization` | Intervalos numéricos, de escolhas ou horários, referenciados por caminhos semânticos |

Objetos rejeitam campos desconhecidos. Tipos de indicador, operando, ordem e
alvo são discriminados: por exemplo, um ADX não aceita parâmetros de MA. Slots,
períodos, candles e versões inteiras não aceitam booleanos ou números fracionários.
Números decimais aceitam strings para preservar precisão; a versão 1 limita a
representação a 32 dígitos/12 casas, além dos limites técnicos do contrato.
Objetos são imutáveis, coleções são tuplas e instâncias são revalidadas ao entrar
em `validate_strategy()`. Metadados de origem/autoria são declarações do documento,
não autenticação ou autorização.

### Timeframe, operandos e lados

`execution_hint.base_timeframe` é explícito, como M5, e pertence ao contexto do
teste/gráfico. `indicators[].timeframe` aceita `current` ou um período explícito.
`current` herda a base da execução; a alteração da sugestão de execução não muda
a configuração nativa. Todos os slots usam o ativo da execução.

Operandos: preço/candle, linha de um slot ou constante à direita. Linhas `main`,
`di_plus`, `di_minus`, `upper`, `middle`, `lower` só são aceitas quando compatíveis
com o indicador e sua finalidade. Não há expressões Python, comandos ou fórmulas
livres. `if/and/or` reproduzem a grade atual e sua precedência, sem parênteses
arbitrários. A primeira regra de cada finalidade/lado deve usar `if`.

`side` sempre representa a posição afetada: em entrada, `buy` abre compra;
em saída, `buy` fecha compra. O adaptador converte a saída para o sinal nativo
oposto; o documento semântico não exige que o agente conheça essa inversão.

### Gestão e extensão futura

Percentuais são distâncias relativas ao preço de entrada/abertura, conforme o
recurso do Uni, e não risco sobre o patrimônio. Lote não é dimensionado por risco.
Trailing e stop móvel aceitam somente `distance_policy: fixed`, em pontos ou
percentual. Políticas por indicador são recusadas até existir implementação e
contrato explícitos. Modo desativado mantém valores de rascunho no documento,
mas projeta valores nativos zerados e não permite otimização dessa gestão.

### Otimização

Caminhos usam o número do slot, não a posição no array. Exemplos:

- `indicators.1.period`, `.timeframe`, `.price`, `.method`, `.shift` (quando aplicáveis).
- `indicators.2.lower`, `.middle`, `.upper` para RSI.
- `operation.direction`, `session.entry_start`, `session.entry_end`.
- `order.reference`, `order.candle` para pendentes.
- `risk.stop_loss.distance`, `.candle`, `.measure` quando aplicáveis.
- `risk.take_profit.distance` ou `.multiplier`, conforme o tipo.
- `risk.breakeven.trigger`, `.offset` quando habilitado.
- `risk.trailing.trigger`, `.distance`, `.adjustment_step`; idem para `moving_stop`.

O tipo de intervalo deve corresponder ao parâmetro; caminhos desconhecidos,
repetidos, inativos ou nomes `Inp*` são recusados. `choice` usa os valores
contíguos nativos entre os dois extremos, inclusive intermediários; não é uma
lista de duas escolhas. Horários têm passo cinco. Extremos iguais deixam o
parâmetro fixo e não substituem seu valor independente.

## Validação compartilhada

`uni_mapping.compile_strategy()` produz somente um dicionário de inputs para
conferência. Ele não é o novo gerador público de `.set` e não altera a importação
versão 2 do GeraSet. As ativações live/tester são explicitamente falsas nessa
projeção; contexto, metadados e identificadores de sessão interna não são inputs.

A projeção passa pelo mesmo parser, limites escalares e regras entre campos
que o Bridge. Essas implementações foram extraídas para `uni_presets.py` e
`uni_configuration.py`; os módulos antigos do Bridge são adaptadores que
preservam `BridgeError`, códigos e status. Não há duas cópias Python das regras.
O contrato canônico continua em `mt5_bridge/contracts/uni_inputs.json`; o pacote
lê esse artefato sem importar o serviço MT5. Docker inclui pacote, dependência e
somente esse JSON do Bridge, sem FastAPI, executor ou credenciais locais.

`validate_strategy()` calcula `invalid` ou `structurally_valid` e retorna erros
com caminho/código/mensagem. O relatório inclui hash do contrato e sempre
`financial_state: not_tested`. Limites do símbolo, ticks, stops, margem, histórico
e aceitação da corretora permanecem pendentes. O documento de entrada não aceita
flags de aprovação, resultados ou alegações de validação financeira.

## Evolução e próximos passos

`schema_version` evolui separadamente de `revision`. Salve o JSON normalizado
com UUID, data e defaults, evitando regenerar sua identidade a cada uso. Versões
desconhecidas falham explicitamente; não há migração automática ainda. Quando
surgir outro schema, mantenha o leitor 1.0, preserve o original e registre uma
migração explícita em nova revisão. O hash do contrato identifica os limites
utilizados; ainda não é uma versão/hash do binário Uni executado.

Faltam persistência de revisões, autoria autenticada, aprovação vinculada ao hash,
adaptador da interface, gerador Python público e integração do agente. Essas
camadas usarão este modelo; não foram introduzidas nesta etapa. A pendência de
execução real no MT5 e o relatório existente da etapa 5 permanecem inalterados.
