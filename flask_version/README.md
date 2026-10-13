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
iniciar uma execução para conferir a importação. Horários, indicadores e gestão
ainda não são aplicados pelo arquivo nesta etapa.

## Sinal

Cada condição herda Entrada ou Saída de “Usar como” dos indicadores selecionados.
Condições somente com preços são de Entrada. Misturar indicadores de Entrada e
Saída na mesma condição gera um erro. A direção é definida na condição.
Compra e venda aplica a mesma regra
às duas direções, sem inverter a comparação. Condições são agrupadas por
finalidade e direção: a primeira usa Se e as seguintes E ou Ou, com prioridade
de E sobre Ou. O resumo apresenta os grupos com parênteses.

Da (DE) aceita Valor fixo na escala de A, por exemplo RSI < 30. ADX oferece
também +DI e −DI. O candle da referência não se aplica a valor fixo.
Cruzar e fechar exige candles fechados; Vela atual ainda pode variar.

Distância é tolerância absoluta para Toque, Igual que e Diferente de, e
afastamento mínimo nas demais comparações. Porcentagem usa o valor absoluto
da referência como base. Pontos se aplicam apenas a preços. Para RSI/ADX,
use distância N.usar ou porcentagem. Zero representa tolerância/afastamento
zero; N.usar exige distância zero.

Condições incompletas ou inválidas impedem a exportação. Os novos campos são
anexados à ordem de armazenamento para preservar os campos dos setups salvos.
O antigo campo Finalidade é removido dos setups salvos, preservando direção e
valor fixo. Estas regras descrevem a configuração exportada; o projeto
não executa sinais e o robô integrado precisa implementar essa interpretação.
