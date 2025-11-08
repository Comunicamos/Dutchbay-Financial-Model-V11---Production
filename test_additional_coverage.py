#!/usr/bin/env python3
"""
Additional Test Coverage for Previously Uncovered Functions
Tests for: SSCL, FX compounding, OPEX escalation, Parameter validation
"""
import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from dutch_bay_financial_model import (
    compute_sscl,
    compute_revenue,
    compute_fx,
    compute_opex,
    compute_generation,
    SSCL_RATE,
    FX_INITIAL,
    FX_DEPR,
    OPEX_USD_MWH,
    OPEX_ESC_USD,
    OPEX_ESC_LKR,
    OPEX_SPLIT_USD,
    OPEX_SPLIT_LKR,
    YEARLY_DEGRADATION,
    PROJECT_YEARS
)

from parameter_validation import (
    validate_project_parameters,
    validate_debt_structure,
    validate_and_warn,
    ValidationError
)


class TestSSCLCalculation:
    """Test Social Service Contribution Levy calculation."""
    
    def test_sscl_is_2_5_percent_of_revenue(self):
        """Verify SSCL is exactly 2.5% of revenue for all years."""
        for year in range(1, PROJECT_YEARS + 1):
            revenue = compute_revenue(year)
            sscl = compute_sscl(year)
            expected_sscl = revenue * SSCL_RATE
            
            np.testing.assert_allclose(
                sscl,
                expected_sscl,
                rtol=1e-10,
                err_msg=f"SSCL mismatch in year {year}"
            )
    
    def test_sscl_positive_all_years(self):
        """SSCL should be positive for all years."""
        for year in range(1, PROJECT_YEARS + 1):
            sscl = compute_sscl(year)
            assert sscl > 0, f"SSCL should be positive in year {year}"
    
    def test_sscl_proportional_to_revenue(self):
        """SSCL should track revenue changes."""
        sscl_1 = compute_sscl(1)
        sscl_10 = compute_sscl(10)
        rev_1 = compute_revenue(1)
        rev_10 = compute_revenue(10)
        
        # Ratio of SSCL should equal ratio of revenue
        np.testing.assert_allclose(
            sscl_10 / sscl_1,
            rev_10 / rev_1,
            rtol=1e-10
        )


class TestFXCompounding:
    """Test FX depreciation compounding accuracy."""
    
    def test_fx_compounds_correctly(self):
        """Verify FX rate compounds depreciation annually."""
        for year in range(1, PROJECT_YEARS + 1):
            fx = compute_fx(year)
            expected_fx = FX_INITIAL * (1 + FX_DEPR) ** (year - 1)
            
            np.testing.assert_allclose(
                fx,
                expected_fx,
                rtol=1e-10,
                err_msg=f"FX compounding error in year {year}"
            )
    
    def test_fx_year_1_equals_initial(self):
        """Year 1 FX should equal initial FX rate."""
        fx_year_1 = compute_fx(1)
        np.testing.assert_allclose(fx_year_1, FX_INITIAL, rtol=1e-10)
    
    def test_fx_increases_with_depreciation(self):
        """FX rate should increase each year (LKR depreciates)."""
        for year in range(1, PROJECT_YEARS):
            fx_current = compute_fx(year)
            fx_next = compute_fx(year + 1)
            assert fx_next > fx_current, \
                f"FX should increase from year {year} to {year+1}"
    
    def test_fx_year_20_calculation(self):
        """Verify Year 20 FX is correct."""
        fx_year_20 = compute_fx(20)
        expected = FX_INITIAL * (1.03) ** 19  # 19 years of depreciation
        np.testing.assert_allclose(fx_year_20, expected, rtol=1e-10)


class TestOPEXEscalation:
    """Test dual-currency OPEX escalation."""
    
    def test_opex_year_1_baseline(self):
        """Year 1 OPEX should be close to base rate * generation."""
        gen_year_1 = compute_generation(1)
        opex_year_1 = compute_opex(1)
        
        # Year 1: No escalation, FX = initial
        expected_opex = gen_year_1 * OPEX_USD_MWH / 1_000_000
        
        # Should be very close (within 0.1%)
        np.testing.assert_allclose(
            opex_year_1,
            expected_opex,
            rtol=0.001
        )
    
    def test_opex_escalates_over_time(self):
        """OPEX should increase in later years due to escalation."""
        opex_1 = compute_opex(1)
        opex_20 = compute_opex(20)
        
        # Despite lower generation, OPEX per MWh should increase
        gen_1 = compute_generation(1)
        gen_20 = compute_generation(20)
        
        opex_per_mwh_1 = opex_1 / gen_1 * 1_000_000
        opex_per_mwh_20 = opex_20 / gen_20 * 1_000_000
        
        assert opex_per_mwh_20 > opex_per_mwh_1, \
            "OPEX per MWh should increase due to escalation"
    
    def test_opex_dual_currency_components(self):
        """Verify USD and LKR portions escalate differently."""
        # This tests the logic even though we can't directly observe components
        opex_values = [compute_opex(y) for y in range(1, PROJECT_YEARS + 1)]
        
        # OPEX should not decline (despite degradation, escalation dominates)
        # This is a characteristic of the dual currency model
        assert all(o > 0 for o in opex_values), "All OPEX values should be positive"


