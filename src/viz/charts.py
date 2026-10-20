import numpy as np
import plotly.graph_objects as go

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
GRAY = "#8a8983"
LIGHT_GRAY = "#b9b8b2"
BLUE, RED = "#2a78d6", "#e34948"
DIVERGING = [[0.0, BLUE], [0.5, "#f0efec"], [1.0, RED]]


def _layout(fig, y_title, y_format=None, height=400):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_yaxes(title_text=y_title, tickformat=y_format, showgrid=True, gridwidth=1)
    fig.update_xaxes(showgrid=False)
    return fig


def _lines(fig, frame, colors, names, hover):
    for t in frame.columns:
        fig.add_trace(go.Scatter(
            x=frame.index, y=frame[t], name=names.get(t, t), mode="lines",
            line=dict(color=colors[t], width=2), hovertemplate=hover,
        ))


def _benchmark_line(fig, series, name, hover):
    fig.add_trace(go.Scatter(
        x=series.index, y=series, name=name, mode="lines",
        line=dict(color=GRAY, width=2, dash="dash"), hovertemplate=hover,
    ))


def base_100(prices, colors, names, benchmark=None, benchmark_name=None):
    fig = go.Figure()
    _lines(fig, prices / prices.iloc[0] * 100, colors, names, "%{y:.1f}")
    if benchmark is not None:
        _benchmark_line(fig, benchmark / benchmark.iloc[0] * 100, benchmark_name, "%{y:.1f}")
    fig.add_hline(y=100, line_width=1, line_color=GRAY)
    return _layout(fig, "Start = 100")


def candles(ohlc, y_title):
    fig = go.Figure(go.Candlestick(
        x=ohlc.index, open=ohlc["Open"], high=ohlc["High"], low=ohlc["Low"], close=ohlc["Close"],
        increasing_line_color=BLUE, decreasing_line_color=RED, showlegend=False,
    ))
    weekends = (ohlc.index.dayofweek >= 5).any()
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=[] if weekends else [dict(bounds=["sat", "mon"])])
    return _layout(fig, y_title)


def drawdowns(dd, colors, names, benchmark=None, benchmark_name=None):
    fig = go.Figure()
    _lines(fig, dd, colors, names, "%{y:.1%}")
    if benchmark is not None:
        _benchmark_line(fig, benchmark, benchmark_name, "%{y:.1%}")
    return _layout(fig, "Loss from previous peak", ".0%")


def risk_return(stats, colors, names, benchmark_stats=None, benchmark_name=None):
    fig = go.Figure()
    for t, row in stats.iterrows():
        name = names.get(t, t)
        fig.add_trace(go.Scatter(
            x=[row["volatility"]], y=[row["return"]], mode="markers+text",
            text=[name], textposition="top center", showlegend=False,
            marker=dict(size=12, color=colors[t], line=dict(width=2, color="white")),
            hovertemplate=f"<b>{name}</b><br>Volatility %{{x:.1%}}<br>Return %{{y:.1%}}"
                          f"<br>Sharpe {row['sharpe']:.2f}<extra></extra>",
        ))
    if benchmark_stats is not None:
        fig.add_trace(go.Scatter(
            x=[benchmark_stats["volatility"]], y=[benchmark_stats["return"]], mode="markers+text",
            text=[benchmark_name], textposition="bottom center", showlegend=False,
            marker=dict(size=12, color=GRAY, symbol="diamond", line=dict(width=2, color="white")),
            hovertemplate=f"<b>{benchmark_name}</b><br>Volatility %{{x:.1%}}<br>Return %{{y:.1%}}<extra></extra>",
        ))
    fig.add_hline(y=0, line_width=1, line_color=GRAY)
    fig = _layout(fig, "Annual return", ".0%")
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title_text="Annual volatility", tickformat=".0%", showgrid=True)
    return fig


