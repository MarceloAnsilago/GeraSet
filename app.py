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
PRICE_OPTIONS = ["Close", "Open", "High", "Low", "Median", "Typical", "Weighted"]
METHOD_OPTIONS = ["SMA", "EMA", "SMMA", "LWMA"]


def render_optimization_row(indicator_index: int, name: str, key_prefix: str, current_value: int | float) -> None:
    current_col, start_col, step_col, end_col = st.columns(4)
    is_integer = isinstance(current_value, int)
    current_kwargs = {"value": int(current_value), "step": 1} if is_integer else {
        "value": float(current_value),
        "step": 1.0,
        "format": "%.2f",
    }
    step_kwargs = {"value": 1, "step": 1, "min_value": 1} if is_integer else {
        "value": 0.01,
        "step": 0.01,
        "min_value": 0.01,
        "format": "%.2f",
    }

    with current_col:
        st.number_input(
            f"{name} atual",
            disabled=True,
            key=f"opt_{key_prefix}_current_{indicator_index}",
            **current_kwargs,
        )
    with start_col:
        st.number_input(
            "Iniciar",
            key=f"opt_{key_prefix}_start_{indicator_index}",
            **current_kwargs,
        )
    with step_col:
        st.number_input(
            "Passo",
            key=f"opt_{key_prefix}_step_{indicator_index}",
            **step_kwargs,
        )
    with end_col:
        st.number_input(
            "Terminar",
            key=f"opt_{key_prefix}_end_{indicator_index}",
            **current_kwargs,
        )


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

    st.info("Configure os quatro indicadores. Apenas Média Móvel pode ser repetida.")

    indicator_cols = st.columns(4, gap="medium")
    for index in range(1, 5):
        with indicator_cols[index - 1]:
            with st.container(border=True):
                st.subheader(f"Indicador {index}")
                indicator_type = st.selectbox(
                    "Tipo",
                    ["Não usar", "Média Móvel", "RSI", "ADX"],
                    key=f"indicator_type_{index}",
                )
                parameters_tab, optimize_tab = st.tabs(["Parâmetros", "Otimizar"])

                with parameters_tab:
                    if indicator_type == "Média Móvel":
                        st.number_input("Período", min_value=1, max_value=100000, value=20, key=f"ma_period_{index}")
                        st.selectbox("Método", METHOD_OPTIONS, index=1, key=f"ma_method_{index}")
                        st.selectbox("Preço aplicado", PRICE_OPTIONS, key=f"ma_price_{index}")
                        st.number_input("Shift", min_value=-100000, max_value=100000, value=0, key=f"ma_shift_{index}")
                        st.number_input("Velas de inclinação", min_value=2, max_value=100000, value=3, key=f"ma_slope_{index}")
                    elif indicator_type == "RSI":
                        st.number_input("Período", min_value=1, max_value=100000, value=14, key=f"rsi_period_{index}")
                        st.selectbox("Preço aplicado", PRICE_OPTIONS, key=f"rsi_price_{index}")
                        st.number_input("Sobrevenda", min_value=0.0, max_value=100.0, value=30.0, key=f"rsi_lower_{index}")
                        st.number_input("Sobrecompra", min_value=0.0, max_value=100.0, value=70.0, key=f"rsi_upper_{index}")
                        st.caption("Cruzamento no fechamento.")
                    elif indicator_type == "ADX":
                        st.number_input("Período", min_value=1, max_value=100000, value=14, key=f"adx_period_{index}")
                        st.number_input("ADX mínimo", min_value=0.0, max_value=100.0, value=25.0, key=f"adx_min_{index}")
                        st.caption("Compra: +DI > -DI")
                        st.caption("Venda: -DI > +DI")
                    else:
                        st.caption("Sem parâmetros ativos.")

                with optimize_tab:
                    if indicator_type == "Média Móvel":
                        render_optimization_row(index, "Período", "ma_period", st.session_state.get(f"ma_period_{index}", 20))
                        render_optimization_row(index, "Shift", "ma_shift", st.session_state.get(f"ma_shift_{index}", 0))
                        render_optimization_row(index, "Inclinação", "ma_slope", st.session_state.get(f"ma_slope_{index}", 3))
                    elif indicator_type == "RSI":
                        render_optimization_row(index, "Período", "rsi_period", st.session_state.get(f"rsi_period_{index}", 14))
                        render_optimization_row(index, "Sobrevenda", "rsi_lower", st.session_state.get(f"rsi_lower_{index}", 30.0))
                        render_optimization_row(index, "Sobrecompra", "rsi_upper", st.session_state.get(f"rsi_upper_{index}", 70.0))
                    elif indicator_type == "ADX":
                        render_optimization_row(index, "Período", "adx_period", st.session_state.get(f"adx_period_{index}", 14))
                        render_optimization_row(index, "ADX mínimo", "adx_min", st.session_state.get(f"adx_min_{index}", 25.0))
                    else:
                        st.caption("Escolha um indicador para configurar a otimização.")

    st.subheader("Resumo dos indicadores")
    summary_cols = st.columns(4)
    for index in range(1, 5):
        selected_type = st.session_state.get(f"indicator_type_{index}", "Não usar")
        with summary_cols[index - 1]:
            with st.container(border=True):
                st.markdown(f"**Indicador {index}**")
                st.write(selected_type)

                if selected_type == "Média Móvel":
                    st.caption(f"Período: {st.session_state.get(f'ma_period_{index}', 20)}")
                    st.caption(f"Método: {st.session_state.get(f'ma_method_{index}', 'EMA')}")
                    st.caption(f"Preço: {st.session_state.get(f'ma_price_{index}', 'Close')}")
                    st.caption(f"Shift: {st.session_state.get(f'ma_shift_{index}', 0)}")
                    st.caption(f"Inclinação: {st.session_state.get(f'ma_slope_{index}', 3)} velas")
                elif selected_type == "RSI":
                    st.caption(f"Período: {st.session_state.get(f'rsi_period_{index}', 14)}")
                    st.caption(f"Preço: {st.session_state.get(f'rsi_price_{index}', 'Close')}")
                    st.caption(f"Compra ↑ {st.session_state.get(f'rsi_lower_{index}', 30.0):.2f}")
                    st.caption(f"Venda ↓ {st.session_state.get(f'rsi_upper_{index}', 70.0):.2f}")
                    st.caption("Cruzamento no fechamento")
                elif selected_type == "ADX":
                    st.caption(f"Período: {st.session_state.get(f'adx_period_{index}', 14)}")
                    st.caption(f"ADX > {st.session_state.get(f'adx_min_{index}', 25.0):.2f}")
                    st.caption("Compra: +DI > -DI")
                    st.caption("Venda: -DI > +DI")
                else:
                    st.caption("Sem parâmetros ativos.")

    footer_left, footer_right = st.columns([4, 1])
    with footer_left:
        st.info("Configure os indicadores antes de seguir para Regras.")
    with footer_right:
        st.button("Salvar indicadores", type="primary", width="stretch")


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
