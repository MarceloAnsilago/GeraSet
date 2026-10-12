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
Nesta primeira etapa, somente `InpName` e `InpMagic` são aplicados ao UniEA.
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
   Os demais inputs não estão mapeados nesta etapa; confira os valores existentes.

O carregamento ocorre pelos inputs nativos do MT5, não pelo leitor binário
legado `GuiLoadSet`. Não é necessário recompilar o Uni para esta etapa.
Arquivos JSON `.set` exportados antes desta integração precisam ser exportados
novamente. A nova faixa do hash pode alterar o Magic exibido em rascunhos antigos.

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
