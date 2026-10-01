function setVisible(elements, visible) {
    elements.forEach((element) => {
        element.classList.toggle("is-hidden", !visible);
    });
}

function bindRulesVisibility() {
    const orderSelect = document.querySelector("[data-rule-order]");
    const pendingFields = Array.from(document.querySelectorAll("[data-pending-fields]"));

    if (orderSelect) {
        const updateOrder = () => {
            setVisible(pendingFields, orderSelect.value === "Pendente");
        };
        orderSelect.addEventListener("change", updateOrder);
        updateOrder();
    }

    const candleCondition = document.querySelector("[data-candle-condition]");
    const candleCommon = Array.from(document.querySelectorAll("[data-candle-common]"));
    const candleSize = Array.from(document.querySelectorAll("[data-candle-size]"));
    const candleWicks = Array.from(document.querySelectorAll("[data-candle-wicks]"));

    if (candleCondition) {
        const updateCandleFilter = () => {
            const condition = candleCondition.value;
            setVisible(candleCommon, condition !== "Desativado");
            setVisible(candleSize, condition === "Candles");
            setVisible(candleWicks, condition === "Pavios");
        };
        candleCondition.addEventListener("change", updateCandleFilter);
        updateCandleFilter();
    }

    const takeMode = document.querySelector("[data-take-mode]");
    const takeMultiplier = Array.from(document.querySelectorAll("[data-take-multiplier]"));
    const takeDistance = Array.from(document.querySelectorAll("[data-take-distance]"));

    if (takeMode) {
        const updateTakeProfit = () => {
            const usesMultiplier = takeMode.value === "Vezes o stop";
            setVisible(takeMultiplier, usesMultiplier);
            setVisible(takeDistance, !usesMultiplier);
        };
        takeMode.addEventListener("change", updateTakeProfit);
        updateTakeProfit();
    }
}

document.addEventListener("DOMContentLoaded", bindRulesVisibility);
