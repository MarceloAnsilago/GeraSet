# Contrato dos inputs do Uni — conferência de 22/10/2026

`uni_inputs.json` descreve os 108 inputs do `UniEA.mq5`: nome, tipo MQL5,
tipo de transporte, padrão nativo, enum e possibilidade de otimização.
Inclui limites escalares e unidades quando aplicáveis. Não é um catálogo
de estratégias nem certificação de funcionamento no MT5.

## Conferência e atualização

Na raiz do GeraSet, com o caminho do repositório Uni disponível:

```powershell
.\.venv\Scripts\python.exe -m mt5_bridge.contracts.sync_uni_inputs --uni-root 'CAMINHO_DO_UNI' --check
```

O comando só lê e retorna código diferente de zero quando houver divergência.
Sem `--check`, regenera o JSON. Nomes, tipos, enums e padrões vêm das declarações
MQL5. Limites semânticos e unidades são mantidos explicitamente no extrator,
conferidos contra `GuiSetupState`, `GuiRulesState`, `GuiManagementState`,
`MyMA`, `MyRSI`, `MyADX` e `UniSignalHistogram`. Mudanças nesses validadores
exigem revisão desses limites; a extração não interpreta funções MQL5.

`presets.parse_set()` usa esse contrato para validar o valor fixo e os limites
dos intervalos Y. O passo é um incremento, não outro valor do parâmetro:
por exemplo, um passo de 1 é válido para o Magic, independentemente do Magic
fixo. Horários e seus passos ativos devem ser múltiplos de cinco.
Colunas inativas N são preservadas por compatibilidade com presets nativos.

## Correspondência e diferenças intencionais

| Área | Contrato verificado |
|---|---|
| Mercado | Forex=0; B3=1 |
| Modalidade | Day=0; Swing=1 |
| Direção | Ambas=0; compra=1; venda=2 |
| Tipo de indicador | Não usar=-1; MA=0; RSI=1; ADX=2 |
| Finalidade | Entrada=0; saída=1 |
| Preço aplicado | Close=1 até Weighted=7 |
| Método MA | SMA=0; EMA=1; SMMA=2; LWMA=3 |
| Timeframe do slot | Índices 0..21; corrente=0; H1=12; MN1=21 |
| Timeframe base/ativo | Contexto do gráfico/testador; não há `InpStrategyTimeframe` nem input de símbolo |
| Pendente | Mercado=0; pendente=1; referência máxima=0, mínima=1, abertura=2, fechamento=3 |
| Horário | Minutos do servidor, 0..1435, passo 5 |
| Alvos | Pontos=0 ou percentual do preço de entrada=1; percentual não significa risco sobre patrimônio |
| Stop | Distância+candle=0; fixo=1; candle fechado 1..3 |
| Take | Nativo -1 infere presets antigos; GeraSet emite 0=múltiplo ou 1=fixo explicitamente |
| Gestão | Desativado=0; pontos=1; percentual do preço de abertura=2 |
| Lote | Positivo; mínimo, máximo e passo dependem do símbolo e são conferidos pelo Uni |
| MA/RSI/ADX | Período 1..100000; shift MA -100000..100000; níveis RSI 0..100 |
| Distâncias/multiplicadores | 0..100000000; relações entre campos são regras adicionais |
| Histograma/fonte | Histórico 1..5000; fonte é normalizada pelo Uni a 10..20 |
| Cores | Padrões MQL5 convertidos para inteiro BGR; sem mudança de cores |

MA tem parâmetros por slot; RSI e ADX têm grupos por finalidade. Os padrões
nativos são registrados no JSON. Os defaults da interface foram conferidos:
MA 20/EMA/Close/shift 0; RSI 14/Close/30/50/70; ADX 14; Forex/Day/lote 0.01;
horários 00:00 e 23:55; stop+candle com multiplicador 1 e take múltiplo 2.
O take automático nativo (-1) e o explícito da interface (0) são compatíveis
com esses valores; não devem ser igualados removendo compatibilidade antiga.

## Inputs não controlados pelo exportador atual

- Trailing e stop móvel: existem no Uni e na interface, sem emissão nativa pelo
  exportador. Integração pendente, não corrigida por este contrato.
- `InpCandleFilter`: input do Uni não emitido atualmente pelo gerador.
- `InpAutoStart`: não emitido; padrão nativo false. O Bridge força false.
- `InpTesterAutoStart`: opcional na exportação; Bridge define conforme o job.
- Marcadores e separadores: não configuráveis no exportador atual; padrões nativos.
- `InpCurveSession`: interno; constará no contrato para rastreabilidade, mas é
  recusado em presets recebidos. Somente o executor o injeta na otimização.
- O gerador fixa `InpHistogramasBarras=300` e exporta os seletores de painel/histogramas.

Não presumir que campos guardados nos comentários JSON alterem os inputs.
Inputs omitidos não são preenchidos automaticamente por este contrato.

## Limites desta etapa

Verificação de escalares não substitui relações entre campos (RSI inferior <
médio < superior, take dependente de stop, janela com limites diferentes,
gestão habilitada com valores positivos), semântica completa dos sinais,
limites do ativo ou testes de execução na corretora. Essas validações continuam
no Uni e parcialmente no navegador, com consolidação no servidor pendente.

Não foram alterados o motor MQL5, o formato dos sinais, os valores dos enums,
os inputs emitidos nem o metadado de importação versão 2. O `.ex5` não precisa
ser recompilado por esta mudança. Presets fora dos limites agora são recusados
pelo Bridge antes de lançar o terminal.
