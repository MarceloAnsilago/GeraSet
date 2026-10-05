from __future__ import annotations

from flask import Flask, redirect, render_template, request, url_for


app = Flask(__name__)

PAGES = {
    "inicio": "Página Inicial",
    "indicadores": "Indicadores",
    "gestao": "Gestão",
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
TARGET_UNITS = ["Pontos", "Porcentagem"]
CANDLE_OPTIONS = ["Candle 1 (último fechado)", "Candle 2", "Candle 3"]

DEFAULTS = {
    "setup_name": "Meu setup",
    "setup_magic": "1",
    "setup_market": "Forex",
    "setup_mode": "Day trade",
    "setup_timeframe": "Tempo corrente",
    "setup_lot": "0.01",
    "setup_direction": "Compra e venda",
    "setup_entry_start": "00:00",
    "setup_entry_end": "23:55",
    "rule_order_mode": "A mercado",
    "candle_filter_condition": "Desativado",
    "rule_target_unit": "Pontos",
    "rule_stop_multiplier": "1.00",
    "rule_stop_candle": "último",
    "rule_stop_measure": "Total (com pavios)",
    "rule_take_mode": "Vezes o stop",
    "rule_take_multiplier": "2.00",
}


def view_context(page: str) -> dict[str, object]:
    data = DEFAULTS | request.args.to_dict()
    return {
        "active_page": page,
        "data": data,
        "pages": PAGES,
        "timeframes": TIMEFRAMES,
        "times": TIMES,
        "price_options": PRICE_OPTIONS,
        "method_options": METHOD_OPTIONS,
        "management_modes": MANAGEMENT_MODES,
        "target_units": TARGET_UNITS,
        "candle_options": CANDLE_OPTIONS,
    }


@app.route("/")
def index():
    return redirect(url_for("page", page="inicio"))


@app.route("/<page>")
def page(page: str):
    allowed_pages = set(PAGES) | {"revisao"}
    if page not in allowed_pages:
        return redirect(url_for("page", page="inicio"))
    return render_template("page.html", **view_context(page))


if __name__ == "__main__":
    app.run(debug=True)
