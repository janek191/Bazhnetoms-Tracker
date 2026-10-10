"""Yahoo Finance market data and annual financial statements."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import yfinance as yf

from brand import finite


INCOME_ROWS = {
    "revenue": ["Total Revenue"],
    "gross_profit": ["Gross Profit"],
    "operating_income": ["Operating Income"],
    "ebitda": ["EBITDA"],
    "net_income": ["Net Income Common Stockholders", "Net Income"],
    "diluted_shares": ["Diluted Average Shares"],
}

BALANCE_ROWS = {
    "equity": ["Stockholders Equity", "Common Stock Equity"],
    "total_assets": ["Total Assets"],
    "total_debt": ["Total Debt"],
    "cash": ["Cash And Cash Equivalents"],
    "ordinary_shares": ["Ordinary Shares Number"],
}

CASHFLOW_ROWS = {
    "dividends": ["Common Stock Dividend Paid", "Cash Dividends Paid"],
    "free_cash_flow": ["Free Cash Flow"],
}


class MarketDataError(Exception):
    """Raised when a ticker cannot be resolved on Yahoo Finance."""


def _pick_row(frame: Optional[pd.DataFrame], names: list[str]) -> Optional[pd.Series]:
    if frame is None or frame.empty:
        return None
    lookup = {}
    for idx in frame.index:
        lookup.setdefault(str(idx).strip().lower(), idx)
    for name in names:
        key = name.strip().lower()
        if key not in lookup:
            continue
        row = frame.loc[lookup[key]]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        values = pd.to_numeric(row, errors="coerce")
        values.index = pd.to_datetime(values.index, errors="coerce")
        values = values[values.index.notna()]
        values = values[~values.index.duplicated(keep="first")].sort_index()
        return values
    return None


def _annual_statements(ticker: yf.Ticker) -> pd.DataFrame:
    income = ticker.financials
    balance = ticker.balance_sheet
    cashflow = ticker.cashflow
    columns = {}
    for mapping, statement in (
        (INCOME_ROWS, income),
        (BALANCE_ROWS, balance),
        (CASHFLOW_ROWS, cashflow),
    ):
        for column, names in mapping.items():
            series = _pick_row(statement, names)
            if series is not None:
                columns[column] = series
    if not columns:
        return pd.DataFrame()
    annual = pd.DataFrame(columns)
    annual.index.name = "period"
    if "dividends" in annual.columns:
        annual["dividends"] = annual["dividends"].abs()
    annual = annual.sort_index()
    annual = annual.dropna(how="all")
    return annual


def _history(ticker: yf.Ticker) -> pd.DataFrame:
    history = ticker.history(period="5y", auto_adjust=True)
    if history is None or history.empty or "Close" not in history.columns:
        return pd.DataFrame(columns=["date", "close"])
    frame = history[["Close"]].rename(columns={"Close": "close"}).reset_index()
    date_col = "Date" if "Date" in frame.columns else frame.columns[0]
    frame["date"] = pd.to_datetime(frame[date_col]).dt.tz_localize(None)
    frame = frame[["date", "close"]].dropna()
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    return frame.dropna().sort_values("date")


def load_quote(symbol: str) -> dict:
    """Current market snapshot used for the subject company and for peers."""
    ticker_symbol = symbol.strip().upper()
    if not ticker_symbol:
        raise MarketDataError("Enter a ticker symbol.")
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info or {}
    except Exception as exc:  # noqa: BLE001 - yfinance raises several client errors
        raise MarketDataError(f"Yahoo Finance did not return data for {ticker_symbol}.") from exc

    price = finite(info.get("currentPrice"))
    if price is None:
        price = finite(info.get("regularMarketPrice"))
    previous = finite(info.get("previousClose"))
    market_cap = finite(info.get("marketCap"))
    enterprise_value = finite(info.get("enterpriseValue"))
    name = info.get("longName") or info.get("shortName")

    if price is None or market_cap is None or not name:
        raise MarketDataError(
            f"No listed-company data for '{ticker_symbol}'. "
            "Check the symbol. Non-US listings need the exchange suffix, for example SAP.DE or AIR.PA."
        )

    shares = market_cap / price if price else None
    net_debt = None
    if enterprise_value is not None and market_cap is not None:
        net_debt = enterprise_value - market_cap

    book_ps = finite(info.get("bookValue"))
    eps = finite(info.get("trailingEps"))
    revenue = finite(info.get("totalRevenue"))
    ebitda = finite(info.get("ebitda"))
    net_income = finite(info.get("netIncomeToCommon"))

    return {
        "ticker": ticker_symbol,
        "name": name,
        "sector": info.get("sector") or "—",
        "industry": info.get("industry") or "—",
        "exchange": info.get("exchange") or "—",
        "currency": info.get("currency") or info.get("financialCurrency") or "USD",
        "financial_currency": info.get("financialCurrency") or info.get("currency") or "USD",
        "price": price,
        "previous_close": previous,
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "shares": shares,
        "net_debt": net_debt,
        "beta": finite(info.get("beta")),
        "dividend_rate": finite(info.get("trailingAnnualDividendRate")),
        "week_high": finite(info.get("fiftyTwoWeekHigh")),
        "week_low": finite(info.get("fiftyTwoWeekLow")),
        "ttm_revenue": revenue,
        "ttm_ebitda": ebitda,
        "ttm_net_income": net_income,
        "ttm_eps": eps,
        "book_value_ps": book_ps,
        "book_equity": (book_ps * shares) if book_ps is not None and shares else None,
    }


def load_company(symbol: str) -> dict:
    """Quote, five-year price history and annual statements for the subject company."""
    ticker_symbol = symbol.strip().upper()
    quote = load_quote(ticker_symbol)
    ticker = yf.Ticker(ticker_symbol)
    annual = _annual_statements(ticker)
    history = _history(ticker)
    quote["annual"] = annual
    quote["history"] = history
    return quote


def search_listings(query: str, limit: int = 12) -> list[dict]:
    """Equities matching a name or ticker across the Yahoo Finance universe."""
    text = query.strip()
    if len(text) < 2:
        return []
    try:
        found = yf.Search(text, max_results=20, news_count=0)
    except Exception:
        return []
    quotes = list(found.quotes or [])
    equities = [quote for quote in quotes if quote.get("quoteType") == "EQUITY"]
    chosen = equities or quotes
    listings = []
    seen = set()
    for quote in chosen:
        symbol = str(quote.get("symbol") or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        listings.append(
            {
                "symbol": symbol,
                "name": quote.get("longname") or quote.get("shortname") or symbol,
                "exchange": quote.get("exchDisp") or quote.get("exchange") or "",
                "type": quote.get("typeDisp") or quote.get("quoteType") or "Equity",
            }
        )
        if len(listings) >= limit:
            break
    return listings


def market_news(limit: int = 8) -> list[dict]:
    """Recent English business headlines from Yahoo Finance."""
    stories = []
    seen = set()
    for topic in ("stock market", "economy", "interest rates", "Wall Street"):
        try:
            found = yf.Search(topic, max_results=1, news_count=8)
        except Exception:
            continue
        for story in found.news or []:
            title = str(story.get("title") or "").strip()
            link = str(story.get("link") or "")
            if not title or title.casefold() in seen or not link.startswith("https://"):
                continue
            seen.add(title.casefold())
            published = story.get("providerPublishTime")
            try:
                published_at = int(published) if published else None
            except (TypeError, ValueError):
                published_at = None
            stories.append(
                {
                    "title": title,
                    "publisher": story.get("publisher") or "Yahoo Finance",
                    "link": link,
                    "published_at": published_at,
                }
            )
            if len(stories) >= limit:
                stories.sort(key=lambda item: item["published_at"] or 0, reverse=True)
                return stories
    stories.sort(key=lambda item: item["published_at"] or 0, reverse=True)
    return stories
