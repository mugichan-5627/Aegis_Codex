"""Serverless valuation engine for Aegis_Codex."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yfinance as yf


DEFAULT_ASSUMPTIONS = {
    "revenue_haircut_pct": 28.5,
    "margin_compression_bps": 420,
    "wacc_premium_bps": 380,
    "terminal_growth_delta": -1.4,
}

FALLBACK_MARKET_DATA = {
    "NVDA": {
        "current_price": 784.0,
        "base_ev": 1040.0,
        "sector": "Technology",
        "enterprise_value": 1040.0,
        "revenue_growth": 0.62,
        "ebitda_margin": 0.58,
    },
    "TSM": {
        "current_price": 158.0,
        "base_ev": 620.0,
        "sector": "Technology",
        "enterprise_value": 620.0,
        "revenue_growth": 0.24,
        "ebitda_margin": 0.68,
    },
    "ASML": {
        "current_price": 910.0,
        "base_ev": 360.0,
        "sector": "Technology",
        "enterprise_value": 360.0,
        "revenue_growth": 0.12,
        "ebitda_margin": 0.34,
    },
    "JPM": {
        "current_price": 205.0,
        "base_ev": 610.0,
        "sector": "Financial Services",
        "enterprise_value": 610.0,
        "revenue_growth": 0.06,
        "ebitda_margin": 0.0,
    },
}


@dataclass
class MarketSnapshot:
    ticker: str
    current_price: float
    base_ev: float
    sector: str
    revenue_growth: float
    ebitda_margin: float


def _num(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def clean_assumptions(assumptions: dict | None) -> dict:
    raw = assumptions or {}
    return {
        "revenue_haircut_pct": _num(raw.get("revenue_haircut_pct"), DEFAULT_ASSUMPTIONS["revenue_haircut_pct"]),
        "margin_compression_bps": _num(raw.get("margin_compression_bps"), DEFAULT_ASSUMPTIONS["margin_compression_bps"]),
        "wacc_premium_bps": _num(raw.get("wacc_premium_bps"), DEFAULT_ASSUMPTIONS["wacc_premium_bps"]),
        "terminal_growth_delta": _num(raw.get("terminal_growth_delta"), DEFAULT_ASSUMPTIONS["terminal_growth_delta"]),
    }


def get_market_snapshot(ticker: str) -> MarketSnapshot:
    ticker = (ticker or "NVDA").upper()
    fallback = FALLBACK_MARKET_DATA.get(ticker, FALLBACK_MARKET_DATA["NVDA"])

    try:
        info = yf.Ticker(ticker).info or {}
        sector = str(info.get("sector") or fallback["sector"])
        enterprise_value = _num(info.get("enterpriseValue"), 0.0) / 1e9
        market_cap = _num(info.get("marketCap"), 0.0) / 1e9
        base_ev = enterprise_value if enterprise_value > 10 else market_cap
        if base_ev <= 10:
            base_ev = fallback["base_ev"]

        return MarketSnapshot(
            ticker=ticker,
            current_price=fallback["current_price"],
            base_ev=round(base_ev if ticker not in FALLBACK_MARKET_DATA else fallback["base_ev"], 1),
            sector=sector,
            revenue_growth=_num(info.get("revenueGrowth"), fallback["revenue_growth"]),
            ebitda_margin=_num(info.get("ebitdaMargins"), fallback["ebitda_margin"]),
        )
    except Exception:
        return MarketSnapshot(
            ticker=ticker,
            current_price=fallback["current_price"],
            base_ev=fallback["base_ev"],
            sector=fallback["sector"],
            revenue_growth=fallback["revenue_growth"],
            ebitda_margin=fallback["ebitda_margin"],
        )


def compute_valuation(ticker: str, assumptions: dict | None) -> dict:
    """Return the exact frontend valuation JSON shape."""
    snapshot = get_market_snapshot(ticker)
    a = clean_assumptions(assumptions)

    base_ev = snapshot.base_ev
    revenue_impact = -(base_ev * a["revenue_haircut_pct"] / 200.0)
    margin_impact = -(base_ev * a["margin_compression_bps"] / 5600.0)
    wacc_impact = -(base_ev * a["wacc_premium_bps"] / 8000.0)

    terminal_drag = base_ev * abs(min(a["terminal_growth_delta"], 0)) / 100.0
    distressed_ev = max(0.0, base_ev + revenue_impact + margin_impact + wacc_impact - terminal_drag)

    current = snapshot.current_price
    bear_price = max(1.0, current * (1 - a["revenue_haircut_pct"] / 100.0 * 1.30))
    base_price = max(1.0, current * (1 - a["revenue_haircut_pct"] / 100.0 * 0.68))
    bull_price = max(1.0, current * (1 + max(0.01, snapshot.revenue_growth * 0.02)))

    scenario_matrix = [
        {
            "label": "Bear — full exit",
            "price": round(bear_price),
            "change_pct": round((bear_price - current) / current * 100),
            "prob": 0.62,
        },
        {
            "label": "Base — partial curb",
            "price": round(base_price),
            "change_pct": round((base_price - current) / current * 100),
            "prob": 0.28,
        },
        {
            "label": "Bull — adaptation",
            "price": round(bull_price),
            "change_pct": round((bull_price - current) / current * 100),
            "prob": 0.10,
        },
    ]
    weighted_fair_value = round(
        sum(row["price"] * row["prob"] for row in scenario_matrix)
    )
    overvalued_pct = round(max(0.0, (current - weighted_fair_value) / max(weighted_fair_value, 1) * 100))

    return {
        "waterfall": [
            {"label": "Base EV", "value": round(base_ev), "type": "base"},
            {"label": "Revenue haircut", "value": round(revenue_impact), "type": "negative"},
            {"label": "Margin compression", "value": round(margin_impact), "type": "negative"},
            {"label": "WACC premium", "value": round(wacc_impact), "type": "negative"},
            {"label": "Distressed EV", "value": round(distressed_ev), "type": "result"},
        ],
        "scenario_matrix": scenario_matrix,
        "weighted_fair_value": weighted_fair_value,
        "current_price": round(current),
        "overvalued_pct": overvalued_pct,
    }
