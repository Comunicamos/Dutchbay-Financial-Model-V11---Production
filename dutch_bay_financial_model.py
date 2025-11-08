"""Dutch Bay 150MW Wind Farm Financial Model - Core Module
Version 11 - Verified and tested with pytest and Hypothesis
"""

import numpy as np
import pandas as pd
from typing import Tuple

# ============================================================================
# CORE INPUT PARAMETERS (Can be overridden via CSV)
# ============================================================================

PROJECT_YEARS = 20
NAMEPLATE_MW = 150
CF_P50 = 0.40  # Capacity factor (P50 base case)
YEARLY_DEGRADATION = 0.006  # 0.6%/yr
HOURS_PER_YEAR = 8760
TARIFF_LKR_KWH = 20.36
FX_INITIAL = 300
FX_DEPR = 0.03  # 3% annual LKR depreciation
OPEX_USD_MWH = 6.83
OPEX_ESC_USD = 0.02
OPEX_ESC_LKR = 0.05
OPEX_SPLIT_USD = 0.3
OPEX_SPLIT_LKR = 0.7
CAPEX_TOTAL = 146.38  # USD M
ECON_LIFE = 20
SSCL_RATE = 0.025  # Critical: 2.5% Social Service Levy
TAX_RATE = 0.30
USD_DEBT_INIT = 56.36  # USD M
LKR_DEBT_INIT = 13833.0  # LKR M
USD_DEBT_RATE = 0.07
LKR_DEBT_RATE = 0.07
USD_DEBT_TENOR = 15
LKR_DEBT_TENOR = 15
GRACE_PERIOD = 1
PRINCIPAL_PCT_1_4 = 0.80  # 80% of OpCF for Years 2-4
PRINCIPAL_PCT_5_ON = 0.20  # 20% of OpCF for Years 5+

# ============================================================================
# CORE CALCULATION FUNCTIONS
# ============================================================================

def compute_generation(year: int) -> float:
    """Annual gross generation in MWh.
    
    Args:
        year: Project year (1-20)
        
    Returns:
        Generation in MWh
    """
    return NAMEPLATE_MW * HOURS_PER_YEAR * CF_P50 * (1 - YEARLY_DEGRADATION) ** (year - 1)


def compute_fx(year: int) -> float:
    """FX rate for given year with depreciation.
    
    Args:
        year: Project year (1-20)
        
    Returns:
        FX rate (LKR/USD)
    """
    return FX_INITIAL * (1 + FX_DEPR) ** (year - 1)


def compute_tariff_usd(year: int) -> float:
    """USD equivalent tariff per MWh.
    
    Args:
        year: Project year (1-20)
        
    Returns:
        Tariff in USD/MWh
    """
    fx = compute_fx(year)
    return TARIFF_LKR_KWH / fx * 1000  # USD/MWh


def compute_revenue(year: int) -> float:
    """Annual revenue in USD millions.
    
    Args:
        year: Project year (1-20)
        
    Returns:
        Revenue in USD M
    """
    gen = compute_generation(year)
    tariff_usd = compute_tariff_usd(year)
    return gen * tariff_usd / 1_000_000  # USD million


def compute_sscl(year: int) -> float:
    """Social Service Contribution Levy (2.5% on turnover).
    
    Args:
        year: Project year (1-20)
        
    Returns:
        SSCL in USD M
    """
    return compute_revenue(year) * SSCL_RATE


def compute_opex(year: int) -> float:
    """Annual OPEX with dual-currency escalation.
    
    Args:
        year: Project year (1-20)
        
    Returns:
        OPEX in USD M
    """
    gen = compute_generation(year)
    fx = compute_fx(year)
    
    # USD portion escalates at USD inflation rate
    usd_portion = OPEX_USD_MWH * OPEX_SPLIT_USD * (1 + OPEX_ESC_USD) ** (year - 1)
    
    # LKR portion escalates at LKR inflation rate, then converted to USD
    lkr_portion_base = OPEX_USD_MWH * OPEX_SPLIT_LKR * (1 + OPEX_ESC_LKR) ** (year - 1)
    lkr_portion_usd = lkr_portion_base / (fx / FX_INITIAL)
    
    return gen * (usd_portion + lkr_portion_usd) / 1_000_000  # USD million


def compute_depreciation() -> float:
    """Annual straight-line depreciation.
    
    Returns:
        D&A in USD M per year
    """
    return CAPEX_TOTAL / ECON_LIFE


