"""WHU equity valuation app.

Residual income, trading comparables and a football field for one listed company,
with market and financial data from Yahoo Finance.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Callable, Optional

import pandas as pd
import streamlit as st

from brand import CSS, finite, money, multiple, pct, per_share
from charts import (
    book_and_ri_chart,
    financial_trend,
    football_field,
    forecast_chart,
    margin_trend,
    market_comparison,
    multiple_bars,
    price_chart,
    sensitivity_heatmap,
    waterfall,
    yoy_growth_chart,
)
from valuation import (
    Anchors,
    ValuationError,
    derive_anchors,
    growth_range,
    historical_metrics,
    implied_price,
    peer_distribution,
    residual_income,
    sensitivity_grid,
    trading_multiples,
)
from ticker_search import ticker_search
from yahoo_data import MarketDataError, load_company, load_quote, market_news, search_listings

PAGES = ["Overview", "Residual Income", "Trading Comparables", "Football Field"]
STEP = {
    "Overview": "Step 1 of 4 · Market and financials",
    "Residual Income": "Step 2 of 4 · Forecast and residual income",
    "Trading Comparables": "Step 3 of 4 · Peer multiples",
    "Football Field": "Step 4 of 4 · Valuation range",
}
MULTIPLE_META = [
    ("ev_revenue", "EV / Revenue", "EV/Revenue", "#00AAB9"),
    ("ev_ebitda", "EV / EBITDA", "EV/EBITDA", "#006E78"),
    ("pe", "P / E", "P/E", "#00A5DC"),
    ("pb", "P / Book", "P/Book", "#1E2F78"),
]
PLOT_CONFIG = {"responsive": True, "displayModeBar": False}


st.set_page_config(
    page_title="WHU Equity Valuation · Group 8",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def _init() -> None:
    st.session_state.setdefault("page", "Overview")
    st.session_state.setdefault("company", None)
    st.session_state.setdefault("anchors", None)
    st.session_state.setdefault("anchor_error", None)
    st.session_state.setdefault("load_error", None)
    st.session_state.setdefault("pending_load", None)
    st.session_state.setdefault("peers", [])
    st.session_state.setdefault("company_query", "")
    st.session_state.setdefault("peer_query", "")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _set_assumptions(anchors: Anchors) -> None:
    st.session_state.rev_g = _clamp(round(anchors.revenue_growth * 100, 1), -30.0, 40.0)
    st.session_state.margin = _clamp(round(anchors.net_margin * 100, 1), -20.0, 60.0)
    st.session_state.payout = _clamp(round(anchors.payout * 100, 1), 0.0, 100.0)
    st.session_state.coe = 8.0
    st.session_state.tg = 2.5
    st.session_state.years = 5


@st.cache_data(ttl=1800, show_spinner=False)
def _company(symbol: str) -> dict:
    return load_company(symbol)


@st.cache_data(ttl=1800, show_spinner=False)
def _quote(symbol: str) -> dict:
    return load_quote(symbol)


@st.cache_data(ttl=900, show_spinner=False)
def _search_listings(query: str) -> list[dict]:
    return search_listings(query)


@st.cache_data(ttl=900, show_spinner=False)
def _headlines() -> list[dict]:
    return market_news()


def _live_pick(label: str, state_key: str, component_key: str) -> Optional[dict]:
    """Search box whose matches appear while typing, then return the chosen share."""
    query = st.session_state.get(state_key, "")
    if not isinstance(query, str):
        query = ""
    cleaned = query.strip()
    matches = _search_listings(cleaned) if len(cleaned) >= 2 else []
    payload = [
        {"symbol": item["symbol"], "name": item["name"], "exchange": item.get("exchange") or ""}
        for item in matches
    ]
    picked = ticker_search(label, cleaned, payload, component_key)
    new_query = str(picked.get("query") or "").strip()
    if new_query != cleaned:
        st.session_state[state_key] = new_query
        st.rerun()
    symbol = picked.get("symbol") or None
    if not symbol:
        return None
    return {
        "symbol": str(symbol),
        "name": picked.get("name") or str(symbol),
        "exchange": picked.get("exchange") or "",
    }


def _mark(kind: str = "") -> None:
    marker = f"assign-anchor {kind}".strip()
    st.markdown(f'<span class="{marker}">!</span>', unsafe_allow_html=True)


def _kpi(label: str, value: str, assignment: bool = False, delta: Optional[str] = None) -> None:
    flag = '<span class="assign-flag">!</span>' if assignment else ""
    delta_html = ""
    if delta:
        tone = "up" if str(delta).startswith("+") else "down" if str(delta).startswith(("-", "−")) else ""
        delta_html = f'<div class="kpi-delta {tone}">{html.escape(str(delta))}</div>'
    st.markdown(
        f'<div class="kpi">{flag}<div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(str(value))}</div>{delta_html}</div>',
        unsafe_allow_html=True,
    )


def _when(timestamp: Optional[int]) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp).strftime("%d %b %Y · %H:%M")


def _load(symbol: str) -> None:
    st.session_state.pending_load = None
    try:
        company = _company(symbol.strip().upper())
    except MarketDataError as exc:
        st.session_state.load_error = str(exc)
        return
    except Exception:
        st.session_state.load_error = "Yahoo Finance could not be reached. Try the ticker again in a moment."
        return
    previous = (st.session_state.get("company") or {}).get("ticker")
    st.session_state.company = company
    st.session_state.load_error = None
    st.session_state.anchor_error = None
    if previous and previous != company["ticker"]:
        st.session_state.peers = []
    try:
        anchors = derive_anchors(company["annual"])
    except ValuationError as exc:
        st.session_state.anchors = None
        st.session_state.anchor_error = str(exc)
        st.rerun()
        return
    st.session_state.anchors = anchors
    _set_assumptions(anchors)
    st.rerun()


def _chart(fig) -> None:
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)


def _assumptions() -> dict:
    return {
        "growth": st.session_state.rev_g / 100,
        "margin": st.session_state.margin / 100,
        "payout": st.session_state.payout / 100,
        "cost_of_equity": st.session_state.coe / 100,
        "terminal_growth": st.session_state.tg / 100,
        "years": int(st.session_state.years),
    }


def _builder(company: dict, anchors: Anchors) -> Callable:
    base = _assumptions()

    def build(**overrides):
        params = {
            "revenue0": anchors.base_revenue,
            "book0": anchors.base_book,
            "shares": company["shares"],
            "growth": base["growth"],
            "margin": base["margin"],
            "payout": base["payout"],
            "cost_of_equity": base["cost_of_equity"],
            "terminal_growth": base["terminal_growth"],
            "years": base["years"],
            "base_year": int(anchors.base_year.year),
        }
        params.update(overrides)
        return residual_income(**params)

    return build


def _solve(company: dict, anchors: Anchors):
    try:
        return _builder(company, anchors)(), None
    except ValuationError as exc:
        return None, str(exc)


def _total_return(close: pd.Series, years: int = 0, months: int = 0) -> Optional[float]:
    if close.empty:
        return None
    cutoff = close.index[-1] - pd.DateOffset(years=years, months=months)
    prior = close[close.index <= cutoff]
    if prior.empty:
        nearby = close[close.index <= cutoff + pd.Timedelta(days=14)]
        if nearby.empty:
            return None
        base = float(nearby.iloc[0])
    else:
        base = float(prior.iloc[-1])
    if base <= 0:
        return None
    return float(close.iloc[-1] / base - 1)


def _returns(history: pd.DataFrame) -> dict:
    if history is None or history.empty:
        return {}
    close = history.set_index("date")["close"].sort_index()
    end = close.index[-1]
    previous_year = close[close.index.year < end.year]
    ytd = None
    if not previous_year.empty and float(previous_year.iloc[-1]) > 0:
        ytd = float(close.iloc[-1] / previous_year.iloc[-1] - 1)
    return {
        "1M": _total_return(close, months=1),
        "YTD": ytd,
        "1Y": _total_return(close, years=1),
        "3Y": _total_return(close, years=3),
        "5Y": _total_return(close, years=5),
    }


def _peer_symbols(target: str) -> list[str]:
    symbols = []
    for peer in st.session_state.get("peers", []):
        symbol = peer.get("symbol")
        if symbol and symbol != target and symbol not in symbols:
            symbols.append(symbol)
    return symbols[:8]


def _add_peer(choice: dict, target: str) -> None:
    if choice["symbol"] == target:
        st.session_state.peer_notice = "That share is the company being valued."
        return
    peers = st.session_state.peers
    if any(peer["symbol"] == choice["symbol"] for peer in peers):
        st.session_state.peer_notice = f"{choice['symbol']} is already in the peer group."
        return
    if len(peers) >= 8:
        st.session_state.peer_notice = "The peer group is limited to eight companies."
        return
    peers.append({"symbol": choice["symbol"], "name": choice["name"], "exchange": choice.get("exchange", "")})
    st.session_state.peer_notice = None
    st.rerun()


def _peer_rows(target: str, tickers: list[str]) -> tuple[list[dict], list[str]]:
    rows = []
    errors = []
    for symbol in tickers:
        try:
            quote = _quote(symbol)
        except MarketDataError as exc:
            errors.append(str(exc))
            continue
        except Exception:
            errors.append(f"No data for {symbol}.")
            continue
        if quote["ticker"] == target:
            continue
        multiples = trading_multiples(quote)
        rows.append({**quote, **multiples})
    return rows, errors


def _footer(company: Optional[dict] = None) -> None:
    currency = ""
    if company:
        currency = (
            f" Market prices in {company['currency']}."
            f" Financial statements in {company['financial_currency']}."
        )
    st.markdown(
        f'<p class="footnote">Source: Yahoo Finance.{currency} '
        "Prices can be delayed. This is a course model for teaching valuation, not a recommendation to buy or sell. "
        "PtMiM - Advanced Financial Accounting - Group 8 · WHU – Otto Beisheim School of Management.</p>",
        unsafe_allow_html=True,
    )


def _hero(company: dict) -> None:
    price = company["price"]
    previous = company.get("previous_close")
    change = (price - previous) if previous else None
    change_pct = (change / previous) if previous else None
    if change is not None and change >= 0:
        change_html = f'<span class="hero-change up">▲ {per_share(change, company["currency"])} ({pct(change_pct, 2, signed=True)})</span>'
    elif change is not None:
        change_html = f'<span class="hero-change down">▼ {per_share(abs(change), company["currency"])} ({pct(change_pct, 2)})</span>'
    else:
        change_html = ""
    st.markdown(
        f"""
        <div class="hero">
          <span class="assign-flag">!</span>
          <p class="hero-title">{html.escape(company["name"])}</p>
          <p class="hero-meta">{company["ticker"]} · {company["exchange"]} · {company["sector"]} · {company["industry"]}</p>
          <p class="hero-price">{per_share(price, company["currency"])}{change_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _sidebar() -> None:
    st.sidebar.markdown(
        """
        <div class="brand">
          <div class="brand-credit">PtMiM - Advanced Financial Accounting - Group 8</div>
          <div class="brand-school">WHU – Otto Beisheim School of Management</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        choice = _live_pick("Search Yahoo Finance", "company_lookup", "company_search")
    symbol = choice["symbol"] if choice else None
    if choice:
        st.sidebar.caption(f"{choice['symbol']} · {choice['name']}")
    if st.sidebar.button("Load company", type="primary", use_container_width=True, disabled=symbol is None):
        st.session_state.pending_load = symbol
    pending = st.session_state.get("pending_load")
    if pending:
        with st.spinner(f"Loading {pending.strip().upper()}…"):
            _load(pending)
    if st.session_state.get("load_error"):
        st.sidebar.error(st.session_state.load_error)
    open_company = st.session_state.get("company")
    if open_company:
        st.sidebar.caption(f"Open: {open_company['ticker']} · {open_company['name']}")
    st.sidebar.divider()
    st.sidebar.radio("Navigate", PAGES, key="page")
    st.sidebar.caption(STEP[st.session_state.page])
    st.sidebar.caption("A red ! marks a metric from the assignment.")
    st.sidebar.caption("Loading a company refills growth, margin and payout from its history, and resets the cost of equity to 8%.")


def _landing() -> None:
    st.markdown(
        """
        <section class="guide">
          <p class="guide-kicker">PtMiM · Advanced Financial Accounting · Group 8</p>
          <h2>From the statements to a value per share.</h2>
          <p class="guide-lead">Search Yahoo Finance in the sidebar, choose a listed share, and load it. The pages then walk from the reported numbers to a residual-income value, peer multiples, and one range against the live price.</p>
          <div class="guide-grid">
            <div>
              <h3>How to proceed</h3>
              <ol>
                <li>Type a name or ticker, pick a share from the list, and press Load company.</li>
                <li>On Overview, read the market price and the annual statements.</li>
                <li>On Residual Income, edit the forecast. The value updates as you type.</li>
                <li>On Trading Comparables, add peers the same way, then open the Football Field.</li>
              </ol>
            </div>
            <div>
              <h3>Where the assignment KPIs are</h3>
              <ul>
                <li><strong>Overview</strong> — market price, book value per share, revenue growth, and net margin.</li>
                <li><strong>Residual Income</strong> — revenue growth, net income margin, payout ratio, cost of equity, terminal growth, forecast period, and implied value per share.</li>
                <li><strong>Trading Comparables</strong> — EV/Revenue, EV/EBITDA, P/E, and P/Book.</li>
                <li><strong>Football Field</strong> — the valuation range set against the market price.</li>
              </ul>
            </div>
            <div>
              <h3>How to recognise them</h3>
              <p>Each KPI named in the assignment carries a red <span class="guide-bang">!</span> in the corner. Hover the mark and it reads “Relevant KPI's from Assignment”. Figures without the mark are extra context and are not part of the assignment block.</p>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<p class="kicker">Business news</p>', unsafe_allow_html=True)
    st.subheader("Current Business Headlines")
    st.caption("General business news from Yahoo Finance.")
    stories = _headlines()
    if not stories:
        st.info("Yahoo Finance did not return headlines just now.")
    else:
        cards = []
        for story in stories:
            cards.append(
                "<a class='news-card' href='{link}' target='_blank' rel='noopener noreferrer'>"
                "<div class='news-source'>{publisher}</div>"
                "<div class='news-title'>{title}</div>"
                "<div class='news-time'>{when}</div></a>".format(
                    link=html.escape(story["link"], quote=True),
                    publisher=html.escape(story["publisher"]),
                    title=html.escape(story["title"]),
                    when=html.escape(_when(story.get("published_at"))),
                )
            )
        st.markdown(f"<div class='news-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)
    _footer()


def _page_overview(company: dict) -> None:
    st.markdown('<p class="kicker">Market & financials</p>', unsafe_allow_html=True)
    st.subheader("What the market and the statements say")
    st.markdown(
        '<p class="lede">Live price and trailing profile on top. Annual statements underneath — they are the base for the residual-income forecast.</p>',
        unsafe_allow_html=True,
    )
    currency = company["currency"]
    fcy = company["financial_currency"]
    if currency != fcy:
        st.warning(f"The share trades in {currency}, while the statements are in {fcy}. Per-share values later in the app stay in {fcy} and are not compared with the {currency} price.")

    annual = historical_metrics(company["annual"])
    latest = annual.dropna(how="all").iloc[-1] if not annual.empty else None
    div_yield = None
    if company.get("dividend_rate") and company["price"]:
        div_yield = company["dividend_rate"] / company["price"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi("Market cap", money(company["market_cap"], currency))
    with c2:
        _kpi("Enterprise value", money(company["enterprise_value"], currency))
    with c3:
        _kpi("Book value / share", per_share(company.get("book_value_ps"), currency), assignment=True)
    with c4:
        _kpi("Shares", _shares(company))
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        _kpi("Beta", f"{company['beta']:.2f}" if company.get("beta") is not None else "—")
    with d2:
        _kpi("Dividend yield", pct(div_yield))
    with d3:
        _kpi("Net debt", money(company.get("net_debt"), currency))
    with d4:
        _kpi("Trailing EPS", per_share(company.get("ttm_eps"), currency))

    returns = _returns(company["history"])
    if returns:
        cols = st.columns(len(returns))
        for col, (label, value) in zip(cols, returns.items()):
            with col:
                _kpi(label, pct(value, signed=True))

    history = company["history"]
    if history is not None and not history.empty:
        _chart(price_chart(history, currency, company["ticker"]))
    else:
        st.info("No price history came back for this ticker.")

    if annual.empty:
        st.info("Annual financial statements were not available.")
        _footer(company)
        return

    left, right = st.columns(2)
    with left:
        _mark()
        _chart(financial_trend(annual, fcy))
    with right:
        _mark()
        _chart(margin_trend(annual))

    st.markdown('<p class="kicker">Further metrics</p>', unsafe_allow_html=True)
    st.subheader("Profitability, returns and leverage")
    if latest is not None:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            _kpi("Gross margin", pct(latest.get("gross_margin")))
        with m2:
            _kpi("Operating margin", pct(latest.get("operating_margin")))
        with m3:
            _kpi("Net margin", pct(latest.get("net_margin")), assignment=True)
        with m4:
            _kpi("ROE", pct(latest.get("roe")))
        n1, n2, n3, n4 = st.columns(4)
        with n1:
            _kpi("Free cash flow", money(latest.get("free_cash_flow"), fcy))
        with n2:
            _kpi("Asset turnover", f"{latest['asset_turnover']:.2f}x" if finite(latest.get("asset_turnover")) else "—")
        with n3:
            _kpi("Net debt / EBITDA", f"{latest['net_debt_ebitda']:.2f}x" if finite(latest.get("net_debt_ebitda")) else "—")
        with n4:
            _kpi("Latest revenue growth", pct(latest.get("revenue_growth"), signed=True), assignment=True)
        st.caption("ROE uses average equity. Net debt / EBITDA uses reported debt minus cash, which can differ from the enterprise-value bridge on the quote.")

    display = pd.DataFrame(
        {
            "Year": [f"FY{idx.year}" for idx in annual.index],
            "Revenue": [money(v, fcy) for v in annual.get("revenue", [])],
            "Net income": [money(v, fcy) for v in annual.get("net_income", [])],
            "Net margin": [pct(v) for v in annual.get("net_margin", [])],
            "Book equity": [money(v, fcy) for v in annual.get("equity", [])],
            "ROE": [pct(v) for v in annual.get("roe", [])],
            "Dividends": [money(v, fcy) for v in annual.get("dividends", [])],
            "Payout": [pct(v) for v in annual.get("payout", [])],
            "Free cash flow": [money(v, fcy) for v in annual.get("free_cash_flow", [])],
        }
    )
    _mark()
    st.dataframe(display, hide_index=True, use_container_width=True)
    _footer(company)


def _shares(company: dict) -> str:
    shares = finite(company.get("shares"))
    if shares is None:
        return "—"
    if shares >= 1e9:
        return f"{shares / 1e9:.2f}bn"
    if shares >= 1e6:
        return f"{shares / 1e6:.1f}m"
    return f"{shares:,.0f}"


def _page_residual(company: dict, anchors: Optional[Anchors]) -> None:
    st.markdown('<p class="kicker">Assignment</p>', unsafe_allow_html=True)
    st.subheader("Residual income valuation")
    st.markdown(
        '<p class="lede">Revenue is grown forward, net income is revenue times the margin, and dividends follow the payout ratio. Book value rolls forward. Residual income is net income minus the cost of equity on beginning book value.</p>',
        unsafe_allow_html=True,
    )
    if anchors is None:
        st.error(st.session_state.get("anchor_error") or "The forecast cannot start from these statements.")
        _footer(company)
        return

    fcy = company["financial_currency"]
    currency = company["currency"]
    comparable = currency == fcy

    with st.container(border=True):
        st.markdown("**Assumptions**")
        st.caption("Edit any input. The value updates immediately. Reset restores this company’s history and an 8% cost of equity.")
        a, b, c = st.columns(3)
        with a:
            _mark("field")
            st.number_input("Revenue growth (%)", min_value=-30.0, max_value=40.0, value=float(st.session_state.rev_g), step=0.1, key="rev_g", help="Applied every forecast year to the latest fiscal-year revenue.")
            st.markdown(f'<span class="anchor">{anchors.growth_label}: {pct(anchors.revenue_growth)}</span>', unsafe_allow_html=True)
            if anchors.yoy_growth is not None:
                st.caption(f"Latest year-on-year: {pct(anchors.yoy_growth, signed=True)}")
        with b:
            _mark("field")
            st.number_input("Net income margin (%)", min_value=-20.0, max_value=60.0, value=float(st.session_state.margin), step=0.1, key="margin", help="Net income as a percentage of revenue in every forecast year.")
            st.markdown(f'<span class="anchor">{anchors.margin_label}: {pct(anchors.net_margin)}</span>', unsafe_allow_html=True)
            if anchors.latest_margin is not None:
                st.caption(f"Latest year: {pct(anchors.latest_margin)}")
        with c:
            _mark("field")
            st.number_input("Payout ratio (%)", min_value=0.0, max_value=100.0, value=float(st.session_state.payout), step=0.1, key="payout", help="Dividends as a percentage of positive net income. Losses pay no dividend in this model.")
            st.markdown(f'<span class="anchor">{anchors.payout_label}: {pct(anchors.payout)}</span>', unsafe_allow_html=True)
            if anchors.latest_payout is not None:
                st.caption(f"Latest year: {pct(anchors.latest_payout)}")
        d, e, f = st.columns(3)
        with d:
            _mark("field")
            st.number_input("Cost of equity (%)", min_value=3.0, max_value=20.0, value=float(st.session_state.coe), step=0.1, key="coe", help="Discount rate for residual income. Default is 8%, not a CAPM estimate.")
            st.caption("Manual assumption, default 8%.")
        with e:
            _mark("field")
            st.number_input("Terminal growth (%)", min_value=0.0, max_value=6.0, value=float(st.session_state.tg), step=0.1, key="tg", help="Perpetual growth of residual income after the explicit forecast. Must stay below the cost of equity.")
            st.caption("Gordon growth after the explicit forecast.")
        with f:
            _mark("field")
            st.slider("Forecast period (years)", min_value=3, max_value=10, value=int(st.session_state.years), key="years")
            st.caption(f"Base year FY{anchors.base_year.year}.")
        st.button("Reset to history", on_click=_set_assumptions, args=(anchors,))

    for note in anchors.notes:
        st.info(note)

    with st.expander("How the value per share is calculated"):
        base_revenue = money(anchors.base_revenue, fcy).replace("$", "\\$")
        base_book = money(anchors.base_book, fcy).replace("$", "\\$")
        st.markdown(
            f"""
            The base year is **FY{anchors.base_year.year}**: revenue {base_revenue} and book value {base_book}.

            - Revenue in year t grows at the revenue-growth rate.
            - Net income = revenue × net income margin.
            - Dividends = payout × net income when net income is positive, otherwise zero.
            - Ending book value = beginning book value + net income − dividends.
            - Residual income = net income − (cost of equity × beginning book value).
            - Terminal value = final residual income × (1 + terminal growth) / (cost of equity − terminal growth).
            - Equity value = current book value + present value of each residual income + present value of the terminal value.
            - Value per share = equity value / shares. Shares are market cap divided by the share price ({_shares(company)}), so they match the market capitalisation.
            """
        )

    result, error = _solve(company, anchors)
    if error:
        st.error(error)
        _footer(company)
        return
    for warning in result.warnings:
        st.warning(warning)

    upside = (result.value_per_share / company["price"] - 1) if comparable and company["price"] else None
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _kpi("Implied value / share", per_share(result.value_per_share, fcy), assignment=True)
    with k2:
        _kpi("Market price", per_share(company["price"], currency) if comparable else "Different currency", assignment=True)
    with k3:
        _kpi("Premium / (discount)", pct(upside, signed=True) if upside is not None else "—")
    with k4:
        _kpi("Equity value", money(result.equity_value, fcy))

    left, right = st.columns(2)
    with left:
        _mark()
        _chart(
            waterfall(
                result.book0 / result.shares,
                result.pv_ri / result.shares,
                result.pv_terminal / result.shares,
                result.value_per_share,
                fcy,
            )
        )
    with right:
        if comparable:
            _mark()
            _chart(
                market_comparison(
                    ["Market price", "Residual income"],
                    [company["price"], result.value_per_share],
                    company["price"],
                    currency,
                )
            )
        else:
            st.info(f"The residual-income value is in {fcy}. It is not plotted against the {currency} share price.")

    forecast = result.forecast
    view = pd.DataFrame(
        {
            "Year": [f"FY{int(y)}" for y in forecast["year"]],
            "Revenue": [money(v, fcy) for v in forecast["revenue"]],
            "Net income": [money(v, fcy) for v in forecast["net_income"]],
            "Margin": [pct(v / r) if r else "—" for v, r in zip(forecast["net_income"], forecast["revenue"])],
            "Dividends": [money(v, fcy) for v in forecast["dividends"]],
            "Beginning book": [money(v, fcy) for v in forecast["bv_begin"]],
            "Ending book": [money(v, fcy) for v in forecast["bv_end"]],
            "Residual income": [money(v, fcy) for v in forecast["residual_income"]],
            "PV of residual income": [money(v, fcy) for v in forecast["pv_residual_income"]],
        }
    )
    _mark()
    st.dataframe(view, hide_index=True, use_container_width=True)
    summary = pd.DataFrame(
        {
            "Component": ["Book value today", "PV of residual income", "PV of terminal value", "Equity value", "Value per share"],
            "Amount": [
                money(result.book0, fcy),
                money(result.pv_ri, fcy),
                money(result.pv_terminal, fcy),
                money(result.equity_value, fcy),
                per_share(result.value_per_share, fcy),
            ],
        }
    )
    _mark()
    st.dataframe(summary, hide_index=True, use_container_width=True)
    st.download_button(
        "Download forecast",
        data=forecast.to_csv(index=False).encode("utf-8"),
        file_name=f"{company['ticker']}_residual_income.csv",
        mime="text/csv",
    )

    g1, g2 = st.columns(2)
    with g1:
        _mark()
        _chart(forecast_chart(forecast, fcy))
    with g2:
        _mark()
        _chart(book_and_ri_chart(forecast, fcy))

    st.markdown('<p class="kicker">Further metrics</p>', unsafe_allow_html=True)
    st.subheader("What drives the starting point")
    history = historical_metrics(company["annual"])
    if "revenue_growth" in history.columns and history["revenue_growth"].notna().any():
        _chart(yoy_growth_chart(history.dropna(subset=["revenue_growth"])))
    if not history.empty:
        drivers = pd.DataFrame(
            {
                "Year": [f"FY{idx.year}" for idx in history.index],
                "Revenue growth": [pct(v, signed=True) for v in history.get("revenue_growth", [])],
                "Net margin": [pct(v) for v in history.get("net_margin", [])],
                "Payout": [pct(v) for v in history.get("payout", [])],
                "ROE": [pct(v) for v in history.get("roe", [])],
            }
        )
        st.dataframe(drivers, hide_index=True, use_container_width=True)

    latest_roe = None
    if not history.empty and "roe" in history.columns and history["roe"].notna().any():
        latest_roe = float(history["roe"].dropna().iloc[-1])
    if latest_roe is not None:
        gap = latest_roe - result.cost_of_equity
        if gap >= 0:
            st.success(f"Latest ROE is {pct(latest_roe)}, {pct(gap)} above the {pct(result.cost_of_equity)} cost of equity. That spread is why residual income starts positive when the forecast margin holds.")
        else:
            st.warning(f"Latest ROE is {pct(latest_roe)}, {pct(abs(gap))} below the {pct(result.cost_of_equity)} cost of equity. Residual income stays negative unless the forecast margin earns the cost of capital.")

    st.subheader("Sensitivity")
    st.caption("Value per share when cost of equity and terminal growth move around the current inputs. The dot marks the case on screen. Cells are blank where terminal growth is not below the cost of equity.")
    grid = sensitivity_grid(
        lambda **kwargs: _builder(company, anchors)(**kwargs),
        result.cost_of_equity,
        result.terminal_growth,
    )
    _chart(sensitivity_heatmap(grid, fcy, result.cost_of_equity, result.terminal_growth))
    _footer(company)


def _football_rows(company: dict, anchors: Optional[Anchors], peers: list[dict]) -> list[dict]:
    rows = []
    if anchors is not None and "rev_g" in st.session_state:
        build = _builder(company, anchors)
        assumptions = _assumptions()
        try:
            current = build()
        except ValuationError:
            current = None
        if current is not None:
            band = growth_range(lambda growth: build(growth=growth), assumptions["growth"])
            low = high = current.value_per_share
            if band is not None:
                low, _mid, high = band
            rows.append(
                {
                    "method": "Residual income",
                    "low": min(low, high, current.value_per_share),
                    "mid": current.value_per_share,
                    "high": max(low, high, current.value_per_share),
                    "color": "#054696",
                    "detail": "Base case. Range is revenue growth ±2 percentage points.",
                    "support": "Clean surplus on reported book equity",
                }
            )
    subject = trading_multiples(company)
    for key, label, _short, color in MULTIPLE_META:
        dist = peer_distribution([peer.get(key) for peer in peers])
        if dist is None:
            continue
        prices = []
        for multiple_value in (dist["low"], dist["median"], dist["high"]):
            price = implied_price(multiple_value, key, company)
            if price is not None and price > 0:
                prices.append(price)
        mid = implied_price(dist["median"], key, company)
        if not prices or mid is None or mid <= 0:
            continue
        rows.append(
            {
                "method": label,
                "low": min(prices),
                "mid": mid,
                "high": max(prices),
                "color": color,
                "detail": f"{dist['method']} · {dist['count']} peers · median {multiple(dist['median'])}",
                "support": f"Subject trades at {multiple(subject.get(key))}",
            }
        )
    return rows


def _page_comps(company: dict, anchors: Optional[Anchors]) -> None:
    st.markdown('<p class="kicker">Assignment</p>', unsafe_allow_html=True)
    st.subheader("Trading comparables")
    st.markdown(
        '<p class="lede">Search Yahoo Finance and add peers from the same kind of menu as the company search. Medians of EV/Revenue, EV/EBITDA, P/E and P/Book are applied to this company’s trailing revenue, EBITDA, earnings and book value.</p>',
        unsafe_allow_html=True,
    )
    if company["sector"] in {"Financial Services", "Financial"}:
        st.info("For many financial companies, enterprise-value multiples are a weak comparison. Lean on P/E, P/Book and the residual-income value.")

    choice = _live_pick("Search peers", "peer_lookup", "peer_search")
    if st.session_state.get("peer_notice"):
        st.caption(st.session_state.peer_notice)
    if st.button("Add peer", disabled=choice is None):
        _add_peer(choice, company["ticker"])
    peers = _peer_symbols(company["ticker"])
    if st.session_state.get("peers"):
        for peer in list(st.session_state.peers):
            if peer["symbol"] == company["ticker"]:
                continue
            label_col, remove_col = st.columns([6, 1])
            exchange = f" · {peer['exchange']}" if peer.get("exchange") else ""
            label_col.markdown(f"**{peer['symbol']}** · {html.escape(peer['name'])}{html.escape(exchange)}")
            if remove_col.button("Remove", key=f"remove-{peer['symbol']}"):
                st.session_state.peers = [item for item in st.session_state.peers if item["symbol"] != peer["symbol"]]
                st.session_state.peer_notice = None
                st.rerun()
    if not peers:
        st.info("Add at least one peer to calculate the four multiples and the implied prices.")
        _footer(company)
        return

    with st.spinner("Loading peer data from Yahoo Finance…"):
        rows, errors = _peer_rows(company["ticker"], peers)
    for message in errors:
        st.warning(message)
    if not rows:
        st.error("None of the peer tickers returned usable market data.")
        _footer(company)
        return

    currency = company["currency"]
    subject = trading_multiples(company)
    st.markdown(f"**{company['ticker']} trailing multiples**")
    m1, m2, m3, m4 = st.columns(4)
    for col, (key, label, _short, _color) in zip((m1, m2, m3, m4), MULTIPLE_META):
        with col:
            _kpi(label, multiple(subject.get(key)), assignment=True)

    peer_table = pd.DataFrame(
        [
            {
                "Ticker": row["ticker"],
                "Company": row["name"],
                "Price": row["price"],
                "Market cap": row["market_cap"],
                "EV/Revenue": row.get("ev_revenue"),
                "EV/EBITDA": row.get("ev_ebitda"),
                "P/E": row.get("pe"),
                "P/Book": row.get("pb"),
            }
            for row in rows
        ]
    )
    _mark()
    st.dataframe(
        peer_table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="%.2f"),
            "Market cap": st.column_config.NumberColumn(format="%,.0f"),
            "EV/Revenue": st.column_config.NumberColumn(format="%.1f"),
            "EV/EBITDA": st.column_config.NumberColumn(format="%.1f"),
            "P/E": st.column_config.NumberColumn(format="%.1f"),
            "P/Book": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    charts = st.columns(2)
    for index, (key, label, _short, _color) in enumerate(MULTIPLE_META):
        names = [company["ticker"]] + [row["ticker"] for row in rows]
        values = [subject.get(key)] + [row.get(key) for row in rows]
        paired = [(name, value) for name, value in zip(names, values) if finite(value) is not None and value > 0]
        dist = peer_distribution([row.get(key) for row in rows])
        with charts[index % 2]:
            if not paired:
                st.info(f"{label} is unavailable. The metric is missing or not positive.")
                continue
            _mark()
            _chart(
                multiple_bars(
                    [name for name, _value in paired],
                    [value for _name, value in paired],
                    company["ticker"],
                    dist["median"] if dist else None,
                    label,
                )
            )

    implied_rows = []
    for key, label, _short, _color in MULTIPLE_META:
        dist = peer_distribution([row.get(key) for row in rows])
        price = implied_price(dist["median"], key, company) if dist else None
        vs_market = (price / company["price"] - 1) if price and company["price"] and company["currency"] == company["financial_currency"] else None
        implied_rows.append(
            {
                "Method": label,
                "Median multiple": multiple(dist["median"]) if dist else "—",
                "Peers": dist["count"] if dist else 0,
                "Band": dist["method"] if dist else "—",
                "Implied price": per_share(price, currency) if price else "—",
                "vs market": pct(vs_market, signed=True) if vs_market is not None else "—",
            }
        )
    st.markdown("**Implied price from the peer median**")
    _mark()
    st.dataframe(pd.DataFrame(implied_rows), hide_index=True, use_container_width=True)
    with st.expander("How a multiple becomes a price"):
        net_debt = money(company.get("net_debt"), currency).replace("$", "\\$")
        st.markdown(
            f"""
            - EV/Revenue and EV/EBITDA: implied enterprise value = multiple × the company’s trailing metric. Equity value = enterprise value − net debt. Net debt here is Yahoo’s enterprise value minus market cap ({net_debt}), so the company’s own multiple comes back to today’s equity value.
            - P/E: implied price = multiple × trailing EPS.
            - P/Book: implied price = multiple × book value per share.
            - Negative or missing metrics are left out. The subject company is not part of the median.
            """
        )

    st.markdown('<p class="kicker">Further metrics</p>', unsafe_allow_html=True)
    st.subheader("Premium or discount to the peer median")
    premium_bits = []
    cols = st.columns(4)
    for col, (key, label, _short, _color) in zip(cols, MULTIPLE_META):
        dist = peer_distribution([row.get(key) for row in rows])
        own = subject.get(key)
        if dist is None or own is None or dist["median"] == 0:
            with col:
                _kpi(label, "—", assignment=True)
            continue
        gap = own / dist["median"] - 1
        with col:
            _kpi(label, f"{multiple(own)} vs {multiple(dist['median'])}", assignment=True, delta=pct(gap, signed=True))
        premium_bits.append(gap)
    st.caption("A positive figure means the subject company trades richer than the peer median on that multiple.")
    _ = anchors
    _footer(company)


def _page_football(company: dict, anchors: Optional[Anchors]) -> None:
    st.markdown('<p class="kicker">Assignment</p>', unsafe_allow_html=True)
    st.subheader("Football field")
    st.markdown(
        '<p class="lede">Residual income and the comparables on one range, with the Yahoo Finance price marked through the chart. Diamonds are the values actually applied: the residual-income base case, and the peer median for each multiple.</p>',
        unsafe_allow_html=True,
    )
    peers = _peer_symbols(company["ticker"])
    peer_rows = []
    if peers:
        with st.spinner("Updating comparables…"):
            peer_rows, errors = _peer_rows(company["ticker"], peers)
        for message in errors:
            st.warning(message)
    elif anchors is not None:
        st.info("The range below is residual income only. Add peer tickers on Trading Comparables to bring in the four multiples.")

    if company["currency"] != company["financial_currency"]:
        st.warning("Statement currency and trading currency differ, so this range is not shown against the market price.")
        _footer(company)
        return

    rows = _football_rows(company, anchors, peer_rows)
    if not rows:
        st.error("No valuation could be drawn. Check the residual-income assumptions, or add peers with positive multiples.")
        _footer(company)
        return

    _mark()
    _chart(football_field(rows, company["price"], company["currency"]))
    table = pd.DataFrame(
        [
            {
                "Method": row["method"],
                "Low": per_share(row["low"], company["currency"]),
                "Applied": per_share(row["mid"], company["currency"]),
                "High": per_share(row["high"], company["currency"]),
                "vs market": pct(row["mid"] / company["price"] - 1, signed=True),
                "What the range is": row["detail"],
            }
            for row in rows
        ]
    )
    _mark()
    st.dataframe(table, hide_index=True, use_container_width=True)

    st.markdown('<p class="kicker">Further metrics</p>', unsafe_allow_html=True)
    st.subheader("Where the market price sits")
    applied = [row["mid"] for row in rows]
    low = min(row["low"] for row in rows)
    high = max(row["high"] for row in rows)
    price = company["price"]
    above = sum(1 for value in applied if value > price)
    c1, c2, c3 = st.columns(3)
    with c1:
        _kpi("Lowest point", per_share(low, company["currency"]), assignment=True)
    with c2:
        _kpi("Highest point", per_share(high, company["currency"]), assignment=True)
    with c3:
        _kpi("Methods above the price", f"{above} of {len(applied)}")
    low_label = per_share(low, company["currency"]).replace("$", "\\$")
    high_label = per_share(high, company["currency"]).replace("$", "\\$")
    market_label = per_share(price, company["currency"]).replace("$", "\\$")
    if price < low:
        st.info(f"The market price {market_label} sits below every low end in this range.")
    elif price > high:
        st.info(f"The market price {market_label} sits above every high end in this range.")
    else:
        st.success(f"The market price {market_label} sits inside the span from {low_label} to {high_label}.")
    st.caption("The span mixes a fundamental value with market multiples. It is a way to see disagreement across methods, not a weighted target price.")
    _footer(company)


def main() -> None:
    _init()
    _sidebar()
    company = st.session_state.get("company")
    if not company:
        _landing()
        return
    _hero(company)
    page = st.session_state.page
    anchors = st.session_state.get("anchors")
    if page == "Overview":
        _page_overview(company)
    elif page == "Residual Income":
        _page_residual(company, anchors)
    elif page == "Trading Comparables":
        _page_comps(company, anchors)
    else:
        _page_football(company, anchors)


main()
