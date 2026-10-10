"""Search box that lists Yahoo matches while the user is typing."""

from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component(
    "ticker_search",
    path=str(Path(__file__).parent / "ticker_search_ui"),
)


def ticker_search(label: str, query: str, results: list, key: str) -> dict:
    value = _component(
        label=label,
        query=query,
        results=results,
        key=key,
        default={"query": query, "symbol": None, "name": None, "exchange": None},
    )
    return value if isinstance(value, dict) else {"query": query, "symbol": None, "name": None, "exchange": None}
