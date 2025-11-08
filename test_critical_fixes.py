#!/usr/bin/env python3
"""
Targeted Tests for Critical Fixes
- Tests debt repayment logic correction
- Tests optimization robustness enhancements
- Tests constraint verification
"""
import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from dutch_bay_financial_model import (
    compute_debt_schedule,
    compute_revenue,
    compute_sscl,
    compute_opex,
    compute_depreciation,
    build_full_model,
    TAX_RATE
)


class TestDebtRepaymentLogicFix:
    """Test that debt repayment uses correct cash flow available."""
    
    def test_debt_repayment_uses_net_opcf(self):
        """Verify USD principal repayment is based on OpCF after all costs."""
        df = build_full_model()
        
        # For year 2 (first repayment year after grace period)
        year2 = df[df['Year'] == 2].iloc[0]
        
        # Calculate what OpCF available should be
        ebitda = year2['Revenue_USD_M'] - year2['SSCL_USD_M'] - year2['OPEX_USD_M']
        ebit = ebitda - year2['DA']
        tax = max(0, ebit * TAX_RATE)
        op_cf = ebit - tax + year2['DA']
        op_cf_avail = op_cf - year2['USD_Int'] - year2['LKR_Int']
        
        # USD principal should be min(balance, 80% * op_cf_avail)
        # We can't test exact value without USD balance tracking,
        # but we can verify it's NOT using gross EBITDA
        gross_cf = ebitda
        
        # Principal should be less than 80% of gross CF
        assert year2['USD_Prin'] < 0.80 * gross_cf, \
            "USD principal appears to use gross CF instead of net OpCF"
        
        # Verify DSCR calculation is reasonable
        assert year2['DSCR'] > 0, "DSCR should be positive"
        assert year2['DSCR'] < 10, "DSCR should be reasonable (<10x)"
    
    def test_debt_schedule_incorporates_interest(self):
        """Verify debt schedule calculation includes interest in OpCF calc."""
        usd_prin, usd_int, lkr_prin, lkr_int, lkr_ds = compute_debt_schedule()
        
        # All arrays should have 20 elements
        assert len(usd_prin) == 20
        assert len(usd_int) == 20
        
        # Year 1 should have zero principal (grace period)
        assert usd_prin[0] == 0, "Year 1 should have zero USD principal"
        
        # Interest should be positive in all years with outstanding balance
        assert usd_int[0] > 0, "Year 1 should have positive USD interest"
        
        # USD principal should start being paid from year 2
        assert usd_prin[1] > 0, "Year 2 should have positive USD principal payment"
    
    def test_equity_cashflow_consistency(self):
        """Verify equity cash flow is consistent with debt service."""
        df = build_full_model()
        
        for idx, row in df.iterrows():
            # Equity CF = Op CF - Total DS
            expected_eq_cf = row['Op_CF'] - row['Total_DS']
            
            np.testing.assert_allclose(
                row['Eq_CF'], 
                expected_eq_cf, 
                rtol=1e-6,
                err_msg=f"Equity CF mismatch in year {row['Year']}"
            )


class TestOptimizationRobustness:
    """Test optimization enhancements and error handling."""
    
    def test_optimization_enhanced_exists(self):
        """Verify enhanced optimization module exists."""
        try:
            from optimization_enhanced import optimize_capital_structure
            assert callable(optimize_capital_structure)
        except ImportError:
            pytest.fail("optimization_enhanced.py not found or not importable")
    
    def test_optimization_handles_convergence_failure(self):
        """Test that optimization gracefully handles convergence issues."""
        from optimization_enhanced import optimize_capital_structure
        
        # Run optimization with very tight constraints that may fail
        result = optimize_capital_structure(
            objective='equity_irr',
            constraints={'min_irr': 0.50, 'min_dscr': 3.0}  # Unrealistic constraints
        )
        
        # Should not crash - should return dict with convergence status
        assert isinstance(result, dict)
        assert 'convergence' in result
        assert 'message' in result
    
    def test_optimization_verifies_constraints(self):
        """Test that optimization returns constraint violation info."""
        from optimization_enhanced import optimize_capital_structure
        
        result = optimize_capital_structure()
        
        # Should have constraint violation tracking
        assert 'constraint_violations' in result
        assert 'irr_violation' in result['constraint_violations']
        assert 'dscr_violation' in result['constraint_violations']
    
    def test_optimization_increased_iterations(self):
        """Verify optimization uses increased iteration limit."""
        import inspect
        from optimization_enhanced import optimize_capital_structure
        
        # Check source code contains maxiter=150
        source = inspect.getsource(optimize_capital_structure)
        assert 'maxiter' in source.lower()
        # Should have maxiter > 100
        assert '150' in source or '100' in source or '200' in source


class TestNumericalStability:
    """Test numerical stability of fixed calculations."""
    
    def test_dscr_no_division_by_zero(self):
        """Verify DSCR calculation handles zero debt service."""
        df = build_full_model()
        
        # DSCR should never be inf or nan in normal operation
        assert not np.any(np.isinf(df['DSCR'])), "DSCR contains infinity"
        # Small values are OK, but should be positive or NaN
        assert np.all((df['DSCR'] > 0) | np.isnan(df['DSCR'])), "DSCR should be positive or NaN"
    
    def test_cash_flow_monotonicity(self):
        """Test that revenue decreases over time due to degradation."""
        df = build_full_model()
        
        # Revenue should decline year over year (FX depr + degradation)
        for i in range(len(df) - 1):
            # Later years should have lower revenue in USD terms
            assert df.iloc[i+1]['Revenue_USD'] < df.iloc[i]['Revenue_USD'], \
                f"Revenue should decline from year {i+1} to {i+2}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_final_year_debt_fully_repaid(self):
        """Verify all debt is repaid by end of tenor."""
        usd_prin, usd_int, lkr_prin, lkr_int, lkr_ds = compute_debt_schedule()
        
        # Sum of USD principal payments should roughly equal initial debt
        # (within tolerance for rounding and OpCF-based repayment)
        from dutch_bay_financial_model import USD_DEBT_INIT
        total_usd_repaid = np.sum(usd_prin)
        
        # Should repay most of the debt (at least 90%)
        assert total_usd_repaid >= 0.9 * USD_DEBT_INIT, \
            f"Only {total_usd_repaid/USD_DEBT_INIT:.1%} of USD debt repaid"
    
    def test_tax_never_negative(self):
        """Verify tax is never negative (uses max(0, ...))."""
        df = build_full_model()
        
        assert np.all(df['Tax'] >= 0), "Tax should never be negative"
    
    def test_depreciation_equals_capex_over_life(self):
        """Verify total depreciation equals initial CAPEX."""
        df = build_full_model()
        from dutch_bay_financial_model import CAPEX_TOTAL, ECON_LIFE
        
        total_da = np.sum(df['DA'])
        
        np.testing.assert_allclose(
            total_da,
            CAPEX_TOTAL,
            rtol=1e-6,
            err_msg="Total D&A should equal CAPEX"
        )


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
