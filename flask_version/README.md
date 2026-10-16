# GeraSet Flask

Aplicação Flask do GeraSet.

## Rodar

```powershell
cd D:\driver\Documentos\GeraSet
.\.venv\Scripts\pip install -r .\flask_version\requirements-flask.txt
.\.venv\Scripts\python .\flask_version\app.py
```

Depois abra:

```text
http://localhost:5000
```


## Exportar set

O card **Alvos** exporta unidade, stop fixo, multiplicador/candle/tamanho do
stop e o modo de take. Distância fixa usa `InpTakeMode=1` e `InpTakeProfit`;
vezes o stop usa `InpTakeMode=0` e `InpTakeStopMultiplier`. Zero desliga o
take do modo escolhido. Apenas o intervalo do modo ativo é exportado.
Atualize com Ctrl+F5, reexporte o set e carregue no Uni recompilado para
aplicar esses campos. Rascunhos salvos mantêm a ordem dos controles.

Em **Revisão e Sets**, clique em **Exportar set**. No Chrome ou Edge,
o diálogo **Salvar como** permite escolher a pasta e o nome do arquivo `.set`.
O app confirma o salvamento somente depois de concluir a gravação.
Cancelar o diálogo cancela a exportação.

Nos navegadores sem suporte ao seletor de salvamento, o app inicia um download.
Para escolher a pasta nesse caso, configure o navegador para perguntar onde
salvar cada download.

O arquivo usa o formato nativo de parâmetros do MT5 (UTF-16LE com BOM).
São aplicados Identificação (`InpName`, `InpMagic`) e Mercado e operação
(`InpMarket`, `InpTradeMode`, `InpStrategyTimeframe`, `InpLot`, `InpDirection`).
O card Horários também é aplicado: `InpEntryStart` e `InpEntryEnd`.
O JSON do GeraSet, versão 1, permanece em linhas de comentário (`; `), com
os parâmetros e intervalos das três etapas, inclusive opções desativadas.
Esses comentários não configuram indicadores, gestão ou outros inputs do Uni.
Salvar novamente pelo MT5 pode descartar os comentários; preserve o original.

O nome deve ter de 1 a 48 unidades UTF-16, sem caracteres de controle ou `|`.
Nomes numéricos fornecem o Magic diretamente (1 a 2147483647).
Outros nomes geram um Magic determinístico nessa faixa; nomes iguais geram
o mesmo Magic e o hash não garante exclusividade entre nomes diferentes.
O Flask não consulta reservas ou histórico de ordens do terminal.

### Testar a identificação no Uni

1. Atualize o navegador com Ctrl+F5 e defina o nome em Identificação.
2. Anote o Magic mostrado e exporte em **Revisão e Sets**.
3. Nas propriedades do UniEA no MT5, abra **Parâmetros de entrada → Carregar**
   e selecione o `.set` exportado.
4. Confira Nome do setup (`InpName`) e Magic Number (`InpMagic`) contra o Flask.
   Confira também os valores do card Mercado e operação conforme abaixo.

O carregamento ocorre pelos inputs nativos do MT5, não pelo leitor binário
legado `GuiLoadSet`. Não é necessário recompilar o Uni para esta etapa.
Arquivos JSON `.set` exportados antes desta integração precisam ser exportados
novamente. A nova faixa do hash pode alterar o Magic exibido em rascunhos antigos.

### Mercado e operação: parâmetros e otimização

| Campo | Input Uni | Otimização |
| --- | --- | --- |
| Mercado | `InpMarket` (Forex=0, B3=1) | Fixo |
| Modalidade | `InpTradeMode` (Day trade=0, Swing trade=1) | Fixo |
| Timeframe | `InpStrategyTimeframe` (enum do Uni) | Iniciar/Terminar |
| Lote | `InpLot` | Fixo |
| Direção | `InpDirection` (Compra e venda=0, Somente compra=1, Somente venda=2) | Iniciar/Terminar |