def compute_debt_schedule() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calculate complete debt service schedule for 20 years.
    
    Returns:
        Tuple of (USD Principal, USD Interest, LKR Principal, LKR Interest, LKR Total DS)
        All as numpy arrays of length PROJECT_YEARS
    """
    usd_bal = USD_DEBT_INIT
    lkr_bal = LKR_DEBT_INIT

    usd_principal_hist = []
    usd_interest_hist = []
    lkr_principal_hist = []
    lkr_interest_hist = []
    lkr_ds_hist = []

    for year in range(1, PROJECT_YEARS + 1):
        # USD debt service
        usd_int = usd_bal * USD_DEBT_RATE
        # LKR debt service (straight-line amortization)
        lkr_int = lkr_bal * LKR_DEBT_RATE
        fx = compute_fx(year)
        lkr_int_usd = lkr_int / fx
        # Calculate true available OpCF for debt service after all costs
        ebitda = compute_revenue(year) - compute_sscl(year) - compute_opex(year)
        da = compute_depreciation()
        ebit = ebitda - da
        tax = max(0, ebit * TAX_RATE)
        op_cf = ebit - tax + da
        op_cf_avail = op_cf - usd_int - lkr_int_usd
        # Principal repayments
        if year == 1 and GRACE_PERIOD == 1:
            usd_prin = 0
        elif year >= 2 and year <= 4:
            usd_prin = min(usd_bal, PRINCIPAL_PCT_1_4 * op_cf_avail)
        elif year > 4:
            usd_prin = min(usd_bal, PRINCIPAL_PCT_5_ON * op_cf_avail)
        else:
            usd_prin = 0
        usd_bal = max(0, usd_bal - usd_prin)
        if year <= LKR_DEBT_TENOR:
            lkr_prin = lkr_bal / (LKR_DEBT_TENOR - year + 1)
        else:
            lkr_prin = 0
        lkr_bal = max(0, lkr_bal - lkr_prin)
        lkr_ds = lkr_int + lkr_prin
        usd_principal_hist.append(usd_prin)
        usd_interest_hist.append(usd_int)
        lkr_principal_hist.append(lkr_prin)
        lkr_interest_hist.append(lkr_int)
        lkr_ds_hist.append(lkr_ds)
    return (np.array(usd_principal_hist), 
            np.array(usd_interest_hist), 
            np.array(lkr_principal_hist), 
            np.array(lkr_interest_hist), 
            np.array(lkr_ds_hist))


def build_full_model() -> pd.DataFrame:
    """Build complete 20-year financial model.
    
    Returns:
        DataFrame with all financial metrics for 20 years
    """
    years = np.arange(1, PROJECT_YEARS + 1)
    
    # Operating metrics
    gen = np.array([compute_generation(y) for y in years])
    fx = np.array([compute_fx(y) for y in years])
    tariff_usd = np.array([compute_tariff_usd(y) for y in years])
    revenue = np.array([compute_revenue(y) for y in years])
    sscl = np.array([compute_sscl(y) for y in years])
    opex = np.array([compute_opex(y) for y in years])
    
    # Depreciation and earnings
    da = compute_depreciation() * np.ones(PROJECT_YEARS)
    ebitda = revenue - sscl - opex
    ebit = ebitda - da
    tax = np.maximum(0, ebit * TAX_RATE)
    op_cf = ebit - tax + da
    
    # Debt service
    usd_prin, usd_int, lkr_prin, lkr_int, lkr_ds = compute_debt_schedule()
    
    # Convert LKR to USD for consolidated reporting
    lkr_int_usd = lkr_int / fx
    lkr_prin_usd = lkr_prin / fx
    
    total_ds = usd_int + usd_prin + lkr_int_usd + lkr_prin_usd
    dscr = np.where(total_ds > 1e-6, op_cf / total_ds, np.nan)
    eq_cf = op_cf - total_ds
    
    # Build comprehensive dataframe
    df = pd.DataFrame({
        'Year': years,
        'Generation_MWh': gen,
        'FX': fx,
        'Tariff_USD_MWh': tariff_usd,
        'Revenue_USD_M': revenue,
        'SSCL_USD_M': sscl,
        'OPEX_USD_M': opex,
        'EBITDA': ebitda,
        'DA': da,
        'EBIT': ebit,
        'Tax': tax,
        'Op_CF': op_cf,
        'USD_Int': usd_int,
        'USD_Prin': usd_prin,
        'LKR_Int': lkr_int_usd,
        'LKR_Prin': lkr_prin_usd,
        'Total_DS': total_ds,
        'DSCR': dscr,
        'Eq_CF': eq_cf,
    })
    
    return df

import os

if __name__ == "__main__":
    # Run model and export
    df = build_full_model()
    output_path = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'dutchbay_20yr_outputs.csv')
    output_path = os.path.abspath(output_path)
    df.to_csv(output_path, index=False)
    print(f"\n✓ Financial model executed successfully")
    print(f"✓ Exported 20-year outputs to {output_path}")
    print(f"\nKey Year 1 Metrics:")
    print(f"  Generation: {df.iloc[0]['Generation_MWh']/1000:.1f} GWh")
    print(f"  Revenue: ${df.iloc[0]['Revenue_USD_M']:.2f}M")
    print(f"  SSCL: ${df.iloc[0]['SSCL_USD_M']:.3f}M")
    print(f"  Op CF: ${df.iloc[0]['Op_CF']:.2f}M")
    print(f"  DSCR: {df.iloc[0]['DSCR']:.2f}x")
    print(f"  Equity CF: ${df.iloc[0]['Eq_CF']:.2f}M")