def correlations(returns, names):
    corr = returns.corr()
    labels = [names.get(t, t) for t in corr.columns]
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=labels, y=labels,
        zmin=-1, zmax=1, zmid=0, colorscale=DIVERGING,
        text=np.round(corr.values, 2), texttemplate="%{text:.2f}",
        xgap=2, ygap=2,
        hovertemplate="%{y} / %{x}<br>Correlation %{z:.2f}<extra></extra>",
        colorbar=dict(thickness=12),
    ))
    fig.update_layout(height=max(360, 45 * len(labels) + 120), margin=dict(l=10, r=10, t=30, b=10))
    fig.update_yaxes(autorange="reversed")
    return fig


def frontier(cloud, front, stats, colors, names, max_sharpe_point, min_variance_point):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cloud["volatility"], y=cloud["return"], mode="markers", name="Random portfolios",
        marker=dict(size=4, color=LIGHT_GRAY, opacity=0.35), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=front["volatility"], y=front["return"], mode="lines", name="Efficient frontier",
        line=dict(color=BLUE, width=3),
        hovertemplate="Volatility %{x:.1%}<br>Return %{y:.1%}<extra>Frontier</extra>",
    ))
    for t, row in stats.iterrows():
        name = names.get(t, t)
        fig.add_trace(go.Scatter(
            x=[row["volatility"]], y=[row["return"]], mode="markers+text",
            text=[name], textposition="middle right", showlegend=False,
            marker=dict(size=9, color=colors[t], line=dict(width=2, color="white")),
            hovertemplate=f"<b>{name}</b><br>Volatility %{{x:.1%}}<br>Return %{{y:.1%}}<extra></extra>",
        ))
    for (vol, ret), name, symbol in [(max_sharpe_point, "Best risk-adjusted", "star"),
                                     (min_variance_point, "Lowest risk", "diamond")]:
        fig.add_trace(go.Scatter(
            x=[vol], y=[ret], mode="markers", name=name,
            marker=dict(size=18, symbol=symbol, color="#0b0b0b", line=dict(width=2, color="white")),
            hovertemplate=f"<b>{name}</b><br>Volatility %{{x:.1%}}<br>Return %{{y:.1%}}<extra></extra>",
        ))
    fig = _layout(fig, "Annual return", ".0%", height=460)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title_text="Annual volatility", tickformat=".0%", showgrid=True)
    return fig


