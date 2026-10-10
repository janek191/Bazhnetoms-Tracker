"""WHU – Otto Beisheim School of Management visual tokens.

Hex values follow the WHU brand style guide (styleguide.whu.edu):
primary WHU Blue and WHU Light Blue, secondary silver and anthracite,
highlight petrol, and WHU Orange for calls to action.
"""

from __future__ import annotations

import math
from typing import Optional

WHU_BLUE = "#054696"
WHU_LIGHT = "#00A5DC"
ALT_BLUE = "#1E2F78"
PETROL = "#00AAB9"
DARK_PETROL = "#006E78"
ORANGE = "#EB5A0A"
GREEN = "#1CAD4B"
YELLOW = "#FFE600"
SILVER = "#E6EBF0"
ANTHRACITE = "#505459"
INK = "#1A1D21"
CANVAS = "#F4F7FB"
WHITE = "#FFFFFF"

FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif'

PLOTLY_COLORWAY = [WHU_BLUE, WHU_LIGHT, DARK_PETROL, PETROL, ALT_BLUE, GREEN]

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CHF": "CHF ",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
    "SEK": "SEK ",
    "NOK": "NOK ",
    "DKK": "DKK ",
    "HKD": "HK$",
}


def finite(value) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def symbol(currency: Optional[str]) -> str:
    if not currency:
        return ""
    return CURRENCY_SYMBOLS.get(currency.upper(), f"{currency} ")


def money(value, currency: Optional[str] = "USD", digits: int = 2) -> str:
    number = finite(value)
    if number is None:
        return "—"
    sign = "−" if number < 0 else ""
    magnitude = abs(number)
    unit = symbol(currency)
    if magnitude >= 1e12:
        return f"{sign}{unit}{magnitude / 1e12:.2f}tn"
    if magnitude >= 1e9:
        return f"{sign}{unit}{magnitude / 1e9:.2f}bn"
    if magnitude >= 1e6:
        return f"{sign}{unit}{magnitude / 1e6:.1f}m"
    return f"{sign}{unit}{magnitude:,.{digits}f}"


def per_share(value, currency: Optional[str] = "USD") -> str:
    number = finite(value)
    if number is None:
        return "—"
    sign = "−" if number < 0 else ""
    return f"{sign}{symbol(currency)}{abs(number):,.2f}"


def pct(value, digits: int = 1, signed: bool = False) -> str:
    number = finite(value)
    if number is None:
        return "—"
    if signed and number > 0:
        return f"+{number * 100:.{digits}f}%"
    return f"{number * 100:.{digits}f}%"


def multiple(value) -> str:
    number = finite(value)
    if number is None:
        return "—"
    return f"{number:.1f}x"


def compact_number(value, digits: int = 1) -> str:
    number = finite(value)
    if number is None:
        return "—"
    sign = "−" if number < 0 else ""
    magnitude = abs(number)
    if magnitude >= 1e12:
        return f"{sign}{magnitude / 1e12:.2f}tn"
    if magnitude >= 1e9:
        return f"{sign}{magnitude / 1e9:.2f}bn"
    if magnitude >= 1e6:
        return f"{sign}{magnitude / 1e6:.{digits}f}m"
    if magnitude >= 1e3:
        return f"{sign}{magnitude / 1e3:.1f}k"
    return f"{sign}{magnitude:,.0f}"


