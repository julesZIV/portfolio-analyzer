import streamlit as st

from viz.charts import PALETTE

REFRESH = "60s"


def assign_colors(tickers, key="colors"):
    registry = st.session_state.setdefault(key, {})
    for t in list(registry):
        if t not in tickers:
            del registry[t]
    free = [i for i in range(len(PALETTE)) if i not in registry.values()]
    for t in tickers:
        if t not in registry and free:
            registry[t] = free.pop(0)
    return {t: PALETTE[i] for t, i in registry.items()}


def chart(title, fig, why, insight):
    st.subheader(title, help=why)
    st.plotly_chart(fig, width="stretch")
    st.caption(insight)
