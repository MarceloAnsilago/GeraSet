import pandas as pd
import streamlit as st
from streamlit_navigation_bar import st_navbar


PAGES = ["Inicio", "Sets", "Relatorios", "Configuracoes"]


def render_navbar() -> str:
    styles = {
        "nav": {
            "background-color": "#0f172a",
            "height": "4rem",
            "justify-content": "center",
            "padding": "0 1.5rem",
        },
        "span": {
            "color": "#e5e7eb",
            "font-size": "0.95rem",
            "font-weight": "600",
        },
        "active": {
            "color": "#38bdf8",
            "font-weight": "700",
        },
        "hover": {
            "color": "#ffffff",
            "background-color": "#1e293b",
        },
    }

    return st_navbar(
        PAGES,
        selected="Inicio",
        styles=styles,
        options={"show_menu": True, "show_sidebar": False, "use_padding": False},
    )


def render_home() -> None:
    st.title("GeraSet")
    st.caption("Organize, acompanhe e gere seus sets em um painel simples.")

    col_create, col_review = st.columns([2, 1])
    with col_create:
        st.subheader("Novo set")
        nome = st.text_input("Nome do set", value="Meu primeiro set")
        quantidade = st.number_input("Quantidade de itens", min_value=1, max_value=100, value=5)
        categoria = st.selectbox("Categoria", ["Geral", "Operacional", "Relatorio", "Cadastro"])

        if st.button("Gerar set", type="primary"):
            st.success(f"{quantidade} itens criados para {nome} em {categoria}.")

    with col_review:
        st.subheader("Resumo")
        st.metric("Sets ativos", "12", "+3")
        st.metric("Itens gerados", "248", "+31")
        st.metric("Pendencias", "7", "-2")

    st.divider()

    st.subheader("Sets recentes")
    dados = pd.DataFrame(
        {
            "Set": ["Entrada de veiculos", "Banco de horas", "Receitas", "Fichas inativas"],
            "Categoria": ["Operacional", "Relatorio", "Geral", "Cadastro"],
            "Itens": [42, 18, 64, 31],
            "Status": ["Ativo", "Em revisao", "Ativo", "Pendente"],
        }
    )
    st.dataframe(dados, use_container_width=True, hide_index=True)


def render_sets() -> None:
    st.title("Sets")
    st.info("Aqui ficara a lista completa de sets cadastrados.")


def render_reports() -> None:
    st.title("Relatorios")
    st.info("Aqui ficarao os indicadores e exportacoes do GeraSet.")


def render_settings() -> None:
    st.title("Configuracoes")
    st.info("Aqui ficarao as preferencias do projeto.")


def main() -> None:
    st.set_page_config(
        page_title="GeraSet",
        page_icon="GS",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    selected_page = render_navbar()

    if selected_page == "Inicio":
        render_home()
    elif selected_page == "Sets":
        render_sets()
    elif selected_page == "Relatorios":
        render_reports()
    elif selected_page == "Configuracoes":
        render_settings()


if __name__ == "__main__":
    main()
