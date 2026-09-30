import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="GeraSet",
    page_icon="GS",
    layout="wide",
)

st.title("GeraSet")
st.caption("Projeto Streamlit pronto para evoluir.")

with st.sidebar:
    st.header("Configuracao")
    nome = st.text_input("Nome do conjunto", value="Meu primeiro set")
    quantidade = st.number_input("Quantidade de itens", min_value=1, max_value=100, value=5)

st.subheader(nome)

dados = pd.DataFrame(
    {
        "Item": [f"Item {indice}" for indice in range(1, quantidade + 1)],
        "Status": ["Pendente"] * quantidade,
    }
)

st.dataframe(dados, use_container_width=True, hide_index=True)

if st.button("Gerar resumo"):
    st.success(f"{quantidade} itens criados para {nome}.")
