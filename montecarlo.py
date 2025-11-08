#!/usr/bin/env python3
"""
Monte Carlo Simulation module for Dutch Bay 150MW Wind Farm Financial Model V12
Generates scenario analysis by varying key parameters (debt, fx, CF, rates)
"""
from typing import Optional, Any, Dict
import numpy as np
import pandas as pd
from dutchbay_model_v12 import create_default_parameters, create_default_debt_structure, build_financial_model, ProjectParameters, DebtStructure, FinancialResults

def generate_mc_parameters(
    n_scenarios: int,
    seed: Optional[int] = None
) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {
        'usd_rate': rng.uniform(0.065, 0.09, n_scenarios),
        'lkr_rate': rng.uniform(0.075, 0.09, n_scenarios),
        'debt_ratio': rng.uniform(0.5, 0.8, n_scenarios),
        'fx_depr': rng.uniform(0.03, 0.05, n_scenarios),
        'capacity_factor': rng.uniform(0.38, 0.42, n_scenarios),
    }

def run_monte_carlo(
    iterations: int = 1000,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """Run the MC simulation, return DataFrame of scenario results."""
    params = create_default_parameters()
    debt_template = create_default_debt_structure()
    scenarios = generate_mc_parameters(iterations, seed)
    out_data = []
    for i in range(iterations):
        # Parameterize
        capfac = scenarios['capacity_factor'][i]
        fxdepr = scenarios['fx_depr'][i]
        dratio = scenarios['debt_ratio'][i]
        urate = scenarios['usd_rate'][i]
        lrate = scenarios['lkr_rate'][i]

        p = ProjectParameters(
            **{**params.__dict__, 'cf_p50': capfac, 'fx_depr': fxdepr}
        )
        td = p.total_capex * dratio
        ud = td * 0.45
        ld = td - ud
        debt = DebtStructure(
            **{**debt_template.__dict__,
               'total_debt': td,
               'usd_debt': ud,
               'lkr_debt': ld,
               'usd_mkt_rate': urate,
               'lkr_rate': lrate}
        )
        results = build_financial_model(p, debt)
        out_data.append({
            'iteration': i+1,
            'usd_rate': urate,
            'lkr_rate': lrate,
            'debt_ratio': dratio,
            'fx_depr': fxdepr,
            'capacity_factor': capfac,
            'equity_irr': results.equity_irr,
            'project_irr': results.project_irr,
            'npv_12pct': results.npv_12pct,
            'min_dscr': results.min_dscr
        })
    return pd.DataFrame(out_data)
