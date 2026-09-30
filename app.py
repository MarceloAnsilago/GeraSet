import streamlit as st


PAGES = {
    "inicio": "Pagina Inicial",
    "indicadores": "Indicadores",
    "sets": "Sets",
    "relatorios": "Relatorios",
    "configuracoes": "Configuracoes",
}

TIMEFRAMES = [
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M10",
    "M12",
    "M15",
    "M20",
    "M30",
    "H1",
    "H2",
    "H3",
    "H4",
    "H6",
    "H8",
    "H12",
    "D1",
    "W1",
    "MN1",
    "Tempo corrente",
]
TIMES = [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in range(0, 60, 5)]


def render_navbar() -> str:
    current_page = st.query_params.get("page", "inicio")
    if current_page not in PAGES:
        current_page = "inicio"

    nav_items = "".join(
        f'<a class="nav-link {"active" if slug == current_page else ""}" href="?page={slug}" target="_parent">{label}</a>'
        for slug, label in PAGES.items()
    )

    st.markdown(
        f"""<style>
.block-container {{
    padding-top: 0;
}}

header[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[class="stDeployButton"] {{
    display: none;
}}

.geraset-navbar {{
    align-items: center;
    background: #0f172a;
    box-sizing: border-box;
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    margin: 0 calc(50% - 50vw) 3rem;
    min-height: 64px;
    padding: 0 2rem;
    width: 100vw;
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
<nav class="geraset-navbar"><div class="geraset-navbar-inner"><span class="brand">GeraSet</span>{nav_items}</div></nav>""",
        unsafe_allow_html=True,
    )

    return PAGES[current_page]


def render_home() -> None:
    st.title("GeraSet")
    st.caption("Primeira etapa do Canvas UniversalEa, recriada em Streamlit.")

    col_identity, col_market, col_schedule = st.columns(3, gap="medium")

    with col_identity:
        with st.container(border=True):
            st.subheader("Identificação")
            st.text_input("Nome do setup (opcional)", value="Meu setup", max_chars=48)
            st.text_input("Magic Number (automático)", value="1", disabled=True)
            st.caption("Magic Number identifica as ordens deste setup.")

            action_left, action_right = st.columns(2)
            with action_left:
                st.button("Salvar set", width="stretch")
            with action_right:
                st.button("Carregar set", width="stretch")

    with col_market:
        with st.container(border=True):
            st.subheader("Mercado e operação")
            market_col, mode_col = st.columns(2)
            with market_col:
                st.selectbox("Mercado", ["Forex", "B3"])
            with mode_col:
                st.selectbox("Modalidade", ["Day trade", "Swing trade"])

            timeframe_col, lot_col = st.columns(2)
            with timeframe_col:
                st.selectbox("Timeframe", TIMEFRAMES, index=len(TIMEFRAMES) - 1)
            with lot_col:
                st.text_input("Lote", value="0.01")

            st.selectbox("Direção permitida", ["Compra e venda", "Somente compra", "Somente venda"])
            st.caption("Lote: mín. 0.01 · Passo 0.01")

    with col_schedule:
        with st.container(border=True):
            st.subheader("Horários")
            start_col, end_col = st.columns(2)
            with start_col:
                st.selectbox("Início entradas", TIMES, index=0)
            with end_col:
                st.selectbox("Encerramento entradas", TIMES, index=len(TIMES) - 1)

            st.caption("Posições: conforme a modalidade.")
            st.caption("Day trade: encerrar no dia.")
            st.caption("Horário do servidor da corretora · HH:MM")

    status_col, button_col = st.columns([4, 1])
    with status_col:
        st.info("Defina a identificação e as preferências do setup. Próxima etapa: Indicadores")
    with button_col:
        st.link_button("Continuar →", "?page=indicadores", type="primary", width="stretch")



def render_indicators() -> None:
    st.title("Indicadores")
    st.caption("Segunda etapa do Canvas UniversalEa.")

    col_indicators, col_parameters = st.columns(2, gap="large")

    with col_indicators:
        with st.container(border=True):
            st.subheader("Indicadores")
            selected_slot = st.radio(
                "Selecione o indicador",
                ["Indicador 1", "Indicador 2", "Indicador 3", "Indicador 4"],
                horizontal=True,
            )
            st.selectbox(
                f"Tipo - {selected_slot}",
                ["Não usar", "Média Móvel", "RSI", "ADX"],
            )

    with col_parameters:
        with st.container(border=True):
            st.subheader("Parâmetros")
            st.number_input("Período", min_value=1, value=14)
            st.selectbox("Preço aplicado", ["Close", "Open", "High", "Low", "Median", "Typical", "Weighted"])

    st.info("Configure os indicadores antes de seguir para Regras.")


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
    elif selected_page == "Indicadores":
        render_indicators()
    elif selected_page == "Sets":
        render_sets()
    elif selected_page == "Relatorios":
        render_reports()
    elif selected_page == "Configuracoes":
        render_settings()


if __name__ == "__main__":
    main()
