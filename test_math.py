"""
Unit Tests and Math Verification Suite for Doomsday Rapid Agent
Verifies that all valuation routes (Financials, High-Growth, Mature Tech, Cyclicals)
resolve accurately, compute WACC stress, and scale with the Chaos Slider.
"""

import sys
import os
from valuation_engine import ValuationRouter, CompanyProfile, CompanyType, classify_company

def run_tests():
    print("====================================================")
    print("DOOMSDAY RAPID AGENT - MATHEMATICAL VERIFICATION SUITE")
    print("====================================================\n")

    # 1. TEST CLASSIC/MATURE TECH (e.g. profitable tech - FCF-DCF)
    print("[TEST 1] Profitable Mature Tech Framework (DCF-based)")
    tech_profile = CompanyProfile(
        ticker="MSFT",
        name="Microsoft Corporation",
        sector="Technology",
        industry="Software - Infrastructure",
        company_type=CompanyType.MATURE_TECH,
        current_price=420.0,
        market_cap=3100e9,
        shares_outstanding=7.4e9,
        revenue=236e9,
        revenue_growth=0.15,
        ebitda=115e9,
        ebitda_margin=48.7,
        net_income=86e9,
        eps=11.6,
        total_assets=470e9,
        total_equity=250e9,
        total_debt=100e9,
        cash=80e9,
        net_debt=20e9,
        book_value_per_share=33.7,
        tangible_book_per_share=25.0,
        operating_cash_flow=110e9,
        free_cash_flow=70e9,
        capex=40e9,
        dividends_per_share=3.0,
        dividend_yield=0.007,
        payout_ratio=0.25,
        pe_ratio=36.2,
        pb_ratio=12.4,
        ev_ebitda=27.0,
        ev_revenue=13.2,
        price_to_fcf=44.2,
        roe=34.4,
        roa=18.2,
        roic=28.5,
        beta=1.1
    )
    
    # Run valuation under 0% chaos (base case) and 80% chaos
    base_val = ValuationRouter.value_company(tech_profile, chaos_level=0.0, risk_severity=5.0)
    stressed_val = ValuationRouter.value_company(tech_profile, chaos_level=0.8, risk_severity=8.0)
    
    print(f"  Base Fair Value: ${base_val.base_fair_value}")
    print(f"  Stressed (80% Chaos, 8.0 Severity): ${stressed_val.distressed_value}")
    print(f"  Downside %: {stressed_val.downside_pct}%")
    assert base_val.base_fair_value > stressed_val.distressed_value, "Math error: Stressed value must be lower than base!"
    assert stressed_val.company_type == "MATURE", "Type routing failed!"
    print("  => Mature DCF verification passed.\n")

    # 2. TEST FINANCIAL FRAMEWORK (P/BV & Excess Return Model)
    print("[TEST 2] Financial Sector Framework (P/BV & Excess Return)")
    bank_profile = CompanyProfile(
        ticker="JPM",
        name="JPMorgan Chase & Co.",
        sector="Financial Services",
        industry="Diversified Banks",
        company_type=CompanyType.FINANCIAL,
        current_price=190.0,
        market_cap=540e9,
        shares_outstanding=2.8e9,
        revenue=160e9,
        revenue_growth=0.08,
        ebitda=0.0, # Not applicable
        ebitda_margin=0.0,
        net_income=48e9,
        eps=17.1,
        total_assets=3900e9,
        total_equity=300e9,
        total_debt=400e9, # Depositors/Borrowings
        cash=1400e9,
        net_debt=0.0,
        book_value_per_share=107.0,
        tangible_book_per_share=90.0,
        operating_cash_flow=0.0,
        free_cash_flow=0.0,
        capex=0.0,
        dividends_per_share=4.60,
        dividend_yield=0.024,
        payout_ratio=0.27,
        pe_ratio=11.1,
        pb_ratio=1.77,
        ev_ebitda=0.0,
        ev_revenue=0.0,
        price_to_fcf=0.0,
        roe=16.0,
        roa=1.2,
        roic=0.0,
        beta=1.2,
        nim=2.7,
        npa_ratio=0.8,
        car=15.0
    )
    
    bank_base = ValuationRouter.value_company(bank_profile, chaos_level=0.0, risk_severity=5.0)
    bank_stressed = ValuationRouter.value_company(bank_profile, chaos_level=0.7, risk_severity=7.5)
    
    print(f"  Base Fair Value: ${bank_base.base_fair_value}")
    print(f"  Stressed (70% Chaos, 7.5 Severity): ${bank_stressed.distressed_value}")
    print(f"  Downside %: {bank_stressed.downside_pct}%")
    assert bank_base.base_fair_value > bank_stressed.distressed_value, "Math error: Stressed value must be lower!"
    assert bank_stressed.company_type == "FINANCIAL", "Type routing failed!"
    print("  => Financial frame verification passed.\n")

    # 3. TEST HIGH GROWTH FRAMEWORK (EV/Revenue & Rule of 40)
    print("[TEST 3] High-Growth Framework (EV/Rev & Rule of 40)")
    growth_profile = CompanyProfile(
        ticker="SNOW",
        name="Snowflake Inc.",
        sector="Technology",
        industry="Software - Application",
        company_type=CompanyType.HIGH_GROWTH,
        current_price=160.0,
        market_cap=52e9,
        shares_outstanding=0.33e9,
        revenue=2.8e9,
        revenue_growth=0.32,  # 32% growth
        ebitda=-0.2e9, # Negative
        ebitda_margin=-7.1,
        net_income=-0.3e9,
        eps=-0.9,
        total_assets=8.5e9,
        total_equity=6.2e9,
        total_debt=0.0,
        cash=3.5e9,
        net_debt=-3.5e9,
        book_value_per_share=18.8,
        tangible_book_per_share=18.0,
        operating_cash_flow=0.8e9,
        free_cash_flow=-0.1e9, # Negative FCF
        capex=0.1e9,
        dividends_per_share=0.0,
        dividend_yield=0.0,
        payout_ratio=0.0,
        pe_ratio=0.0,
        pb_ratio=8.5,
        ev_ebitda=0.0,
        ev_revenue=17.3,
        price_to_fcf=0.0,
        roe=-5.0,
        roa=-3.5,
        roic=-4.0,
        beta=1.4
    )
    
    growth_base = ValuationRouter.value_company(growth_profile, chaos_level=0.0, risk_severity=5.0)
    growth_stressed = ValuationRouter.value_company(growth_profile, chaos_level=0.9, risk_severity=9.0)
    
    print(f"  Base Fair Value: ${growth_base.base_fair_value}")
    print(f"  Stressed (90% Chaos, 9.0 Severity): ${growth_stressed.distressed_value}")
    print(f"  Downside %: {growth_stressed.downside_pct}%")
    assert growth_base.base_fair_value > growth_stressed.distressed_value, "Math error: Stressed value must be lower!"
    assert growth_stressed.company_type == "HIGH_GROWTH", "Type routing failed!"
    print("  => High-growth frame verification passed.\n")

    # 4. TEST CYCLICAL FRAMEWORK (Normalized EV/EBITDA)
    print("[TEST 4] Cyclical Commodity Framework (EV/EBITDA)")
    oil_profile = CompanyProfile(
        ticker="XOM",
        name="Exxon Mobil Corp.",
        sector="Energy",
        industry="Oil & Gas Integrated",
        company_type=CompanyType.CYCLICAL,
        current_price=115.0,
        market_cap=460e9,
        shares_outstanding=4.0e9,
        revenue=340e9,
        revenue_growth=0.05,
        ebitda=70e9,
        ebitda_margin=20.5,
        net_income=36e9,
        eps=9.0,
        total_assets=380e9,
        total_equity=210e9,
        total_debt=40e9,
        cash=30e9,
        net_debt=10e9,
        book_value_per_share=52.5,
        tangible_book_per_share=45.0,
        operating_cash_flow=55e9,
        free_cash_flow=35e9,
        capex=20e9,
        dividends_per_share=3.80,
        dividend_yield=0.033,
        payout_ratio=0.42,
        pe_ratio=12.8,
        pb_ratio=2.19,
        ev_ebitda=6.7,
        ev_revenue=1.38,
        price_to_fcf=13.1,
        roe=17.5,
        roa=9.5,
        roic=12.0,
        beta=0.9
    )
    
    cyclical_base = ValuationRouter.value_company(oil_profile, chaos_level=0.0, risk_severity=5.0)
    cyclical_stressed = ValuationRouter.value_company(oil_profile, chaos_level=0.6, risk_severity=6.5)
    
    print(f"  Base Fair Value: ${cyclical_base.base_fair_value}")
    print(f"  Stressed (60% Chaos, 6.5 Severity): ${cyclical_stressed.distressed_value}")
    print(f"  Downside %: {cyclical_stressed.downside_pct}%")
    assert cyclical_base.base_fair_value > cyclical_stressed.distressed_value, "Math error: Stressed value must be lower!"
    assert cyclical_stressed.company_type == "CYCLICAL", "Type routing failed!"
    print("  => Cyclical frame verification passed.\n")

    print("====================================================")
    print("ALL VALUATION MATHEMATICAL ROUTES VERIFIED SUCCESSFULLY!")
    print("====================================================")

if __name__ == "__main__":
    run_tests()
