"""Plotly charts in the WHU colour system."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from brand import (
    ALT_BLUE,
    ANTHRACITE,
    DARK_PETROL,
    FONT,
    GREEN,
    INK,
    ORANGE,
    PETROL,
    PLOTLY_COLORWAY,
    SILVER,
    WHU_BLUE,
    WHU_LIGHT,
    money,
    per_share,
    pct,
    symbol,
)


def _base(title: str, height: int = 420) -> dict:
    return dict(
        title=dict(
            text=title,
            x=0,
            xanchor="left",
            y=1,
            yanchor="top",
            yref="container",
            font=dict(size=16, color=WHU_BLUE, family=FONT),
        ),
        font=dict(family=FONT, color=INK, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=PLOTLY_COLORWAY,
        height=height,
        margin=dict(l=16, r=16, t=72, b=16),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=12)),
        hoverlabel=dict(font=dict(family=FONT, size=13), bgcolor="white", bordercolor=SILVER),
    )


def _axes(fig: go.Figure, ytitle: str = "") -> go.Figure:
    fig.update_xaxes(showgrid=False, linecolor=SILVER, zeroline=False, tickfont=dict(color=ANTHRACITE))
    fig.update_layout(
        yaxis=dict(
            showgrid=True,
            gridcolor=SILVER,
            zerolinecolor=SILVER,
            title=dict(text=ytitle, font=dict(color=ANTHRACITE, size=12)),
            tickfont=dict(color=ANTHRACITE),
        )
    )
    return fig


def price_chart(history: pd.DataFrame, currency: str, name: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history["date"],
            y=history["close"],
            mode="lines",
            name=name,
            line=dict(color=WHU_BLUE, width=2.2),
            fill="tozeroy",
            fillcolor="rgba(0, 165, 220, 0.14)",
            hovertemplate="%{x|%d %b %Y}<br>" + currency + " %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base("Share price"),
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(count=3, label="3Y", step="year", stepmode="backward"),
                    dict(step="all", label="5Y"),
                ],
                bgcolor=SILVER,
                activecolor=WHU_LIGHT,
                font=dict(color=WHU_BLUE, size=12),
                x=1,
                xanchor="right",
                y=1.08,
            ),
            type="date",
        ),
    )
    fig.update_layout(margin=dict(l=16, r=16, t=78, b=16))
    return _axes(fig, currency)


def financial_trend(annual: pd.DataFrame, currency: str) -> go.Figure:
    fig = go.Figure()
    years = [f"FY{idx.year}" for idx in annual.index]
    fig.add_trace(
        go.Bar(
            x=years,
            y=annual["revenue"],
            name="Revenue",
            marker_color=WHU_BLUE,
            hovertemplate="%{x}<br>Revenue: %{y:,.0f}<extra></extra>",
        )
    )
    if "net_income" in annual.columns:
        fig.add_trace(
            go.Scatter(
                x=years,
                y=annual["net_income"],
                name="Net income",
                mode="lines+markers",
                line=dict(color=ORANGE, width=2.6),
                marker=dict(size=8),
                yaxis="y2",
                hovertemplate="%{x}<br>Net income: %{y:,.0f}<extra></extra>",
            )
        )
    fig.update_layout(
        **_base("Revenue and net income"),
        barmode="group",
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Net income", tickfont=dict(color=ANTHRACITE), title_font=dict(color=ANTHRACITE, size=12)),
    )
    return _axes(fig, currency)


def margin_trend(annual: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    years = [f"FY{idx.year}" for idx in annual.index]
    series = [
        ("gross_margin", "Gross margin", WHU_LIGHT),
        ("operating_margin", "Operating margin", DARK_PETROL),
        ("net_margin", "Net margin", WHU_BLUE),
    ]
    for column, label, color in series:
        if column not in annual.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=years,
                y=annual[column] * 100,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2.4),
                marker=dict(size=7),
                hovertemplate="%{x}<br>" + label + ": %{y:.1f}%<extra></extra>",
            )
        )
    fig.update_layout(**_base("Margins"))
    return _axes(fig, "%")


def forecast_chart(forecast: pd.DataFrame, currency: str) -> go.Figure:
    fig = go.Figure()
    labels = [f"FY{int(year)}" for year in forecast["year"]]
    fig.add_trace(
        go.Bar(
            x=labels,
            y=forecast["revenue"],
            name="Revenue",
            marker_color=WHU_BLUE,
            hovertemplate="%{x}<br>Revenue: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=forecast["net_income"],
            name="Net income",
            mode="lines+markers",
            line=dict(color=ORANGE, width=2.6),
            marker=dict(size=8),
            yaxis="y2",
            hovertemplate="%{x}<br>Net income: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base("Forecast revenue and net income"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Net income", tickfont=dict(color=ANTHRACITE), title_font=dict(color=ANTHRACITE, size=12)),
    )
    return _axes(fig, currency)


def book_and_ri_chart(forecast: pd.DataFrame, currency: str) -> go.Figure:
    fig = go.Figure()
    labels = [f"FY{int(year)}" for year in forecast["year"]]
    fig.add_trace(
        go.Bar(
            x=labels,
            y=forecast["residual_income"],
            name="Residual income",
            marker_color=PETROL,
            hovertemplate="%{x}<br>Residual income: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=forecast["bv_end"],
            name="Ending book value",
            mode="lines+markers",
            line=dict(color=WHU_BLUE, width=2.6),
            marker=dict(size=8),
            yaxis="y2",
            hovertemplate="%{x}<br>Ending book value: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base("Residual income and book value"),
        yaxis2=dict(
            overlaying="y",
            side="right",
            showgrid=False,
            title="Book value",
            tickfont=dict(color=ANTHRACITE),
            title_font=dict(color=ANTHRACITE, size=12),
        ),
    )
    return _axes(fig, "Residual income")


def waterfall(book_ps: float, pv_ri_ps: float, pv_tv_ps: float, value_ps: float, currency: str) -> go.Figure:
    labels = ["Book value", "PV of residual income", "PV of terminal value", "Value per share"]
    values = [book_ps, pv_ri_ps, pv_tv_ps, value_ps]
    texts = [per_share(value, currency) for value in values]
    fig = go.Figure(
        go.Waterfall(
            x=labels,
            y=values,
            measure=["absolute", "relative", "relative", "total"],
            text=texts,
            textposition="outside",
            connector=dict(line=dict(color=ANTHRACITE, width=1)),
            increasing=dict(marker=dict(color=WHU_BLUE)),
            decreasing=dict(marker=dict(color=ORANGE)),
            totals=dict(marker=dict(color=DARK_PETROL)),
            hovertemplate="%{x}<br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(**_base("Value bridge per share", height=440))
    fig.update_layout(margin=dict(l=16, r=16, t=56, b=16))
    return _axes(fig, currency)


def market_comparison(labels: list[str], prices: list[float], market: float, currency: str) -> go.Figure:
    colors = []
    for label in labels:
        if label == "Market price":
            colors.append(ORANGE)
        elif label == "Residual income":
            colors.append(WHU_BLUE)
        else:
            colors.append(PETROL)
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=prices,
            marker_color=colors,
            text=[per_share(price, currency) for price in prices],
            textposition="outside",
            hovertemplate="%{x}<br>%{text}<extra></extra>",
        )
    )
    fig.add_hline(y=market, line_dash="dot", line_color=ORANGE, line_width=1)
    fig.update_layout(**_base("Value per share against the market price", height=420))
    fig.update_layout(margin=dict(l=16, r=16, t=56, b=16))
    return _axes(fig, currency)


def multiple_bars(
    names: list[str],
    values: list[float],
    target_name: str,
    median: Optional[float],
    title: str,
) -> go.Figure:
    colors = [WHU_BLUE if name == target_name else WHU_LIGHT for name in names]
    fig = go.Figure(
        go.Bar(
            y=names,
            x=values,
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}<br>%{x:.1f}x<extra></extra>",
        )
    )
    if median is not None:
        fig.add_vline(
            x=median,
            line_dash="dash",
            line_color=DARK_PETROL,
            annotation_text="Median",
            annotation_position="top",
            annotation_font=dict(color=DARK_PETROL, size=11),
        )
    fig.update_layout(**_base(title, height=max(280, 46 * len(names) + 90)))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=ANTHRACITE))
    fig.update_xaxes(showgrid=True, gridcolor=SILVER, ticksuffix="x", tickfont=dict(color=ANTHRACITE))
    return fig


def _football_callout(low: float, high: float, mid: float, market: float, currency: str) -> str:
    applied = per_share(mid, currency)
    versus = pct(mid / market - 1, signed=True) + " vs market" if market else ""
    if high - low < max(abs(mid) * 0.01, 0.01):
        return f"{applied}   ·   {versus}" if versus else applied
    band = f"{per_share(low, currency)} – {per_share(high, currency)}"
    return f"{applied}   ·   range {band}   ·   {versus}" if versus else f"{applied}   ·   range {band}"


def football_field(rows: list[dict], market: float, currency: str) -> go.Figure:
    """Range per method, with the applied value labeled in the open space next to the bar."""
    fig = go.Figure()
    ordered = list(rows)
    points = [market]
    for row in ordered:
        points.extend([float(row["low"]), float(row["mid"]), float(row["high"])])
    lo, hi = min(points), max(points)
    span = max(hi - lo, 1.0)
    pad = span * 0.12
    xmin, xmax = lo - pad * 0.45, hi + pad
    for row in ordered:
        low, high, mid = float(row["low"]), float(row["high"]), float(row["mid"])
        detail = row.get("detail") or ""
        draw_low, draw_high = low, high
        if high - low < span * 0.012:
            draw_low = mid - span * 0.006
            draw_high = mid + span * 0.006
        fig.add_trace(
            go.Bar(
                y=[row["method"]],
                x=[draw_high - draw_low],
                base=[draw_low],
                orientation="h",
                width=0.38,
                marker=dict(color=row["color"], line=dict(width=0)),
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['method']}</b><br>"
                    f"Low {per_share(low, currency)}<br>"
                    f"Applied {per_share(mid, currency)}<br>"
                    f"High {per_share(high, currency)}<br>"
                    f"{detail}<extra></extra>"
                ),
            )
        )
        if market >= high:
            label_x, anchor = high + span * 0.015, "left"
        elif market <= low:
            label_x, anchor = low - span * 0.015, "right"
        else:
            label_x, anchor = max(high, mid) + span * 0.015, "left"
        fig.add_annotation(
            x=label_x,
            y=row["method"],
            xanchor=anchor,
            text=_football_callout(low, high, mid, market, currency),
            showarrow=False,
            font=dict(color=INK, size=13, family=FONT),
            bgcolor="rgba(244,247,251,0.94)",
            borderpad=4,
        )
    fig.add_trace(
        go.Scatter(
            x=[float(row["mid"]) for row in ordered],
            y=[row["method"] for row in ordered],
            mode="markers",
            name="Applied value",
            marker=dict(symbol="diamond", size=11, color="white", line=dict(color=INK, width=1.5)),
            hovertemplate="%{y}<br>Applied %{x:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="lines",
            name="Market price",
            line=dict(color=ORANGE, width=2, dash="dash"),
            hoverinfo="skip",
        )
    )
    fig.add_vline(x=market, line_dash="dash", line_color=ORANGE, line_width=2)
    fig.add_annotation(
        x=market,
        y=1.04,
        yref="paper",
        yanchor="bottom",
        text=f"Market {per_share(market, currency)}",
        showarrow=False,
        font=dict(color=ORANGE, size=13, family=FONT),
        bgcolor="white",
        bordercolor=ORANGE,
        borderwidth=1,
        borderpad=4,
    )
    fig.update_layout(**_base("Football field", height=max(260, 108 * len(ordered) + 150)))
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=[row["method"] for row in ordered],
        autorange="reversed",
        showgrid=False,
        tickfont=dict(color=INK, size=13),
    )
    fig.update_xaxes(
        range=[xmin, xmax],
        showgrid=True,
        gridcolor=SILVER,
        tickprefix=symbol(currency),
        tickfont=dict(color=ANTHRACITE),
        separatethousands=True,
    )
    fig.update_layout(margin=dict(l=16, r=28, t=88, b=36), bargap=0.45)
    return fig


def sensitivity_heatmap(grid: pd.DataFrame, currency: str, base_r: float, base_g: float) -> go.Figure:
    z = grid.to_numpy(dtype=float)
    x = [f"{col * 100:.1f}%" for col in grid.columns]
    y = [f"{idx * 100:.1f}%" for idx in grid.index]
    text = []
    for i, rate in enumerate(grid.index):
        row_text = []
        for j, growth in enumerate(grid.columns):
            value = grid.iloc[i, j]
            if pd.isna(value):
                row_text.append("—")
            else:
                label = f"{value:.1f}"
                if abs(rate - base_r) < 1e-9 and abs(growth - base_g) < 1e-9:
                    label = f"{value:.1f} ●"
                row_text.append(label)
        text.append(row_text)
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=text,
            texttemplate="%{text}",
            textfont=dict(color=WHU_BLUE, size=12, family=FONT),
            colorscale=[[0.0, "#F4F7FB"], [0.45, "#D6EBF8"], [1.0, "#8EC6EA"]],
            hovertemplate="Cost of equity %{y}<br>Terminal growth %{x}<br>Value %{text}<extra></extra>",
            colorbar=dict(title=dict(text=currency, side="right"), tickfont=dict(color=ANTHRACITE)),
            showscale=True,
        )
    )
    fig.update_layout(**_base("Sensitivity: value per share", height=420))
    fig.update_xaxes(title="Terminal growth", side="bottom", showgrid=False)
    fig.update_yaxes(title="Cost of equity", showgrid=False, autorange="reversed")
    fig.update_layout(margin=dict(l=16, r=16, t=56, b=48))
    return fig


def yoy_growth_chart(annual: pd.DataFrame) -> go.Figure:
    years = [f"FY{idx.year}" for idx in annual.index]
    growth = annual["revenue_growth"] * 100
    colors = [GREEN if (pd.notna(value) and value >= 0) else ORANGE for value in growth]
    fig = go.Figure(
        go.Bar(
            x=years,
            y=growth,
            marker_color=colors,
            name="Revenue growth",
            hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(**_base("Historical revenue growth"))
    return _axes(fig, "%")