Os valores de Parâmetros são exportados na coluna Valor, independentemente
da aba visível. Na aba Otimizar, limites diferentes ativam a marcação `Y` do
respectivo input; limites iguais exportam `N` e mantêm o Valor fixo.
Intervalos invertidos são ordenados antes da exportação. O passo dos enums é 1.
Tempo corrente aparece primeiro no intervalo de Timeframe, acompanhando o
enum do Uni (valor 0). Os códigos H1=16385, H4=16388 etc. são preservados.
Os controles mantêm a ordem de armazenamento dos rascunhos anteriores.

O lote aceita ponto ou vírgula decimal e deve ser maior que zero; os limites
e o passo específicos do ativo continuam sendo validados pelo Uni no terminal.

Para conferir, escolha B3, Swing trade, H4, lote 1 e Somente venda. Em Otimizar,
escolha Timeframe M30 até H4 e Direção Compra e venda até Somente venda.
Exporte novamente e carregue nos inputs do **Testador de Estratégias**:
confira os cinco Valores, os dois intervalos e as duas marcações de otimização.
Repita com limites iguais: as marcações devem ficar desativadas. Não é preciso
iniciar uma execução para conferir a importação. Gestão e demais regras
ainda não são aplicadas pelo arquivo nesta etapa.

### Horários: parâmetros e otimização

Início entradas mapeia para `InpEntryStart` e Encerramento entradas para
`InpEntryEnd`. O Flask apresenta HH:MM; o Uni recebe minutos desde 00:00 no
horário do servidor da corretora (09:30 = 570, 17:00 = 1020).
São aceitos 00:00 a 23:55, em passos de 5 minutos. Os valores fixos devem ser
diferentes; início maior que encerramento representa uma janela noturna.

Cada intervalo da aba Otimizar usa passo 5. Limites diferentes exportam `Y`;
iguais exportam `N`, preservando o valor da aba Parâmetros. Limites invertidos
da otimização são ordenados. Se os intervalos produzirem uma combinação com
início igual ao encerramento, o Uni rejeitará essa combinação na inicialização.

Exemplo para conferir no Testador: início 09:30, encerramento 17:00, otimização
do início de 09:00 a 10:00 e do encerramento de 16:00 a 18:00:

```text
InpEntryStart=570||540||5||600||Y
InpEntryEnd=1020||960||5||1080||Y
```

Atualize com Ctrl+F5 e exporte um arquivo novo. Recompile o Uni para visualizar
o grupo **Horários** atualizado. O encerramento de posições continua seguindo
a modalidade; este card define a janela de entradas.

## Sinal

Cada condição herda Entrada ou Saída de “Usar como” dos indicadores selecionados.
Condições somente com preços são de Entrada. Misturar indicadores de Entrada e
Saída na mesma condição gera um erro. Sinal normal define Compra ou Venda por
condição; Sentido oferece Normal e Inverter. Inverter troca o resultado, sem
alterar a comparação. Entrada/Compra abre compra; Entrada/Venda abre venda.
Saída/Compra fecha vendas; Saída/Venda fecha compras, sem abrir posição oposta.
O resumo apresenta essa ação resultante. Condições ativas sem Sinal normal
impedem a exportação; rascunhos antigos exigem escolher esse novo campo.
Os campos novos são anexados ao armazenamento, preservando as seleções antigas.
Rascunhos com as antigas opções de Direção assumem Normal nesse campo.
Condições são agrupadas por
finalidade e sinal resultante: a primeira usa Se e as seguintes E ou Ou, com prioridade
de E sobre Ou. O resumo apresenta os grupos com parênteses.

Da (DE) aceita Valor fixo na escala de A, por exemplo RSI < 30. ADX oferece
também +DI e −DI. RSI oferece sua linha e os níveis superior, médio e inferior
nos dois combos. Os níveis padrão são 70/50/30, ajustáveis nos parâmetros e
na otimização de cada indicador. O candle não se aplica aos níveis nem ao
valor fixo; uma referência constante não transforma vela fechada em sinal por tick.
O .set usa InpRsiEntryUpper/Middle/Lower e InpRsiExitUpper/Middle/Lower. As fontes 22..33 representam
superior/médio/inferior de cada slot, preservando as fontes 0..21 anteriores.
Os valores devem respeitar 0 <= inferior < médio < superior <= 100;
combinações inválidas na otimização são rejeitadas pelo Uni.
Cruzar e fechar exige candles fechados; Vela atual ainda pode variar.

