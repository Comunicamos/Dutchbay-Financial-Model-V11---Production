#!/usr/bin/env python3
"""
Dutch Bay 150MW Wind Farm - Financial Model V11
Enhanced IRR/NPV Framework with Multiple Solver Methods

CAPEX: $155M (Wind only, no BESS)
Debt Structure: 80% total (45% USD, 55% LKR)
  - USD: 10% DFI @ 6.5%, 90% Market @ 7.0%
  - LKR: @ 7.5%
Equity: 20%

Date: November 7, 2025
"""

import numpy as np
import pandas as pd
from scipy.optimize import brentq, newton, bisect
from datetime import datetime, timedelta

# ============================================================================
# ENHANCED IRR/NPV CALCULATION FUNCTIONS
# ============================================================================

def calculate_npv(rate, cash_flows):
    return np.sum([cf / (1 + rate) ** i for i, cf in enumerate(cash_flows)])

def calculate_irr_robust(cash_flows, method='brentq', initial_guess=0.10, tolerance=1e-8, max_iterations=1000):
    if len(cash_flows) < 2:
        return {'irr': None, 'status': 'ERROR', 'message': 'Need at least 2 cash flows', 'method': None}
    if np.all(np.array(cash_flows) >= 0):
        return {'irr': None, 'status': 'ERROR', 'message': 'No negative cash flows - IRR undefined', 'method': None}
    if np.all(np.array(cash_flows) <= 0):
        return {'irr': None, 'status': 'ERROR', 'message': 'No positive cash flows - IRR undefined', 'method': None}
    sign_changes = sum(1 for i in range(len(cash_flows)-1) if (cash_flows[i] * cash_flows[i+1] < 0))
    warning = f'{sign_changes} sign changes detected - multiple IRRs may exist' if sign_changes > 1 else None
    if method in ['brentq', 'both']:
        try:
            irr_result = brentq(lambda r: calculate_npv(r, cash_flows),-0.99, 5.00, xtol=tolerance,maxiter=max_iterations)
            npv_check = calculate_npv(irr_result, cash_flows)
            if abs(npv_check) < tolerance * 10:
                return {'irr': irr_result,'status': 'CONVERGED','method': 'Brentq (Bracketing)','npv_check': npv_check,'warning': warning}
        except ValueError as e:
            if method == 'brentq':
                return {'irr': None,'status': 'ERROR','message': f'Brentq failed: {str(e)}','method': 'Brentq (Bracketing)','warning': warning}
    if method in ['newton', 'both']:
        try:
            def npv_derivative(rate, cash_flows):
                return -np.sum([i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows)])
            irr_result = newton(lambda r: calculate_npv(r, cash_flows),initial_guess,fprime=lambda r: npv_derivative(r, cash_flows),tol=tolerance,maxiter=max_iterations)
            npv_check = calculate_npv(irr_result, cash_flows)
            if abs(npv_check) < tolerance * 10 and -0.99 < irr_result < 5.0:
                return {'irr': irr_result,'status': 'CONVERGED','method': 'Newton-Raphson (with derivative)','npv_check': npv_check,'warning': warning}
        except:
            pass
    return {'irr': None, 'status': 'FAILED', 'message': 'All solver methods failed to converge', 'method': None,'warning': warning}

def calculate_xirr_robust(cash_flows, dates, tolerance=1e-8):
    if len(cash_flows) != len(dates):
        return {'xirr': None, 'status': 'ERROR', 'message': 'Cash flows and dates must have same length'}
    first_date = dates[0]
    years = np.array([(d - first_date).days / 365.25 for d in dates])
    def xnpv(rate, cash_flows, years):
        return np.sum([cf / (1 + rate) ** y for cf, y in zip(cash_flows, years)])
    try:
        xirr = brentq(lambda r: xnpv(r, cash_flows, years),-0.99,5.00,xtol=tolerance)
        return {'xirr': xirr, 'status': 'CONVERGED', 'method': 'Brentq with irregular periods', 'npv_check': xnpv(xirr, cash_flows, years)}
    except:
        return {'xirr': None, 'status': 'FAILED', 'message': 'XIRR calculation failed to converge'}
# ... Continue with model calculations and main as in prior output ...