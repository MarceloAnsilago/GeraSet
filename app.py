import streamlit as st


PAGES = {
    "inicio": "Página Inicial",
    "indicadores": "Indicadores",
    "gestao": "Gestão",
    "revisao": "Revisão e Sets",
    "ativacao": "Ativação",
    "relatorios": "Relatórios",
    "configuracoes": "Configurações",
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
MANAGEMENT_MODES = ["Desativado", "Pontos", "Porcentagem"]
CANDLE_FILTER_MODES = ["Desativado", "Corpo e pavios"]
CANDLE_DIRECTION_OPTIONS = ["N?o usar", "Candle de alta", "Candle de baixa"]
CANDLE_OPTIONS = ["Candle 1 (último fechado)", "Candle 2", "Candle 3"]
TARGET_UNITS = ["Pontos", "Porcentagem"]


def selected_candle_number(label: str) -> int:
    return CANDLE_OPTIONS.index(label) + 1


def render_optimization_row(indicator_index: int, name: str, key_prefix: str, current_value: int | float) -> None:
    st.caption(name)
    start_col, step_col, end_col = st.columns(3)
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


def render_management_value(label: str, key: str, disabled: bool) -> float:
    return st.number_input(
        label,
        min_value=0.0,
        max_value=100000000.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        disabled=disabled,
        key=key,
    )


def render_management_card(card_id: str, title: str, fields: list[str]) -> tuple[str, list[float]]:
    with st.container(border=True):
        st.subheader(title)
        mode = st.selectbox("Modo", MANAGEMENT_MODES, key=f"{card_id}_mode")
        disabled = mode == "Desativado"
        values = [
            render_management_value(field, f"{card_id}_{position}", disabled)
            for position, field in enumerate(fields)
        ]
        unit = "%" if mode == "Porcentagem" else "pontos"
        st.caption(f"Valores em {unit}.")
        return mode, values


def management_summary(title: str, mode: str, fields: list[str], values: list[float]) -> str:
    if mode == "Desativado":
        return f"{title}: Desativado"

    details = " · ".join(f"{field}: {value:.2f}" for field, value in zip(fields, values))
    unit = "%" if mode == "Porcentagem" else "pontos"
    return f"{title}: {details} {unit}"


def state_value(key: str, default: object) -> object:
    return st.session_state.get(key, default)


def write_review_row(label: str, value: object) -> None:
    st.caption(label)
    st.write(value)


def indicator_review_lines(index: int) -> list[str]:
    selected_type = str(state_value(f"indicator_type_{index}", "Não usar"))

    if selected_type == "Média Móvel":
        return [
            selected_type,
            f"Período: {state_value(f'ma_period_{index}', 20)}",
            f"Método: {state_value(f'ma_method_{index}', 'EMA')}",
            f"Preço: {state_value(f'ma_price_{index}', 'Close')}",
            f"Shift: {state_value(f'ma_shift_{index}', 0)}",
            f"Inclinação: {state_value(f'ma_slope_{index}', 3)} velas",
        ]

    if selected_type == "RSI":
        return [
            selected_type,
            f"Período: {state_value(f'rsi_period_{index}', 14)}",
            f"Preço: {state_value(f'rsi_price_{index}', 'Close')}",
            f"Sobrevenda: {float(state_value(f'rsi_lower_{index}', 30.0)):.2f}",
            f"Sobrecompra: {float(state_value(f'rsi_upper_{index}', 70.0)):.2f}",
        ]

    if selected_type == "ADX":
        return [
            selected_type,
            f"Período: {state_value(f'adx_period_{index}', 14)}",
            f"ADX mínimo: {float(state_value(f'adx_min_{index}', 25.0)):.2f}",
            "Compra: +DI > -DI",
            "Venda: -DI > +DI",
        ]

    return ["Não usar", "Sem parâmetros ativos."]


def candle_filter_review_lines() -> list[str]:
    condition = str(state_value("candle_filter_condition", "Desativado"))
    if condition == "Desativado":
        return ["Filtro de candle: Desativado"]

    candle = str(state_value("candle_filter_candle", CANDLE_OPTIONS[0]))
    candle_number = selected_candle_number(candle)
    unit = str(state_value(f"candle_filter_unit_{candle_number}", "Pontos"))

    lines = [f"Condição: {condition}", f"Candle: {candle}", f"Unidade: {unit}"]
    lines.extend(
        [
            f"Medida: {state_value(f'candle_filter_measure_{candle_number}', 'Corpo')}",
            f"Mínimo: {float(state_value(f'candle_filter_body_min_{candle_number}_{unit}', 0.0)):.2f}",
            f"Máximo: {float(state_value(f'candle_filter_body_max_{candle_number}_{unit}', 0.0)):.2f}",
        ]
    )
    lines.extend(
        [
            f"Pavio superior mín.: {float(state_value(f'candle_filter_upper_min_{candle_number}_{unit}', 0.0)):.2f}",
            f"Pavio superior máx.: {float(state_value(f'candle_filter_upper_max_{candle_number}_{unit}', 0.0)):.2f}",
            f"Pavio inferior mín.: {float(state_value(f'candle_filter_lower_min_{candle_number}_{unit}', 0.0)):.2f}",
            f"Pavio inferior máx.: {float(state_value(f'candle_filter_lower_max_{candle_number}_{unit}', 0.0)):.2f}",
        ]
    )
    return lines


def render_rule_value(label: str, key: str, unit: str) -> float:
    max_value = 100.0 if unit == "Porcentagem" else 100000000.0
    return st.number_input(
        label,
        min_value=0.0,
        max_value=max_value,
        value=0.0,
        step=1.0,
        format="%.2f",
        key=key,
    )


def render_rules_section() -> None:
    st.subheader("Regras de entrada e saída")
    order_col, filter_col, targets_col = st.columns(3, gap="medium")

    with order_col:
        with st.container(border=True):
            st.subheader("Ordem")
            order_mode = st.selectbox("Tipo de ordem", ["A mercado", "Pendente"], key="rule_order_mode")

            if order_mode == "Pendente":
                st.selectbox(
                    "Posicionar em",
                    ["Máxima", "Mínima", "Abertura", "Fechamento"],
                    key="rule_pending_reference",
                )
                st.number_input(
                    "Vela (1 = última fechada)",
                    min_value=1,
                    max_value=100000,
                    value=1,
                    step=1,
                    key="rule_pending_bar",
                )

            st.caption("Defina como a entrada será criada.")

    with filter_col:
        with st.container(border=True):
            st.subheader("Filtro de candle")
            condition = st.selectbox("Condição", CANDLE_FILTER_MODES, key="candle_filter_condition")

            if condition == "Desativado":
                st.caption("Sem filtro de tamanho ativo.")
            else:
                candle = st.selectbox("Configurar candle", CANDLE_OPTIONS, key="candle_filter_candle")
                candle_number = selected_candle_number(candle)
                st.selectbox(
                    "Dire??o do candle",
                    CANDLE_DIRECTION_OPTIONS,
                    key=f"candle_filter_direction_{candle_number}",
                )
                st.caption("Alta: fechamento acima da abertura. Baixa: fechamento abaixo da abertura.")
                unit = st.selectbox("Unidade dos tamanhos", TARGET_UNITS, key=f"candle_filter_unit_{candle_number}")
                unit_label = "%" if unit == "Porcentagem" else "pontos"

                st.selectbox(
                    "Medir tamanho do candle",
                    ["Corpo", "Total (máxima - mínima)"],
                    key=f"candle_filter_measure_{candle_number}",
                )
                min_col, max_col = st.columns(2)
                with min_col:
                    render_rule_value(
                        "Candle: mín.",
                        f"candle_filter_body_min_{candle_number}_{unit}",
                        unit,
                    )
                with max_col:
                    render_rule_value(
                        "Candle: máx.",
                        f"candle_filter_body_max_{candle_number}_{unit}",
                        unit,
                    )
                upper_min_col, upper_max_col = st.columns(2)
                with upper_min_col:
                    render_rule_value(
                        "Pavio sup.: mín.",
                        f"candle_filter_upper_min_{candle_number}_{unit}",
                        unit,
                    )
                with upper_max_col:
                    render_rule_value(
                        "Pavio sup.: máx.",
                        f"candle_filter_upper_max_{candle_number}_{unit}",
                        unit,
                    )

                lower_min_col, lower_max_col = st.columns(2)
                with lower_min_col:
                    render_rule_value(
                        "Pavio inf.: mín.",
                        f"candle_filter_lower_min_{candle_number}_{unit}",
                        unit,
                    )
                with lower_max_col:
                    render_rule_value(
                        "Pavio inf.: máx.",
                        f"candle_filter_lower_max_{candle_number}_{unit}",
                        unit,
                    )

            st.caption(f"Em {unit_label}. 0 = sem restrição.")

    with targets_col:
        with st.container(border=True):
            st.subheader("Alvos")
            target_unit = st.selectbox("Unidade dos alvos", TARGET_UNITS, key="rule_target_unit")
            st.number_input(
                f"Stop loss ({target_unit.lower()})",
                min_value=0.0,
                max_value=100000000.0,
                value=0.0,
                step=1.0,
                format="%.2f",
                key=f"rule_stop_loss_{target_unit}",
            )
            st.number_input(
                "+ Vezes",
                min_value=0.0,
                max_value=100000000.0,
                value=1.0,
                step=0.5,
                format="%.2f",
                key="rule_stop_multiplier",
            )
            st.selectbox("Candle", ["Último", "Penúltimo", "Antepenúltimo"], key="rule_stop_candle")
            st.selectbox("Tamanho do candle", ["Total (com pavios)", "Corpo"], key="rule_stop_measure")

            st.divider()
            st.markdown("**Take Profit**")
            take_mode = st.selectbox(
                "Calcular por",
                ["Vezes o stop", "Distância fixa"],
                key="rule_take_mode",
            )

            if take_mode == "Vezes o stop":
                st.number_input(
                    "Vezes o stop",
                    min_value=0.0,
                    max_value=100000000.0,
                    value=2.0,
                    step=0.5,
                    format="%.2f",
                    key="rule_take_multiplier",
                )
            else:
                st.number_input(
                    f"Distância ({target_unit.lower()})",
                    min_value=0.0,
                    max_value=100000000.0,
                    value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=f"rule_take_distance_{target_unit}",
                )

            st.caption("Distância e vezes 0 desligam o alvo.")


def render_navbar() -> str:
    current_page = st.query_params.get("page", "inicio")
    if current_page not in PAGES:
        current_page = "inicio"

    def nav_class(slug: str) -> str:
        classes = ["nav-link"]
        if slug == current_page:
            classes.append("active")
        return " ".join(classes)

    nav_items = "".join(
        f'<a class="{nav_class(slug)}" href="?page={slug}" target="_parent">{label}</a>'
        for slug, label in PAGES.items()
        if slug != "revisao"
    )
    review_item = (
        f'<a class="{nav_class("revisao")}" href="?page=revisao" target="_parent">'
        f'{PAGES["revisao"]}</a>'
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

div[data-testid="stHorizontalBlock"] label {{
    min-height: 2.5rem;
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
    max-width: 1420px;
    width: 100%;
}}

.nav-main {{
    align-items: center;
    display: flex;
    gap: 0.5rem;
}}

.nav-review-slot {{
    align-items: center;
    display: flex;
    margin-left: auto;
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
<nav class="geraset-navbar"><div class="geraset-navbar-inner"><div class="nav-main"><span class="brand">GeraSet</span>{nav_items}</div><div class="nav-review-slot">{review_item}</div></div></nav>""",
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
            st.text_input("Nome do setup (opcional)", value="Meu setup", max_chars=48, key="setup_name")
            st.text_input("Magic Number (automático)", value="1", disabled=True, key="setup_magic")
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
                st.selectbox("Mercado", ["Forex", "B3"], key="setup_market")
            with mode_col:
                st.selectbox("Modalidade", ["Day trade", "Swing trade"], key="setup_mode")

            timeframe_col, lot_col = st.columns(2)
            with timeframe_col:
                st.selectbox("Timeframe", TIMEFRAMES, index=len(TIMEFRAMES) - 1, key="setup_timeframe")
            with lot_col:
                st.text_input("Lote", value="0.01", key="setup_lot")

            st.selectbox("Direção permitida", ["Compra e venda", "Somente compra", "Somente venda"], key="setup_direction")
            st.caption("Lote: mín. 0.01 · Passo 0.01")

    with col_schedule:
        with st.container(border=True):
            st.subheader("Horários")
            start_col, end_col = st.columns(2)
            with start_col:
                st.selectbox("Início entradas", TIMES, index=0, key="setup_entry_start")
            with end_col:
                st.selectbox("Encerramento entradas", TIMES, index=len(TIMES) - 1, key="setup_entry_end")

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
                st.checkbox(
                    "Enviar pra cruzamento",
                    value=False,
                    key=f"indicator_send_to_crossing_{index}",
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

    crossing_options = [
        "Fechamento da vela",
        "Abertura da vela",
        "Máxima da vela",
        "Mínima da vela",
        "Abertura do dia",
        "Máxima do dia",
        "Mínima do dia",
        "Máxima do dia anterior",
        "Mínima do dia anterior",
    ]
    for index in range(1, 5):
        selected_type = st.session_state.get(f"indicator_type_{index}", "Não usar")
        if selected_type != "Não usar" and st.session_state.get(f"indicator_send_to_crossing_{index}", False):
            crossing_options.append(f"Indicador {index}: {selected_type}")

    with st.container(border=True):
        title_col, _, _, _, _, _, distance_unit_col = st.columns(7, gap="medium")
        with title_col:
            st.subheader("Condições")
        with distance_unit_col:
            distance_unit = st.radio(
                "Distância em:",
                ["Pontos", "Porcentagem"],
                horizontal=True,
                key="indicator_condition_distance_unit",
            )
        for row_index in range(5):
            suffix = "" if row_index == 0 else f"_{row_index + 1}"
            if st.session_state.get(f"indicator_condition_target{suffix}") not in crossing_options:
                st.session_state[f"indicator_condition_target{suffix}"] = crossing_options[0]
            if st.session_state.get(f"indicator_condition_reference{suffix}") not in crossing_options:
                st.session_state[f"indicator_condition_reference{suffix}"] = crossing_options[0]

            condition_col, target_col, target_candle_col, comparison_col, reference_col, candle_col, distance_col = st.columns(7, gap="medium")
            with condition_col:
                st.selectbox("Condição", ["Se", "Ou", "E"], key=f"indicator_condition_operator{suffix}")
            with target_col:
                st.selectbox("A", crossing_options, key=f"indicator_condition_target{suffix}")
            with target_candle_col:
                st.selectbox(
                    "No Candle",
                    ["Vela atual", "Anterior", "Penúltima", "Antepenúltima"],
                    key=f"indicator_condition_target_candle{suffix}",
                )
            with comparison_col:
                st.selectbox(
                    "Comparação",
                    [
                        "Maior que",
                        "Menor que",
                        "Maior ou igual que",
                        "Menor ou igual que",
                        "Igual que",
                        "Diferente de",
                        "Cruzar p/ cima de",
                        "Cruzar p/ baixo de",
                        "Cruzar&fechar acima de",
                        "Cruzar&fechar abaixo de",
                    ],
                    key=f"indicator_condition_comparison{suffix}",
                )
            with reference_col:
                st.selectbox("Da (DE)", crossing_options, key=f"indicator_condition_reference{suffix}")
            with candle_col:
                st.selectbox(
                    "No Candle",
                    ["Vela atual", "Anterior", "Penúltima", "Antepenúltima"],
                    key=f"indicator_condition_candle{suffix}",
                )
            with distance_col:
                st.text_input(f"A distância de: {distance_unit}", value="0", key=f"indicator_condition_distance{suffix}")

    footer_left, footer_right = st.columns([4, 1])
    with footer_left:
        st.info("Configure os indicadores antes de seguir para Gestão.")
    with footer_right:
        st.link_button("Continuar →", "?page=gestao", type="primary", width="stretch")


def render_management() -> None:
    st.title("Gestão")
    st.caption("Configure o breakeven, trailing stop e stop móvel da estratégia.")

    breakeven_fields = ["Ativar após", "Proteção na entrada"]
    trailing_fields = ["Ativar após", "Distância do preço", "Passo de ajuste"]
    moving_fields = ["Ativar após", "Distância do preço", "Passo de ajuste"]

    be_col, trailing_col, moving_col = st.columns(3, gap="medium")

    with be_col:
        breakeven_mode, breakeven_values = render_management_card(
            "breakeven",
            "Breakeven",
            breakeven_fields,
        )

    with trailing_col:
        trailing_mode, trailing_values = render_management_card(
            "trailing",
            "Trailing stop",
            trailing_fields,
        )

    with moving_col:
        moving_mode, moving_values = render_management_card(
            "moving_stop",
            "Stop móvel",
            moving_fields,
        )

    st.subheader("Resumo do stop móvel")
    with st.container(border=True):
        st.write(management_summary("Breakeven", breakeven_mode, breakeven_fields, breakeven_values))
        st.write(management_summary("Trailing stop", trailing_mode, trailing_fields, trailing_values))
        st.write(management_summary("Stop móvel", moving_mode, moving_fields, moving_values))

    footer_left, footer_middle, footer_right = st.columns([3, 1, 1])
    with footer_left:
        st.info("Próxima etapa: Revisão")
    with footer_middle:
        st.link_button("← Indicadores", "?page=indicadores", width="stretch")
    with footer_right:
        st.link_button("Continuar →", "?page=revisao", type="primary", width="stretch")


def render_review() -> None:
    st.title("Revisão")
    st.caption("Confira a configuração antes de salvar ou ativar o set.")

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.info("Carregue um set salvo ou confira a configuração atual.")
    with top_right:
        st.button("Carregar set", type="primary", width="stretch")

    setup_col, rules_col = st.columns(2, gap="medium")
    with setup_col:
        with st.container(border=True):
            st.subheader("Setup")
            write_review_row("Nome", state_value("setup_name", "Meu setup"))
            write_review_row("Magic Number", state_value("setup_magic", "1"))
            write_review_row("Mercado", state_value("setup_market", "Forex"))
            write_review_row("Modalidade", state_value("setup_mode", "Day trade"))
            write_review_row("Timeframe", state_value("setup_timeframe", "Tempo corrente"))
            write_review_row("Lote", state_value("setup_lot", "0.01"))
            write_review_row("Direção", state_value("setup_direction", "Compra e venda"))
            write_review_row(
                "Janela de entrada",
                f"{state_value('setup_entry_start', '00:00')} até {state_value('setup_entry_end', '23:55')}",
            )

    with rules_col:
        with st.container(border=True):
            st.subheader("Regras")
            order_mode = state_value("rule_order_mode", "A mercado")
            st.write(f"Ordem: {order_mode}")
            if order_mode == "Pendente":
                st.caption(f"Posicionar em: {state_value('rule_pending_reference', 'Máxima')}")
                st.caption(f"Vela: {state_value('rule_pending_bar', 1)}")

            st.divider()
            for line in candle_filter_review_lines():
                st.caption(line)

            st.divider()
            target_unit = str(state_value("rule_target_unit", "Pontos"))
            take_mode = str(state_value("rule_take_mode", "Vezes o stop"))
            st.write("Alvos")
            st.caption(f"Unidade: {target_unit}")
            st.caption(f"Stop loss: {float(state_value(f'rule_stop_loss_{target_unit}', 0.0)):.2f}")
            st.caption(f"+ Vezes: {float(state_value('rule_stop_multiplier', 1.0)):.2f}")
            st.caption(f"Candle: {state_value('rule_stop_candle', 'Último')}")
            st.caption(f"Tamanho: {state_value('rule_stop_measure', 'Total (com pavios)')}")
            st.caption(f"Take Profit: {take_mode}")
            if take_mode == "Vezes o stop":
                st.caption(f"Vezes o stop: {float(state_value('rule_take_multiplier', 2.0)):.2f}")
            else:
                st.caption(f"Distância: {float(state_value(f'rule_take_distance_{target_unit}', 0.0)):.2f}")

    st.subheader("Indicadores")
    indicator_cols = st.columns(4, gap="medium")
    for index in range(1, 5):
        with indicator_cols[index - 1]:
            with st.container(border=True):
                st.markdown(f"**Indicador {index}**")
                for line in indicator_review_lines(index):
                    st.caption(line)

    st.subheader("Gestão")
    management_cols = st.columns(3, gap="medium")
    management_cards = [
        ("Breakeven", "breakeven", ["Ativar após", "Proteção na entrada"]),
        ("Trailing stop", "trailing", ["Ativar após", "Distância do preço", "Passo de ajuste"]),
        ("Stop móvel", "moving_stop", ["Ativar após", "Distância do preço", "Passo de ajuste"]),
    ]
    for column, (title, key, fields) in zip(management_cols, management_cards):
        with column:
            with st.container(border=True):
                mode = str(state_value(f"{key}_mode", "Desativado"))
                values = [float(state_value(f"{key}_{position}", 0.0)) for position, _ in enumerate(fields)]
                st.write(management_summary(title, mode, fields, values))

    st.subheader("Sets")
    set_list_col, set_actions_col = st.columns([2, 1], gap="medium")
    with set_list_col:
        with st.container(border=True):
            st.subheader("Set atual")
            st.write(state_value("setup_name", "Meu setup"))
            st.caption("A revisão acima compõe o set que será salvo.")
            st.caption("Histórico e arquivos serão conectados na próxima etapa de persistência.")

    with set_actions_col:
        with st.container(border=True):
            st.subheader("Ações")
            st.button("Salvar set", type="primary", width="stretch")
            st.button("Exportar set", width="stretch")

    footer_left, footer_save, footer_next = st.columns([3, 1, 1])
    with footer_left:
        st.link_button("← Gestão", "?page=gestao", width="stretch")
    with footer_save:
        if st.button("Conferido", type="secondary", width="stretch"):
            st.success("Set conferido e pronto para salvar.")
    with footer_next:
        st.link_button("Continuar →", "?page=ativacao", type="primary", width="stretch")


def render_activation() -> None:
    st.title("Ativação")
    st.caption("Última etapa do fluxo.")

    with st.container(border=True):
        st.subheader("Controle do set")
        st.info("A ativação real ainda será conectada ao motor. Por enquanto, esta página fecha o fluxo visual.")
        active = st.toggle("Set ativo", value=False)
        st.write("Status:", "Ativo" if active else "Pausado")

    footer_left, footer_right = st.columns([4, 1])
    with footer_left:
        st.link_button("← Revisão", "?page=revisao", width="stretch")
    with footer_right:
        st.button("Aplicar", type="primary", width="stretch")


def render_reports() -> None:
    st.title("Relatórios")
    st.info("Aqui ficarão os indicadores e exportações do GeraSet.")


def render_settings() -> None:
    st.title("Configurações")
    st.info("Aqui ficarão as preferências do projeto.")


def main() -> None:
    st.set_page_config(
        page_title="GeraSet",
        page_icon="GS",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    selected_page = render_navbar()

    if selected_page == "Página Inicial":
        render_home()
    elif selected_page == "Indicadores":
        render_indicators()
    elif selected_page == "Gestão":
        render_management()
    elif selected_page == "Revisão e Sets":
        render_review()
    elif selected_page == "Ativação":
        render_activation()
    elif selected_page == "Relatórios":
        render_reports()
    elif selected_page == "Configurações":
        render_settings()


if __name__ == "__main__":
    main()