Distância é tolerância absoluta para Toque, Igual que e Diferente de, e
afastamento mínimo nas demais comparações. Porcentagem usa o valor absoluto
da referência como base. Pontos se aplicam apenas a preços. Para RSI/ADX,
use distância N.usar ou porcentagem. Zero representa tolerância/afastamento
zero; N.usar exige distância zero.

Condições incompletas ou inválidas impedem a exportação. Os novos campos são
anexados à ordem de armazenamento para preservar os campos dos setups salvos.
O antigo campo Finalidade é removido dos setups salvos, preservando direção e
valor fixo. O Flask exporta os quatro indicadores e as cinco condições para
o avaliador `UniSignals.mqh` do Uni. Os campos antigos de inclinação e ADX mínimo ficam ocultos. Os níveis
RSI são referências selecionáveis; não geram regras automáticas.

### Execução integrada no Uni

Os slots 1 a 4 selecionam tipo e finalidade. MA mantém quatro configurações
por slot; RSI e ADX possuem grupos Entry/Exit independentes, incluindo seus
intervalos de otimização. O Flask separa visualmente os slots dos parâmetros
e exporta cada configuração ao grupo correspondente. Sinais e buffers continuam
endereçados pelo slot. Apenas MA permite repetir a mesma finalidade.
Arquivos .set anteriores com InpIndicatorNRsi/Adx devem ser reexportados pelo
Flask para usar os novos nomes; os valores salvos no navegador são preservados. Os buffers A/Da e candles são gravados nos inputs
`InpSignal1` a `InpSignal5`; condições vazias limpam os respectivos inputs.
Os novos inputs `InpIndicator1Exit` a `InpIndicator4Exit` preservam Entrada/Saída.

Grupos com Vela atual são avaliados a cada tick; grupos somente com candles
fechados, uma vez por nova vela. E tem prioridade sobre Ou dentro de cada grupo
de finalidade e lado resultante. Toque aceita a distância definida e detecta
passagem pelo nível entre ticks. Um sinal intrabar contínuo não repete ordens:
precisa ficar falso antes de um novo disparo. Cruzar e fechar exige velas fechadas.

Saída Compra fecha vendas e Saída Venda fecha compras, somente no ativo/Magic
configurados. Saídas têm prioridade e não abrem uma posição contrária no mesmo
tick. Também cancelam pendentes do lado encerrado e funcionam com entradas
pausadas. Entradas opostas simultâneas são ignoradas. Ao ativar, grupos com
Vela atual já podem disparar no próximo tick; os grupos somente de velas fechadas
aguardam uma nova vela.

Atualize com Ctrl+F5, recompile o Uni e exporte um novo arquivo. No Testador,
habilite `InpTesterAutoStart` para testar entradas e use ticks reais para validar
Toque/Vela atual. Confira os parâmetros de gestão no Uni, pois ainda não são
exportados. Bollinger ainda não está entre os tipos disponíveis: MA, RSI e ADX.


### Card Ordem integrado ao Uni

O card Ordem exporta InpOrderMode (0 mercado, 1 pendente),
InpPendingReference (0 maxima, 1 minima, 2 abertura, 3 fechamento) e
InpPendingCandle (1 ultima vela fechada, ate 100000), no periodo da estrategia.
O Uni tem um grupo Ordem com os mesmos campos. Stop/Limit e escolhido pelo
motor conforme lado do sinal e posicao do preco OHLC em relacao ao mercado.

A referencia e a vela possuem intervalos de otimizacao independentes do valor
fixo. Vela com 0/0/0 desativa a otimizacao; intervalos ativos exigem inteiros
positivos e fim >= inicio. A mercado desativa os intervalos da pendente.
Setups salvos no navegador mantem sua ordem de campos; reexporte o .set para
incluir estes inputs. Validacao: testes de exportacao e compilacao; envio de
ordens deve ser verificado no testador.
