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
