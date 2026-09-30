import streamlit as st
from streamlit_navigation_bar import st_navbar


PAGES = ["Pagina Inicial", "Sets", "Relatorios", "Configuracoes"]


def render_navbar() -> str:
    styles = {
        "nav": {
            "background-color": "#0f172a",
            "height": "4rem",
            "padding": "0 2rem",
        },
        "div": {
            "max-width": "1180px",
            "margin": "0 auto",
        },
        "span": {
            "color": "#e5e7eb",
            "font-size": "0.95rem",
            "font-weight": "600",
        },
        "active": {
            "color": "#ffffff",
            "font-weight": "700",
        },
        "hover": {
            "color": "#ffffff",
            "background-color": "#1e293b",
        },
    }

    page = st_navbar(
        PAGES,
        selected="Pagina Inicial",
        styles=styles,
        options={"show_menu": True, "show_sidebar": False, "use_padding": True},
    )

    return page or "Pagina Inicial"


def render_home() -> None:
    st.title("GeraSet")
    st.caption("Organize, acompanhe e gere seus sets em um painel simples.")

    col_sets, col_reports = st.columns(2, gap="large")

    with col_sets:
        with st.container(border=True):
            st.subheader("Gerar sets")
            st.write("Crie e organize conjuntos de dados para acompanhar suas rotinas.")
            st.metric("Sets ativos", "12", "+3")
            st.button("Novo set", type="primary", width="stretch")

    with col_reports:
        with st.container(border=True):
            st.subheader("Acompanhar resultados")
            st.write("Veja indicadores, pendencias e resumos dos seus sets cadastrados.")
            st.metric("Itens gerados", "248", "+31")
            st.button("Ver relatorios", width="stretch")


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

    if selected_page == "Pagina Inicial":
        render_home()
    elif selected_page == "Sets":
        render_sets()
    elif selected_page == "Relatorios":
        render_reports()
    elif selected_page == "Configuracoes":
        render_settings()


if __name__ == "__main__":
    main()
