"""Residual-income valuation and trading-comparable math.

Residual income follows the clean-surplus relation:

    BV_t = BV_{t-1} + Net income_t − Dividends_t
    RI_t = Net income_t − Cost of equity × BV_{t-1}

Terminal value at the forecast horizon uses Gordon growth on residual income:

    TV_N = RI_N × (1 + g) / (r − g)

Equity value = current book value + present value of residual income
               + present value of the terminal value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from brand import finite


class ValuationError(Exception):
    """Raised when the residual-income model cannot be solved."""


@dataclass
class Anchors:
    revenue_growth: float
    growth_label: str
    yoy_growth: Optional[float]
    net_margin: float
    margin_label: str
    latest_margin: Optional[float]
    payout: float
    payout_label: str
    latest_payout: Optional[float]
    base_revenue: float
    base_book: float
    base_year: pd.Timestamp
    notes: list[str] = field(default_factory=list)


@dataclass
class ResidualIncomeResult:
    forecast: pd.DataFrame
    book0: float
    revenue0: float
    shares: float
    pv_ri: float
    terminal_value: float
    pv_terminal: float
    equity_value: float
    value_per_share: float
    cost_of_equity: float
    terminal_growth: float
    warnings: list[str] = field(default_factory=list)


def derive_anchors(annual: pd.DataFrame) -> Anchors:
    """Historical starting points for growth, margin and the payout ratio."""
    if annual is None or annual.empty:
        raise ValuationError("Yahoo Finance did not return annual financial statements for this company.")

    notes: list[str] = []
    revenue = annual["revenue"].dropna() if "revenue" in annual.columns else pd.Series(dtype=float)
    revenue = revenue[revenue > 0]
    if revenue.empty:
        raise ValuationError("No positive annual revenue was found, so the forecast has no base.")

    base_year = revenue.index[-1]
    base_revenue = float(revenue.iloc[-1])

    equity = annual["equity"].dropna() if "equity" in annual.columns else pd.Series(dtype=float)
    equity = equity[equity.index <= base_year]
    if equity.empty or not finite(equity.iloc[-1]):
        raise ValuationError("No stockholders' equity was found, so book value cannot be rolled forward.")
    # Book value and revenue must refer to the same fiscal year.
    if equity.index[-1] != base_year:
        shared = revenue.index.intersection(equity.index)
        if len(shared) == 0:
            raise ValuationError("Revenue and book value do not share a fiscal year.")
        base_year = shared[-1]
        base_revenue = float(revenue.loc[base_year])
    base_book = float(equity.loc[base_year])

    growth_points = revenue[revenue.index <= base_year]
    yoy = None
    if len(growth_points) >= 2:
        previous = float(growth_points.iloc[-2])
        latest = float(growth_points.iloc[-1])
        if previous > 0:
            yoy = latest / previous - 1

    revenue_growth = 0.05
    growth_label = "Default 5% — fewer than two revenue years"
    if len(growth_points) >= 2:
        periods = min(3, len(growth_points) - 1)
        start = float(growth_points.iloc[-1 - periods])
        end = float(growth_points.iloc[-1])
        if start > 0 and end > 0:
            revenue_growth = (end / start) ** (1 / periods) - 1
            start_year = growth_points.index[-1 - periods].year
            end_year = growth_points.index[-1].year
            growth_label = f"{periods}-year revenue CAGR, FY{start_year}–FY{end_year}"
        elif yoy is not None:
            revenue_growth = yoy
            growth_label = f"Latest year-on-year growth, FY{growth_points.index[-1].year}"
    if revenue_growth < -0.30 or revenue_growth > 0.40:
        notes.append(
            f"Historical revenue growth is {revenue_growth:.1%}. "
            "The input was left at that rate so you can judge it; move it if a normalised rate is more appropriate."
        )

    margin_rows = []
    income = annual["net_income"] if "net_income" in annual.columns else pd.Series(dtype=float)
    candidates = [idx for idx in growth_points.index if idx <= base_year][-3:]
    for idx in candidates:
        rev = finite(annual.at[idx, "revenue"]) if "revenue" in annual.columns else None
        ni = finite(income.get(idx)) if len(income) else None
        if rev and rev > 0 and ni is not None:
            margin_rows.append((idx, ni / rev))
    if not margin_rows:
        raise ValuationError("Net income margin cannot be computed from the reported statements.")
    net_margin = float(np.mean([row[1] for row in margin_rows]))
    latest_margin = margin_rows[-1][1]
    first_m, last_m = margin_rows[0][0].year, margin_rows[-1][0].year
    if first_m == last_m:
        margin_label = f"FY{last_m} net income margin"
    else:
        margin_label = f"{len(margin_rows)}-year average net margin, FY{first_m}–FY{last_m}"

    payout_rows = []
    dividends = annual["dividends"] if "dividends" in annual.columns else pd.Series(dtype=float)
    for idx in candidates:
        ni = finite(income.get(idx)) if len(income) else None
        div = finite(dividends.get(idx)) if len(dividends) else None
        if ni is not None and ni > 0 and div is not None and div >= 0:
            payout_rows.append((idx, div / ni))
    if payout_rows:
        payout = float(np.mean([row[1] for row in payout_rows]))
        latest_payout = payout_rows[-1][1]
        first_p, last_p = payout_rows[0][0].year, payout_rows[-1][0].year
        if first_p == last_p:
            payout_label = f"FY{last_p} dividend payout"
        else:
            payout_label = f"{len(payout_rows)}-year average payout, FY{first_p}–FY{last_p}"
        if payout > 1:
            notes.append(
                "The historical payout is above 100% of net income. "
                "The default is capped at 100%; the history is still shown below."
            )
            payout = 1.0
    else:
        payout = 0.0
        latest_payout = None
        payout_label = "No positive-earnings dividend history — default 0%"
        notes.append("No dividend history on positive earnings was found. The payout ratio starts at 0%.")

    return Anchors(
        revenue_growth=revenue_growth,
        growth_label=growth_label,
        yoy_growth=yoy,
        net_margin=net_margin,
        margin_label=margin_label,
        latest_margin=latest_margin,
        payout=payout,
        payout_label=payout_label,
        latest_payout=latest_payout,
        base_revenue=base_revenue,
        base_book=base_book,
        base_year=pd.Timestamp(base_year),
        notes=notes,
    )


def residual_income(
    revenue0: float,
    book0: float,
    shares: float,
    growth: float,
    margin: float,
    payout: float,
    cost_of_equity: float,
    terminal_growth: float,
    years: int,
    base_year: int,
) -> ResidualIncomeResult:
    """Forecast residual income and convert it to a value per share."""
    if shares is None or shares <= 0:
        raise ValuationError("Share count is missing, so a per-share value cannot be calculated.")
    if revenue0 is None or revenue0 <= 0:
        raise ValuationError("Base revenue must be positive.")
    if book0 is None:
        raise ValuationError("Beginning book value is missing.")
    if years < 1:
        raise ValuationError("The forecast needs at least one year.")
    if cost_of_equity <= -0.99:
        raise ValuationError("Cost of equity is too low to discount cash amounts.")
    if terminal_growth >= cost_of_equity:
        raise ValuationError(
            "Terminal growth must sit below the cost of equity. "
            "Otherwise the Gordon growth term is undefined."
        )

    warnings: list[str] = []
    if cost_of_equity - terminal_growth < 0.02:
        warnings.append(
            "The gap between the cost of equity and terminal growth is under 2 percentage points. "
            "Small changes in either input move the terminal value sharply."
        )

    rows = []
    revenue = float(revenue0)
    book = float(book0)
    for step in range(1, years + 1):
        revenue = revenue * (1 + growth)
        net_income = revenue * margin
        # A loss is not modelled as a negative dividend (that would be a capital raise).
        dividends = net_income * payout if net_income > 0 else 0.0
        book_end = book + net_income - dividends
        ri = net_income - cost_of_equity * book
        discount = 1 / (1 + cost_of_equity) ** step
        rows.append(
            {
                "year": base_year + step,
                "revenue": revenue,
                "net_income": net_income,
                "dividends": dividends,
                "payout": (dividends / net_income) if net_income > 0 else 0.0,
                "bv_begin": book,
                "bv_end": book_end,
                "residual_income": ri,
                "discount_factor": discount,
                "pv_residual_income": ri * discount,
            }
        )
        book = book_end

    forecast = pd.DataFrame(rows)
    last_ri = float(forecast.iloc[-1]["residual_income"])
    terminal_value = last_ri * (1 + terminal_growth) / (cost_of_equity - terminal_growth)
    pv_terminal = terminal_value * float(forecast.iloc[-1]["discount_factor"])
    pv_ri = float(forecast["pv_residual_income"].sum())
    equity_value = float(book0) + pv_ri + pv_terminal
    value_per_share = equity_value / float(shares)

    if last_ri < 0:
        warnings.append(
            "Residual income in the final year is negative, so the terminal value is negative too. "
            "That means the forecast earns less than the cost of equity on a lasting basis."
        )
    if equity_value < 0:
        warnings.append(
            "Implied equity value is negative. Check growth, margin, payout and the cost of equity "
            "before reading the per-share figure as a price."
        )
    if (forecast["bv_end"] < 0).any():
        warnings.append("Book value turns negative inside the forecast. The clean-surplus roll-forward still runs, but the capital charge changes sign.")

    return ResidualIncomeResult(
        forecast=forecast,
        book0=float(book0),
        revenue0=float(revenue0),
        shares=float(shares),
        pv_ri=pv_ri,
        terminal_value=terminal_value,
        pv_terminal=pv_terminal,
        equity_value=equity_value,
        value_per_share=value_per_share,
        cost_of_equity=cost_of_equity,
        terminal_growth=terminal_growth,
        warnings=warnings,
    )


def growth_range(result_builder, growth: float, spread: float = 0.02) -> Optional[tuple[float, float, float]]:
    """Low / base / high value per share from revenue growth ± spread."""
    prices = []
    for delta in (-spread, 0.0, spread):
        try:
            result = result_builder(growth + delta)
        except ValuationError:
            continue
        price = finite(result.value_per_share)
        if price is not None:
            prices.append(price)
    if not prices:
        return None
    base = None
    try:
        base = finite(result_builder(growth).value_per_share)
    except ValuationError:
        base = prices[len(prices) // 2]
    return min(prices), base, max(prices)


def sensitivity_grid(
    result_builder,
    cost_of_equity: float,
    terminal_growth: float,
) -> pd.DataFrame:
    """Value per share around the current cost of equity and terminal growth."""
    equity_rates = [cost_of_equity + step for step in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    growth_rates = [terminal_growth + step for step in (-0.01, -0.005, 0.0, 0.005, 0.01)]
    equity_rates = [rate for rate in equity_rates if rate > 0.005]
    frame = pd.DataFrame(index=equity_rates, columns=growth_rates, dtype=float)
    for rate in equity_rates:
        for growth in growth_rates:
            if growth >= rate or growth <= -0.05:
                continue
            try:
                result = result_builder(cost_of_equity=rate, terminal_growth=growth)
            except ValuationError:
                continue
            frame.at[rate, growth] = result.value_per_share
    frame.index.name = "cost_of_equity"
    return frame


def _safe_div(numerator, denominator) -> Optional[float]:
    num = finite(numerator)
    den = finite(denominator)
    if num is None or den is None or den <= 0:
        return None
    return num / den


def trading_multiples(quote: dict) -> dict:
    """Trailing EV/Revenue, EV/EBITDA, P/E and P/Book for one company."""
    ev_revenue = _safe_div(quote.get("enterprise_value"), quote.get("ttm_revenue"))
    ev_ebitda = _safe_div(quote.get("enterprise_value"), quote.get("ttm_ebitda"))
    pe = _safe_div(quote.get("price"), quote.get("ttm_eps"))
    if pe is None:
        pe = _safe_div(quote.get("market_cap"), quote.get("ttm_net_income"))
    book_ps = finite(quote.get("book_value_ps"))
    if book_ps is None and finite(quote.get("book_equity")) and finite(quote.get("shares")):
        book_ps = quote["book_equity"] / quote["shares"]
    pb = _safe_div(quote.get("price"), book_ps)
    return {
        "ev_revenue": ev_revenue,
        "ev_ebitda": ev_ebitda,
        "pe": pe,
        "pb": pb,
        "book_ps": book_ps,
    }


def implied_price(multiple: Optional[float], kind: str, quote: dict) -> Optional[float]:
    """Translate a peer multiple into a price for the subject company."""
    mult = finite(multiple)
    shares = finite(quote.get("shares"))
    if mult is None or shares is None or shares <= 0:
        return None
    net_debt = finite(quote.get("net_debt"))
    if net_debt is None:
        net_debt = 0.0

    if kind == "ev_revenue":
        metric = finite(quote.get("ttm_revenue"))
        if metric is None or metric <= 0:
            return None
        equity = mult * metric - net_debt
        return equity / shares
    if kind == "ev_ebitda":
        metric = finite(quote.get("ttm_ebitda"))
        if metric is None or metric <= 0:
            return None
        equity = mult * metric - net_debt
        return equity / shares
    if kind == "pe":
        eps = finite(quote.get("ttm_eps"))
        if eps is None or eps <= 0:
            return None
        return mult * eps
    if kind == "pb":
        book_ps = finite(quote.get("book_value_ps"))
        if book_ps is None or book_ps <= 0:
            return None
        return mult * book_ps
    return None


def peer_distribution(values: list[Optional[float]]) -> Optional[dict]:
    """Median and a high-low band. Quartiles once four peers are available."""
    clean = [value for value in values if finite(value) is not None and finite(value) > 0]
    if not clean:
        return None
    series = pd.Series(clean, dtype=float)
    median = float(series.median())
    if len(series) == 1:
        low = high = median
        method = "Single peer"
    elif len(series) < 4:
        low = float(series.min())
        high = float(series.max())
        method = "Minimum to maximum"
    else:
        low = float(series.quantile(0.25))
        high = float(series.quantile(0.75))
        method = "25th to 75th percentile"
    return {
        "low": low,
        "median": median,
        "high": high,
        "count": int(len(series)),
        "method": method,
        "mean": float(series.mean()),
    }


def historical_metrics(annual: pd.DataFrame) -> pd.DataFrame:
    """Annual profitability, returns and cash conversion for the overview."""
    if annual is None or annual.empty:
        return pd.DataFrame()
    frame = annual.copy().sort_index()
    frame = frame[frame["revenue"].notna()] if "revenue" in frame.columns else frame
    if frame.empty:
        return frame

    def _div(a, b):
        if a not in frame.columns or b not in frame.columns:
            return pd.Series(np.nan, index=frame.index)
        return frame[a] / frame[b].where(frame[b] > 0)

    frame["gross_margin"] = _div("gross_profit", "revenue")
    frame["operating_margin"] = _div("operating_income", "revenue")
    frame["net_margin"] = _div("net_income", "revenue")
    if "equity" in frame.columns:
        avg_equity = (frame["equity"] + frame["equity"].shift(1)) / 2
        frame["roe"] = frame["net_income"] / avg_equity.where(avg_equity > 0) if "net_income" in frame.columns else np.nan
    if "total_assets" in frame.columns:
        avg_assets = (frame["total_assets"] + frame["total_assets"].shift(1)) / 2
        frame["asset_turnover"] = frame["revenue"] / avg_assets.where(avg_assets > 0)
    if "total_debt" in frame.columns and "cash" in frame.columns:
        frame["net_debt_reported"] = frame["total_debt"] - frame["cash"]
    if "ebitda" in frame.columns and "net_debt_reported" in frame.columns:
        frame["net_debt_ebitda"] = frame["net_debt_reported"] / frame["ebitda"].where(frame["ebitda"] > 0)
    if "dividends" in frame.columns and "net_income" in frame.columns:
        frame["payout"] = frame["dividends"] / frame["net_income"].where(frame["net_income"] > 0)
    if "revenue" in frame.columns:
        frame["revenue_growth"] = frame["revenue"].pct_change()
    return frame


def hand_check() -> None:
    """Locked numerical example used to guard the forecast identities."""
    result = residual_income(
        revenue0=200,
        book0=100,
        shares=10,
        growth=0.10,
        margin=0.10,
        payout=0.40,
        cost_of_equity=0.08,
        terminal_growth=0.02,
        years=2,
        base_year=2024,
    )
    first, second = result.forecast.iloc[0], result.forecast.iloc[1]
    assert math.isclose(first.revenue, 220, rel_tol=1e-9)
    assert math.isclose(first.net_income, 22, rel_tol=1e-9)
    assert math.isclose(first.dividends, 8.8, rel_tol=1e-9)
    assert math.isclose(first.bv_end, 113.2, rel_tol=1e-9)
    assert math.isclose(first.residual_income, 14, rel_tol=1e-9)
    assert math.isclose(second.revenue, 242, rel_tol=1e-9)
    assert math.isclose(second.net_income, 24.2, rel_tol=1e-9)
    assert math.isclose(second.residual_income, 15.144, rel_tol=1e-9)
    assert math.isclose(second.bv_end, 127.72, rel_tol=1e-9)
    expected_tv = 15.144 * 1.02 / 0.06
    assert math.isclose(result.terminal_value, expected_tv, rel_tol=1e-9)
    expected_equity = 100 + 14 / 1.08 + 15.144 / 1.08**2 + expected_tv / 1.08**2
    assert math.isclose(result.equity_value, expected_equity, rel_tol=1e-9)
    assert math.isclose(result.value_per_share, expected_equity / 10, rel_tol=1e-9)
    # Clean surplus holds in every year.
    for _, row in result.forecast.iterrows():
        assert math.isclose(row.bv_end, row.bv_begin + row.net_income - row.dividends, rel_tol=1e-9)


if __name__ == "__main__":
    hand_check()
    print("hand check ok")
