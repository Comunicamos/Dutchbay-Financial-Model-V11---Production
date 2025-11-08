#!/usr/bin/env python3
"""
Multi-Objective Optimizer for Dutch Bay 150MW Financial Model V12
Optimizes debt ratio, USD/LKR split, and DFI debt under IRR/DSCR constraints
ENHANCED VERSION: Robust error handling, constraint verification, dict key access
"""
import numpy as np
import warnings
from scipy.optimize import minimize, Bounds, NonlinearConstraint
from dutchbay_model_v12 import (
    create_default_parameters,
    build_financial_model,
    create_default_debt_structure,
    ProjectParameters,
    DebtStructure,
    USD_MKT_RATE, USD_DFI_RATE, LKR_DEBT_RATE,
    MAX_DEBT_RATIO, USD_DEBT_RATIO, USD_DFI_PCT, DEBT_TENOR_YEARS,
    OPEX_USD_MWH, OPEX_ESC_USD, OPEX_ESC_LKR, OPEX_SPLIT_USD, OPEX_SPLIT_LKR, SSCL_RATE, TAX_RATE, TOTAL_CAPEX, PROJECT_LIFE_YEARS
)
from typing import Dict, Any

def optimize_capital_structure(
    objective: str = 'equity_irr',
    constraints: Dict[str, float] = {'min_irr': 0.15, 'min_dscr': 1.3}
) -> Dict[str, Any]:
    """Optimize capital structure with robust error handling.
    Args:
        objective: Optimization target ('equity_irr', 'project_irr', 'npv')
        constraints: Dict with 'min_irr' and 'min_dscr' thresholds
    Returns:
        Dict with optimization results and convergence status
    """
    params = create_default_parameters()
    debt_template = create_default_debt_structure()

    def objective_func(x: np.ndarray) -> float:
        try:
            dratio, usd_pct, dfi_pct = x
            td = params.total_capex * dratio
            ud = td * usd_pct
            ld = td - ud
            debt = DebtStructure(
                **{**debt_template.__dict__,
                   'total_debt': td,
                   'usd_debt': ud,
                   'lkr_debt': ld,
                   'dfi_pct_of_usd': dfi_pct}
            )
            model = build_financial_model(params, debt)
            if objective == 'equity_irr':
                return -model['equity_irr']
            if objective == 'project_irr':
                return -model['project_irr']
            if objective == 'npv':
                return -model['npv_12pct']
            return -model['equity_irr']
        except Exception as e:
            warnings.warn(f"Objective evaluation failed: {e}")
            return 1e10

    def constraint_min_irr(x: np.ndarray) -> float:
        try:
            dratio, usd_pct, dfi_pct = x
            td = params.total_capex * dratio
            ud = td * usd_pct
            ld = td - ud
            debt = DebtStructure(
                **{**debt_template.__dict__,
                   'total_debt': td,
                   'usd_debt': ud,
                   'lkr_debt': ld,
                   'dfi_pct_of_usd': dfi_pct}
            )
            model = build_financial_model(params, debt)
            return model['equity_irr'] - constraints['min_irr']
        except Exception:
            return -1e10

    def constraint_min_dscr(x: np.ndarray) -> float:
        try:
            dratio, usd_pct, dfi_pct = x
            td = params.total_capex * dratio
            ud = td * usd_pct
            ld = td - ud
            debt = DebtStructure(
                **{**debt_template.__dict__,
                   'total_debt': td,
                   'usd_debt': ud,
                   'lkr_debt': ld,
                   'dfi_pct_of_usd': dfi_pct}
            )
            model = build_financial_model(params, debt)
            return model['min_dscr'] - constraints['min_dscr']
        except Exception:
            return -1e10

    bounds = Bounds([0.50, 0.0, 0.0], [0.80, 1.0, 0.20])
    nlc_irr = NonlinearConstraint(constraint_min_irr, 0, np.inf)
    nlc_dscr = NonlinearConstraint(constraint_min_dscr, 0, np.inf)
    x0 = np.array([0.8, 0.45, 0.10])
    try:
        res = minimize(
            objective_func, x0, method='SLSQP', bounds=bounds,
            constraints=[nlc_irr, nlc_dscr],
            options={'ftol': 1e-4, 'disp': True, 'maxiter': 150}
        )

        if not res.success:
            warnings.warn(f"Optimization did not converge: {res.message}")

        dratio, usd_pct, dfi_pct = res.x
        td = params.total_capex * dratio
        ud = td * usd_pct
        ld = td - ud
        debt = DebtStructure(
            **{**debt_template.__dict__,
               'total_debt': td,
               'usd_debt': ud,
               'lkr_debt': ld,
               'dfi_pct_of_usd': dfi_pct}
        )
        model = build_financial_model(params, debt)

        irr_violation = constraints['min_irr'] - model['equity_irr']
        dscr_violation = constraints['min_dscr'] - model['min_dscr']

        if irr_violation > 1e-4:
            warnings.warn(f"Solution violates IRR constraint by {irr_violation:.4f}")
        if dscr_violation > 1e-4:
            warnings.warn(f"Solution violates DSCR constraint by {dscr_violation:.4f}")

        return {
            'optimal_debt_ratio': dratio,
            'optimal_usd_pct': usd_pct,
            'optimal_dfi_pct': dfi_pct,
            'optimized_equity_irr': model['equity_irr'],
            'optimized_project_irr': model['project_irr'],
            'optimized_npv': model['npv_12pct'],
            'optimized_min_dscr': model['min_dscr'],
            'result': model,
            'convergence': res.success,
            'message': res.message,
            'constraint_violations': {
                'irr_violation': max(0, irr_violation),
                'dscr_violation': max(0, dscr_violation)
            }
        }

    except Exception as e:
        return {
            'optimal_debt_ratio': None,
            'optimal_usd_pct': None,
            'optimal_dfi_pct': None,
            'optimized_equity_irr': None,
            'optimized_project_irr': None,
            'optimized_npv': None,
            'optimized_min_dscr': None,
            'result': None,
            'convergence': False,
            'message': f'Optimization failed with error: {str(e)}',
            'error': str(e)
        }