def weights(weights_df, names):
    df = weights_df.sort_values(weights_df.columns[0])
    labels = [names.get(t, t) for t in df.index]
    fig = go.Figure()
    for i, strategy in enumerate(df.columns):
        fig.add_trace(go.Bar(
            y=labels, x=df[strategy], name=strategy, orientation="h",
            marker=dict(color=PALETTE[i], cornerradius=4),
            text=[f"{v:.0%}" if v >= 0.01 else "" for v in df[strategy]], textposition="outside",
            hovertemplate="%{y}<br>%{x:.1%}<extra>" + strategy + "</extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig = _layout(fig, None, height=max(320, 40 * len(df) + 100))
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(tickformat=".0%", showgrid=True, title_text="Portfolio weight")
    return fig


def ranking(perf, names, x_title="Performance"):
    perf = perf.sort_values()
    fig = go.Figure(go.Bar(
        y=[names.get(t, t) for t in perf.index], x=perf, orientation="h",
        marker=dict(color=[BLUE if v >= 0 else RED for v in perf], cornerradius=4),
        text=[f"{v:+.1%}" for v in perf], textposition="outside",
        hovertemplate="%{y}<br>%{x:+.2%}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_color=GRAY)
    fig = _layout(fig, None, height=max(340, 26 * len(perf) + 80))
    fig.update_layout(hovermode="closest", showlegend=False)
    fig.update_xaxes(tickformat=".0%", showgrid=True, title_text=x_title)
    return fig


def top_holdings(df, n=10):
    top = df.head(n)
    rest = df["weight"].iloc[n:].sum()
    labels = list(top["label"]) + ([f"Other ({len(df) - n} positions)"] if rest > 0 else [])
    values = list(top["weight"]) + ([rest] if rest > 0 else [])
    colors = [BLUE] * len(top) + ([GRAY] if rest > 0 else [])
    fig = go.Figure(go.Bar(
        y=labels[::-1], x=values[::-1], orientation="h",
        marker=dict(color=colors[::-1], cornerradius=4),
        text=[f"{v:.1%}" for v in values[::-1]], textposition="outside",
        hovertemplate="%{y}<br>%{x:.2%} of the portfolio<extra></extra>",
    ))
    fig = _layout(fig, None, height=max(340, 30 * len(labels) + 80))
    fig.update_layout(hovermode="closest", showlegend=False)
    fig.update_xaxes(tickformat=".0%", showgrid=True, title_text="Portfolio weight")
    return fig


def changes(df, n=10):
    top = df.head(n).iloc[::-1]
    fig = go.Figure(go.Bar(
        y=[f"{i} · {a}" for i, a in zip(top["issuer"].str.title(), top["action"])],
        x=top["weight_change"], orientation="h",
        marker=dict(color=[BLUE if v >= 0 else RED for v in top["weight_change"]], cornerradius=4),
        text=[f"{v * 100:+.1f} pts" for v in top["weight_change"]], textposition="outside",
        customdata=np.stack([top["weight_before"], top["weight"]], axis=1),
        hovertemplate="%{y}<br>Weight: %{customdata[0]:.2%} → %{customdata[1]:.2%}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_color=GRAY)
    fig = _layout(fig, None, height=max(340, 30 * len(top) + 80))
    fig.update_layout(hovermode="closest", showlegend=False)
    fig.update_xaxes(tickformat=".0%", showgrid=True, title_text="Change in portfolio weight")
    return fig


def copycat(portfolio, reference, reference_name, filing_date):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=portfolio.index, y=portfolio, name="Copied portfolio", mode="lines",
        line=dict(color=BLUE, width=2), hovertemplate="%{y:.1f}",
    ))
    _benchmark_line(fig, reference, reference_name, "%{y:.1f}")
    fig.add_hline(y=100, line_width=1, line_color=GRAY)
    fig.add_vline(x=filing_date, line_width=1, line_dash="dot", line_color=GRAY)
    fig.add_annotation(x=filing_date, y=1, yref="paper", text="Filing made public", showarrow=False,
                       xanchor="left", yanchor="top", xshift=4, font=dict(size=12))
    return _layout(fig, "Quarter end = 100")


def option_prices(spots, call, put, spot, strike):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spots, y=call, name="Call", mode="lines",
                             line=dict(color=PALETTE[0], width=2), hovertemplate="%{y:.2f}"))
    fig.add_trace(go.Scatter(x=spots, y=put, name="Put", mode="lines",
                             line=dict(color=PALETTE[1], width=2), hovertemplate="%{y:.2f}"))
    fig.add_vline(x=strike, line_width=1, line_dash="dot", line_color=GRAY)
    fig.add_vline(x=spot, line_width=1, line_color=GRAY)
    fig.add_annotation(x=strike, y=1, yref="paper", text="Strike", showarrow=False,
                       xanchor="left", yanchor="top", xshift=4, font=dict(size=12))
    fig = _layout(fig, "Option price")
    fig.update_xaxes(title_text="Underlying price")
    return fig


def vol_smile(df, spot):
    fig = go.Figure()
    for i, (typ, name) in enumerate([("call", "Call"), ("put", "Put")]):
        d = df[df["type"] == typ].sort_values("strike")
        fig.add_trace(go.Scatter(
            x=d["strike"], y=d["iv"], name=f"{name} (Black-Scholes)", mode="lines+markers",
            line=dict(color=PALETTE[i], width=2), marker=dict(size=8, line=dict(width=2, color="white")),
            hovertemplate="%{y:.1%}",
        ))
        fig.add_trace(go.Scatter(
            x=d["strike"], y=d["iv_yahoo"], name=f"{name} (Yahoo)", mode="lines",
            line=dict(color=PALETTE[i], width=2, dash="dash"), opacity=0.5, hovertemplate="%{y:.1%}",
        ))
    fig.add_vline(x=spot, line_width=1, line_color=GRAY)
    fig.add_annotation(x=spot, y=1, yref="paper", text="Spot", showarrow=False,
                       xanchor="left", yanchor="top", xshift=4, font=dict(size=12))
    fig = _layout(fig, "Implied volatility", ".0%", height=450)
    fig.update_xaxes(title_text="Strike")
    return fig