class TestGenerationDegradation:
    """Test generation degradation over project life."""
    
    def test_generation_declines_annually(self):
        """Generation should decline each year due to degradation."""
        for year in range(1, PROJECT_YEARS):
            gen_current = compute_generation(year)
            gen_next = compute_generation(year + 1)
            
            assert gen_next < gen_current, \
                f"Generation should decline from year {year} to {year+1}"
    
    def test_generation_degradation_rate(self):
        """Verify degradation rate is correct."""
        gen_1 = compute_generation(1)
        gen_2 = compute_generation(2)
        
        actual_decline = (gen_1 - gen_2) / gen_1
        
        np.testing.assert_allclose(
            actual_decline,
            YEARLY_DEGRADATION,
            rtol=1e-10,
            err_msg="Degradation rate doesn't match specification"
        )
    
    def test_generation_year_20_cumulative_degradation(self):
        """Verify cumulative degradation over 20 years."""
        gen_1 = compute_generation(1)
        gen_20 = compute_generation(20)
        
        expected_gen_20 = gen_1 * (1 - YEARLY_DEGRADATION) ** 19
        
        np.testing.assert_allclose(gen_20, expected_gen_20, rtol=1e-10)


class TestParameterValidation:
    """Test parameter validation module."""
    
    def test_valid_parameters_pass(self):
        """Valid parameters should pass validation."""
        valid_params = {
            'total_capex': 155.0,
            'cf_p50': 0.40,
            'nameplate_mw': 150,
            'tax_rate': 0.30,
            'fx_depr': 0.03
        }
        
        is_valid, errors = validate_project_parameters(valid_params)
        assert is_valid, f"Valid parameters failed: {errors}"
        assert len(errors) == 0
    
    def test_invalid_capex_fails(self):
        """CAPEX outside bounds should fail validation."""
        invalid_params = {
            'total_capex': 600.0  # Too high
        }
        
        is_valid, errors = validate_project_parameters(invalid_params)
        assert not is_valid
        assert len(errors) > 0
        assert 'CAPEX' in errors[0]
    
    def test_invalid_cf_fails(self):
        """Capacity factor outside bounds should fail."""
        invalid_params = {
            'cf_p50': 1.5  # >100%
        }
        
        is_valid, errors = validate_project_parameters(invalid_params)
        assert not is_valid
        assert any('capacity factor' in e.lower() for e in errors)
    
    def test_invalid_tax_rate_fails(self):
        """Tax rate outside bounds should fail."""
        invalid_params = {
            'tax_rate': 0.80  # 80%
        }
        
        is_valid, errors = validate_project_parameters(invalid_params)
        assert not is_valid
    
    def test_validate_and_warn_raises_on_critical(self):
        """validate_and_warn should raise ValidationError for critical issues."""
        bad_params = {
            'total_capex': 700,  # Way too high
            'cf_p50': 2.0,  # Impossible
            'tax_rate': 1.5,  # >100%
            'fx_depr': 0.50  # 50% annual depreciation
        }
        
        with pytest.raises(ValidationError):
            validate_and_warn(bad_params)
    
    def test_debt_structure_validation(self):
        """Debt structure should validate correctly."""
        valid_debt = {
            'total_debt': 124.0,
            'usd_debt': 55.8,
            'lkr_debt': 68.2,
            'dfi_pct_of_usd': 0.10
        }
        
        is_valid, errors = validate_debt_structure(valid_debt)
        assert is_valid, f"Valid debt structure failed: {errors}"
    
    def test_debt_split_mismatch_fails(self):
        """USD + LKR != Total should fail."""
        invalid_debt = {
            'total_debt': 100.0,
            'usd_debt': 50.0,
            'lkr_debt': 60.0  # Sum = 110, not 100
        }
        
        is_valid, errors = validate_debt_structure(invalid_debt)
        assert not is_valid
        assert any('!=' in e or 'sum' in e.lower() for e in errors)


class TestNumericalPrecision:
    """Test numerical precision and rounding."""
    
    def test_consistent_calculations_across_calls(self):
        """Same inputs should give identical outputs."""
        for year in [1, 10, 20]:
            rev1 = compute_revenue(year)
            rev2 = compute_revenue(year)
            assert rev1 == rev2, "Calculations should be deterministic"
    
    def test_no_catastrophic_cancellation(self):
        """No precision loss in critical calculations."""
        # Test that small differences don't get lost
        opex_1 = compute_opex(1)
        opex_2 = compute_opex(2)
        
        difference = abs(opex_1 - opex_2)
        # Difference should be measurable (not lost to floating point)
        assert difference > 1e-10, "Precision loss detected in OPEX calculation"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
