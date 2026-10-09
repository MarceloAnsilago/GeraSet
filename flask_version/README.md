# GeraSet Flask

Versão Flask separada do app Streamlit.

## Rodar

```powershell
cd C:\Users\76395499220\Desktop\prog\GeraSet
.\.venv\Scripts\pip install -r .\flask_version\requirements-flask.txt
.\.venv\Scripts\python .\flask_version\app.py
```

Depois abra:

```text
http://localhost:5000
```

Para remover esta versão, apague somente a pasta `flask_version`.

## Exportar set

Em **Revisão e Sets**, clique em **Exportar set**. No Chrome ou Edge,
o diálogo **Salvar como** permite escolher a pasta e o nome do arquivo `.set`.
O app confirma o salvamento somente depois de concluir a gravação.
Cancelar o diálogo cancela a exportação.

Nos navegadores sem suporte ao seletor de salvamento, o app inicia um download.
Para escolher a pasta nesse caso, configure o navegador para perguntar onde
salvar cada download.

O arquivo usa o formato do GeraSet (JSON UTF-8, versão 1) e inclui o nome,
o magic number, os parâmetros e os intervalos de otimização das três etapas,
inclusive opções desativadas. A integração com um robô do MetaTrader exige
o mapeamento dos parâmetros desse robô.

## Sinal

Cada condição define sua finalidade (Entrada ou Saída) e direção. Esses campos
prevalecem sobre “Usar como” do indicador. Compra e venda aplica a mesma regra
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
Setups antigos recebem Entrada e Compra e venda como padrões; confira esses
campos ao reabrir. Estas regras descrevem a configuração exportada; o projeto
não executa sinais e o robô integrado precisa implementar essa interpretação.
