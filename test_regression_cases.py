"""Run with: python test_regression_cases.py"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests


GOLDEN_DIR = Path("data/golden_cases")
API_BASE = os.environ.get("AEGIS_TEST_URL", "http://localhost:3000")


def test_case(filename: str) -> None:
    with (GOLDEN_DIR / filename).open("r", encoding="utf-8") as f:
        case = json.load(f)

    res = requests.post(
        f"{API_BASE}/api/valuation",
        json={"ticker": case["ticker"], "assumptions": case["assumptions"]},
        timeout=30,
    )
    res.raise_for_status()
    out = res.json()

    wfv = out["weighted_fair_value"]
    lo, hi = case["expected_output"]["weighted_fair_value_range"]
    tol = case["tolerance_pct"] / 100
    assert lo * (1 - tol) <= wfv <= hi * (1 + tol), (
        f"REGRESSION FAIL {case['ticker']}: got {wfv}, expected {lo}-{hi}"
    )

    bear = out["scenario_matrix"][0]["price"]
    bear_lo, bear_hi = case["expected_output"]["bear_price_range"]
    assert bear_lo * (1 - tol) <= bear <= bear_hi * (1 + tol), (
        f"REGRESSION FAIL {case['ticker']}: bear got {bear}, expected {bear_lo}-{bear_hi}"
    )

    min_overvalued = case["expected_output"]["overvalued_pct_min"]
    assert out["overvalued_pct"] >= min_overvalued, (
        f"REGRESSION FAIL {case['ticker']}: overvalued {out['overvalued_pct']} < {min_overvalued}"
    )

    print(f"OK {case['ticker']} - WFV ${wfv} within [{lo}, {hi}]")


if __name__ == "__main__":
    for path in sorted(GOLDEN_DIR.glob("*.json")):
        test_case(path.name)
    print("\nAll regression cases passed.")
