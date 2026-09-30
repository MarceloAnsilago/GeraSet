import streamlit as st


PAGES = {
    "inicio": "Pagina Inicial",
    "sets": "Sets",
    "relatorios": "Relatorios",
    "configuracoes": "Configuracoes",
}


def render_navbar() -> str:
    current_page = st.query_params.get("page", "inicio")
    if current_page not in PAGES:
        current_page = "inicio"

    nav_items = "".join(
        f'<a class="nav-link {"active" if slug == current_page else ""}" href="?page={slug}">{label}</a>'
        for slug, label in PAGES.items()
    )

    st.html(
        f"""
<style>
.block-container {{
    padding-top: 0;
}}

.geraset-navbar {{
    align-items: center;
    background: #0f172a;
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    margin: 0 calc(50% - 50vw) 3rem;
    min-height: 4rem;
    padding: 0 2rem;
}}

.geraset-navbar-inner {{
    align-items: center;
    display: flex;
    gap: 0.5rem;
    max-width: 1180px;
    width: 100%;
}}

.brand {{
    color: #ffffff;
    font-size: 1rem;
    font-weight: 800;
    margin-right: 1.25rem;
}}

.nav-link {{
    border-radius: 0.5rem;
    color: #dbe4f0 !important;
    font-weight: 700;
    padding: 0.65rem 0.95rem;
    text-decoration: none !important;
}}

.nav-link:hover {{
    background: #1e293b;
    color: #ffffff !important;
}}

.nav-link.active {{
    background: #ffffff;
    color: #0f172a !important;
}}
</style>

<nav class="geraset-navbar">
    <div class="geraset-navbar-inner">
        <span class="brand">GeraSet</span>
        {nav_items}
    </div>
</nav>
"""
    )

    return PAGES[current_page]


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