CSS = f"""
html, body, [class*="css"] {{
    font-family: {FONT};
}}
.stApp {{
    background: {CANVAS};
    color: {INK};
}}
h1, h2, h3, h4 {{
    font-family: {FONT};
    color: {WHU_BLUE};
    letter-spacing: -0.02em;
    font-weight: 700;
}}
p, li, label {{
    font-family: {FONT};
}}
.brand {{
    padding: 0.1rem 0 0.35rem 0;
}}
.brand-credit {{
    font-size: 0.78rem;
    line-height: 1.35;
    color: {INK};
    font-weight: 600;
}}
.brand-school {{
    margin-top: 0.15rem;
    font-size: 0.72rem;
    line-height: 1.35;
    color: {ANTHRACITE};
}}
.hero {{
    background: {WHITE};
    color: {INK};
    border: 1px solid {SILVER};
    border-top: 3px solid {WHU_BLUE};
    border-radius: 12px;
    padding: 0.95rem 1.15rem 0.85rem 1.15rem;
    margin-bottom: 0.9rem;
}}
.hero-title {{
    color: {INK};
    font-size: 1.55rem;
    line-height: 1.15;
    font-weight: 700;
    margin: 0 0 0.2rem 0;
    letter-spacing: -0.02em;
}}
.hero-meta {{
    margin: 0;
    font-size: 0.9rem;
    color: {ANTHRACITE};
}}
.hero-price {{
    color: {WHU_BLUE};
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin: 0.4rem 0 0 0;
    font-variant-numeric: tabular-nums;
}}
.hero-change {{
    font-size: 0.95rem;
    font-weight: 600;
    margin-left: 0.45rem;
}}
.hero-change.up {{ color: {GREEN}; }}
.hero-change.down {{ color: {ORANGE}; }}
.kicker {{
    color: {DARK_PETROL};
    font-size: 0.72rem;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    font-weight: 700;
    margin: 0.35rem 0 0 0;
}}
.lede {{
    color: {ANTHRACITE};
    font-size: 0.98rem;
    line-height: 1.45;
    margin-top: 0.15rem;
}}
.footnote {{
    color: {ANTHRACITE};
    font-size: 0.78rem;
    line-height: 1.45;
    margin-top: 1.2rem;
}}
.anchor {{
    display: inline-block;
    background: {SILVER};
    color: {WHU_BLUE};
    border-radius: 999px;
    padding: 0.12rem 0.55rem;
    font-size: 0.75rem;
    font-weight: 600;
    margin-top: 0.15rem;
}}
div[data-testid="stMetric"] {{
    background: white;
    border: 1px solid {SILVER};
    border-radius: 12px;
    padding: 0.7rem 0.85rem 0.55rem 0.85rem;
}}
div[data-testid="stMetricLabel"] {{
    color: {ANTHRACITE};
    font-size: 0.8rem;
}}
div[data-testid="stMetricValue"] {{
    color: {WHU_BLUE};
    font-variant-numeric: tabular-nums;
    font-size: 1.35rem;
}}
div[data-testid="stButton"] > button[kind="primary"] {{
    background: {ORANGE};
    border: none;
    color: white;
    font-weight: 700;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover {{
    background: #d15109;
    color: white;
}}
div[data-testid="stButton"] > button[kind="primary"]:disabled {{
    background: #E6EBF0;
    color: #8A9096;
}}
div[data-testid="stCustomComponentV1"] iframe {{
    border: none;
    color-scheme: light;
}}
div[data-testid="stButton"] > button[kind="secondary"] {{
    border-color: {WHU_BLUE};
    color: {WHU_BLUE};
    font-weight: 600;
}}
hr {{
    border: none;
    border-top: 1px solid {SILVER};
}}
.news-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 0.75rem;
    margin: 0.35rem 0 1.1rem 0;
}}
.news-card {{
    display: block;
    background: {WHITE};
    border: 1px solid {SILVER};
    border-radius: 12px;
    padding: 0.9rem 1rem 0.85rem 1rem;
    text-decoration: none;
    min-height: 7.2rem;
}}
.news-card:hover {{
    border-color: {WHU_BLUE};
}}
.news-source {{
    color: {DARK_PETROL};
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}
.news-title {{
    color: {INK};
    font-size: 0.98rem;
    font-weight: 650;
    line-height: 1.35;
    margin-top: 0.35rem;
}}
.news-time {{
    color: {ANTHRACITE};
    font-size: 0.78rem;
    margin-top: 0.55rem;
}}
.guide {{
    background: linear-gradient(155deg, {WHU_BLUE} 0%, {ALT_BLUE} 100%);
    color: white;
    border-radius: 14px;
    padding: 1.35rem 1.45rem 1.25rem;
    margin-bottom: 1.15rem;
}}
.guide-kicker {{
    margin: 0;
    color: {WHU_LIGHT};
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}
.guide h2 {{
    margin: 0.35rem 0 0.45rem;
    color: white;
    font-size: 1.7rem;
    line-height: 1.15;
    letter-spacing: -0.02em;
}}
.guide-lead {{
    margin: 0;
    max-width: 46rem;
    color: rgba(255, 255, 255, 0.9);
    font-size: 1rem;
    line-height: 1.45;
}}
.guide-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.1rem;
    margin-top: 1.15rem;
}}
.guide h3 {{
    margin: 0 0 0.4rem;
    color: white;
    font-size: 0.95rem;
}}
.guide p, .guide li {{
    color: rgba(255, 255, 255, 0.9);
    font-size: 0.9rem;
    line-height: 1.45;
}}
.guide ol, .guide ul {{
    margin: 0;
    padding-left: 1.15rem;
}}
.guide li + li {{
    margin-top: 0.35rem;
}}
.guide strong {{
    color: white;
    font-weight: 700;
}}
.guide-bang {{
    position: relative;
    display: inline-block;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #E10600;
    color: white;
    font-size: 11px;
    font-weight: 700;
    line-height: 16px;
    text-align: center;
    vertical-align: -2px;
    cursor: help;
}}
.assign-flag, .assign-anchor {{
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 6;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #E10600;
    color: white;
    font-size: 11px;
    font-weight: 700;
    line-height: 16px;
    text-align: center;
    cursor: help;
}}
.assign-flag::after, .assign-anchor::after, .guide-bang::after {{
    content: "Relevant KPI's from Assignment";
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 40;
    width: max-content;
    max-width: 16rem;
    height: auto;
    padding: 0.45rem 0.75rem;
    border-radius: 0.5rem;
    background: #262730;
    color: #FAFAFA;
    font-size: 0.875rem;
    font-weight: 400;
    line-height: 1.45;
    letter-spacing: 0;
    text-align: left;
    white-space: nowrap;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
}}
.assign-flag:hover::after, .assign-anchor:hover::after, .guide-bang:hover::after {{
    opacity: 1;
    visibility: visible;
}}
div[data-testid="stColumn"]:has(.assign-flag),
div[data-testid="stColumn"]:has(.assign-anchor),
div[data-testid="stVerticalBlock"]:has(.assign-flag),
div[data-testid="stVerticalBlock"]:has(.assign-anchor) {{
    overflow: visible;
}}
div[data-testid="stElementContainer"]:has(.assign-anchor) {{
    position: relative;
    height: 0;
    min-height: 0;
    margin: 0;
    padding: 0;
    overflow: visible;
    z-index: 6;
}}
div[data-testid="stElementContainer"]:has(.assign-anchor.field) + div[data-testid="stElementContainer"] [data-testid="stWidgetLabel"] {{
    width: fit-content;
    max-width: calc(100% - 1.7rem);
}}
div[data-testid="stElementContainer"]:has(.assign-anchor.field) + div[data-testid="stElementContainer"] [data-testid="stTooltipIcon"] {{
    margin-left: 0.15em;
}}
.kpi {{
    position: relative;
    background: white;
    border: 1px solid {SILVER};
    border-radius: 12px;
    padding: 0.7rem 0.85rem 0.6rem 0.85rem;
    min-height: 5.15rem;
}}
.kpi-label {{
    color: {ANTHRACITE};
    font-size: 0.8rem;
    padding-right: 1.1rem;
}}
.kpi-value {{
    color: {WHU_BLUE};
    font-variant-numeric: tabular-nums;
    font-size: 1.35rem;
    font-weight: 650;
    line-height: 1.25;
    margin-top: 0.2rem;
}}
.kpi-delta {{
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: 0.2rem;
}}
.kpi-delta.up {{ color: {GREEN}; }}
.kpi-delta.down {{ color: #E10600; }}
.hero {{
    position: relative;
}}
@media (max-width: 720px) {{
    .hero-title {{ font-size: 1.35rem; }}
    .hero-price {{ font-size: 1.45rem; }}
    .guide h2 {{ font-size: 1.35rem; }}
    .guide-grid {{ grid-template-columns: 1fr; }}
}}
"""
