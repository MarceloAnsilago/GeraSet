# Serviços de configuração, validação e exportação

## Fluxo compartilhado

```text
JSON v1.0 ── configure_strategy ── StrategySpec validada
                                     │
                               compile_strategy
                                     │
                            parser/regras existentes
                                     │
                               export_strategy ── .set

Snapshot da interface ── exportador JS atual ── .set v2
                                     │
                         strategy_from_inputs / v1.0
                                     │
                         mesmo fluxo Python acima
                                     │
                 compare_legacy_set: inputs + otimizações
                                     │
             export_preserving_legacy: envelope v2 preservado
```

Não há chamada a MT5, executor, transporte Bridge, SDK de IA ou rede nos serviços
do domínio. As regras escalares e entre campos continuam centralizadas nos módulos
compartilhados existentes; o adaptador reverso não implementa outro motor de regras.
O registro de parâmetros otimizáveis vem de `compile_strategy(include_bindings=True)`.

## Funções públicas

```python
from geraset_domain.services import (
    configure_strategy, to_uni_inputs, export_strategy,
    configure_from_set, compare_legacy_set, export_preserving_legacy,
)

report = configure_strategy(strategy_json)  # dict, JSON string ou StrategySpec
if not report.valid:
    print(report.as_dict()['errors'])
else:
    artifact = export_strategy(report.strategy)
    print(artifact.filename, artifact.sha256, artifact.warnings)
    # artifact.contents são bytes UTF-16LE com BOM e CRLF; a função não grava disco.
```

`to_uni_inputs()` retorna o relatório e o dicionário nativo. Campos de controle
real não são aceitos: `InpAutoStart` permanece false. `tester_auto_start` é uma
opção separada, explícita e estritamente booleana, exclusiva do Testador.
Painel, histogramas e barras agora fazem parte da projeção do modelo.

Exportações puras incluem um comentário JSON `format: geraset-strategy`, versão 1,
com o documento normalizado e opções de exportação. `configure_from_set()` verifica
esse documento contra os inputs antes de restaurar identidade/revisão/metadados.
Nenhum comentário é executado. Normalize a estratégia uma vez antes de exportações
repetidas: UUID e data são criados quando não fornecidos.

## Origem na interface e compatibilidade

```python
comparison, independent_python_artifact = compare_legacy_set(original_bytes)
if comparison['equivalent']:
    artifact = export_preserving_legacy(
        comparison['configuration']['strategy'], original_bytes,
        comparison['export_options'],
    )
    assert artifact.contents == original_bytes
```

Os dois arquivos canônicos não são exigidos byte a byte iguais: o novo possui
metadados v1.0 e formatação nativa determinística, enquanto o antigo contém o
rascunho da interface v2. A comparação verifica todos os inputs, valores fixos,
posições de sinais e início/passo/fim dos intervalos Y. Numericamente `1` e `1.00`
ou booleanos nativos equivalentes são iguais; colunas N não são valores ativos.
O take AUTO legado fixo é comparado ao modo resolvido. Parâmetros omitidos só
equivalem quando seu valor é o default declarado no contrato.

Depois da equivalência, o envelope original pode ser preservado integralmente:
metadados, nomes de campos antigos, ajustes inativos, colunas N, encoding e bytes.
Isso não substitui o compilador: uma divergência bloqueia esse caminho. Mudanças
de estratégia devem usar uma nova exportação ou novo snapshot, não reaproveitar
metadados divergentes. Configurações nativas conhecidas mas ainda não modeladas
com valores não padrão são informadas, nunca removidas silenciosamente.

`configure_from_set()` converte também presets nativos reconhecidos, retornando
as opções de exportação separadamente em `report.export_options`; preserve-as
ao reexportar. Para manter o rascunho v2, retenha também os bytes originais.
Arquivos anteriores sem grupos de trailing/móvel herdam seus defaults desativados.

## Interface e HTTP

O botão **Exportar set** continua usando o exportador anterior e o seletor de
arquivo existente. O novo **Exportar com Python (comparar)** é opt-in: captura
o mesmo snapshot, compara os caminhos no servidor e só solicita download após
equivalência. Divergência ou indisponibilidade do serviço não provoca fallback
silencioso nem desabilita o botão anterior. O novo botão usa download do navegador.
Não altera localStorage, setup, atalhos do Testador ou importação existentes.

| Rota | Operação |
|---|---|
| `GET /strategies/session` | Token CSRF da sessão, independente do Bridge |
| `GET /strategies/schema` | JSON Schema v1.0 atual |
| `POST /strategies/validate` | Corpo: estratégia v1.0; retorna normalização, erros e avisos |
| `POST /strategies/export` | Corpo: `{strategy, options?, legacy_set_base64?}`; retorna arquivo |
| `POST /strategies/compare` | Corpo: `{set_base64}`; retorna equivalência, diferenças e artefato Python independente |

POSTs exigem `X-GeraSet-Strategy-CSRF`. O modo remoto continua sob a autenticação
global existente; não foi criada autenticação para um agente. As respostas não
são cacheadas. Limites de corpo do Flask e de preset continuam ativos. Erros de
validação retornam 422; falhas de CSRF retornam 403. Em contexto de futuro agente
no servidor, as funções Python podem ser chamadas diretamente sem usar HTTP.

## Erros e avisos

- `structural`: JSON, versão, tipos, campos desconhecidos ou intervalo mal formado.
- `uni`: compatibilidade técnica, fontes, unidades, dependências ou parâmetro perdido.
- Avisos `financial`: ausência de SL/TP, percentuais de preço e ausência de avaliação financeira.
- Aviso `operational`: volume, margem, tick, stops, histórico e corretora ainda pendentes.

Avisos não são tratados como erros técnicos. Todos os relatórios permanecem em
`financial_state: not_tested`; gerar arquivo não aprova a estratégia financeiramente.

## Limites deliberados da migração

- O gerador antigo não foi eliminado nem substituído automaticamente.
- O modelo exige ao menos uma condição. Rascunhos sem sinais continuam no botão
  antigo; não são convertidos artificialmente em estratégias executáveis.
- Importação pela interface continua lendo seu formato v2. O novo botão preserva
  esse envelope e permite o mesmo retorno à interface. Um arquivo canônico puro
  v1.0 pode ser carregado no Uni ou por `configure_from_set()`; carregar esse
  formato puro diretamente no importador visual ainda não foi acrescentado.
- Otimizações fora do subconjunto atual (por exemplo, trocar tipo/finalidade de
  indicador ou stride não contíguo de enums) são recusadas explicitamente.
- Os testes de equivalência usam o serializer JS real com snapshots controlados,
  não automatização do navegador nem execução real do MT5. A etapa 5 continua pendente.
- Não há agente instalado, aprovação persistida, implantação no Fly.io ou mudança no Uni.
