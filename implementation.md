# Dutch Bay Financial Model V12 - Implementation Action Plan

**Date:** November 7, 2025  
**Status:** Ready for Manual Implementation  
**Deployment Timeline:** 30-60 minutes  

---

## COMPLETE NEXT STEPS WITH ARTIFACT REFERENCES

### **Step 1: Follow [285] - The Corrected Deployment Checklist**

**Document:** Corrected-Deployment-Checklist.md (Artifact [285])

**Action:** Open and reference this document for:
- Phase 0: Prerequisite file creation (sensitivity.py, optimization.py)
- Phase 1: File creation and integration
- Phase 2: Dependencies installation
- Phase 3-5: Validation testing

**Location to find it:** Search for artifact [285] in conversation history or retrieve from documents folder.

**Key sections to follow in order:**
1. Phase 0: Complete first (create sensitivity.py and optimization.py)
2. Phase 1: Update CLI and create test files
3. Phase 2: Install dependencies
4. Phase 3-5: Run validation tests

---

### **Step 2: Complete Phase 0 - Create sensitivity.py and optimization.py**

**Source:** Corrected-Deployment-Checklist.md [285] - PHASE 0 section

#### **2.1 Create sensitivity.py**

**Location:** `/Users/aruna/Desktop/DutchBay_Financials_V11/scripts/sensitivity.py`

**Complete code to copy from [285]:**
```python
#!/usr/bin/env python3
"""
Sensitivity analysis module for Dutch Bay 150MW
One-at-a-time stress test (tornado chart compatible)
"""
from typing import Optional, Dict, Any
import pandas as pd
from dutchbay_model_v12 import build_financial_model, create_default_parameters, create_default_debt_structure, ProjectParameters, DebtStructure

SENSITIVITY_CONFIG = [
    {'param': 'cf_p50', 'label': 'Capacity Factor', 'base': 0.40, 'stress': [0.38, 0.42]},
    {'param': 'opex_usd_mwh', 'label': 'OPEX', 'base': 6.83, 'stress': [6.15, 7.51]},
    {'param': 'usd_mkt_rate', 'label': 'USD Rate', 'base': 0.07, 'stress': [0.09]},
    {'param': 'lkr_rate', 'label': 'LKR Rate', 'base': 0.075, 'stress': [0.095]},
    {'param': 'total_capex', 'label': 'CAPEX', 'base': 155, 'stress': [142.6, 167.4]},
    {'param': 'fx_depr', 'label': 'FX Depr', 'base': 0.03, 'stress': [0.05]}
]

def run_sensitivity_analysis(output_dir: str = './outputs') -> pd.DataFrame:
    params = create_default_parameters()
    debt = create_default_debt_structure()
    results = []
    base_model = build_financial_model(params, debt)
    for s in SENSITIVITY_CONFIG:
        base = s['base']
        param = s['param']
        for val in s['stress']:
            sp = ProjectParameters(**{**params.__dict__})
            sd = DebtStructure(**{**debt.__dict__})
            if param in ['usd_mkt_rate', 'lkr_rate']:
                setattr(sd, param, val)
            else:
                setattr(sp, param, val)
            mr = build_financial_model(sp, sd)
            results.append({
                'parameter': s['label'],
                'base_value': base,
                'stressed_value': val,
                'base_equity_irr': base_model.equity_irr,
                'stressed_equity_irr': mr.equity_irr,
                'delta_irr': mr.equity_irr - base_model.equity_irr,
                'base_npv': base_model.npv_12pct,
                'stressed_npv': mr.npv_12pct,
                'delta_npv': mr.npv_12pct - base_model.npv_12pct
            })
    df = pd.DataFrame(results)
    df.to_csv(f\"{output_dir}/dutchbay_sensitivity.csv\", index=False)
    return df
```

**Verify:**
```bash
python -c \"import sys; sys.path.append('./scripts'); from sensitivity import run_sensitivity_analysis; print('✓ sensitivity.py loaded')\"
```

---

#### **2.2 Create optimization.py**

**Location:** `/Users/aruna/Desktop/DutchBay_Financials_V11/scripts/optimization.py`

**Complete code to copy from [285]:**
```python
#!/usr/bin/env python3
"""
Multi-Objective Optimizer for Dutch Bay 150MW Financial Model V12
Optimizes debt ratio, USD/LKR split, and DFI debt under IRR/DSCR constraints
"""
import numpy as np
from scipy.optimize import minimize, Bounds, NonlinearConstraint
from dutchbay_model_v12 import create_default_parameters, build_financial_model, create_default_debt_structure, ProjectParameters, DebtStructure
from typing import Dict, Any

def optimize_capital_structure(
    objective: str = 'equity_irr',
    constraints: Dict[str,float] = {'min_irr':0.15, 'min_dscr':1.3}
) -> Dict[str,Any]:
    params = create_default_parameters()
    debt_template = create_default_debt_structure()

    def objective_func(x: np.ndarray) -> float:
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
        if objective=='equity_irr':
            return -model.equity_irr
        if objective=='project_irr':
            return -model.project_irr
        if objective=='npv':
            return -model.npv_12pct
        return -model.equity_irr

    def constraint_min_irr(x: np.ndarray) -> float:
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
        return model.equity_irr - constraints['min_irr']

    def constraint_min_dscr(x: np.ndarray) -> float:
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
        return model.min_dscr - constraints['min_dscr']

    bounds = Bounds([0.50, 0.0, 0.0], [0.80, 1.0, 0.20])
    nlc_irr = NonlinearConstraint(constraint_min_irr, 0, np.inf)
    nlc_dscr = NonlinearConstraint(constraint_min_dscr, 0, np.inf)
    x0 = np.array([0.8, 0.45, 0.10])

    res = minimize(
        objective_func, x0, method='SLSQP', bounds=bounds,
        constraints=[nlc_irr, nlc_dscr], options={'ftol':1e-5,'disp':True,'maxiter':40}
    )
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
    return {'optimal_debt_ratio': dratio,
            'optimal_usd_pct': usd_pct,
            'optimal_dfi_pct': dfi_pct,
            'optimized_equity_irr': model.equity_irr,
            'optimized_project_irr': model.project_irr,
            'optimized_npv': model.npv_12pct,
            'optimized_min_dscr': model.min_dscr,
            'result': model,
            'convergence': res.success,
            'message': res.message}
```

**Verify:**
```bash
python -c \"import sys; sys.path.append('./scripts'); from optimization import optimize_capital_structure; print('✓ optimization.py loaded')\"
```

---

### **Step 3: Complete Phase 1 - Update CLI and Create Test Files**

**Source:** Enhanced-CLI-Docstrings.md [281] + Testing-Samples-Validation.md [282]

#### **3.1 Update dutchbay_cli.py**

**Reference:** [281] - Enhanced-CLI-Docstrings.md

**Instructions:**
1. Open artifact [281]
2. Find the Python code block (starts with `#!/usr/bin/env python3`)
3. Copy the ENTIRE code block (approximately 400 lines)
4. Replace the existing `/Users/aruna/Desktop/DutchBay_Financials_V11/dutchbay_cli.py`

**Alternative if copy-paste is difficult:**
- Use the method in [285]: "Method 1 (Recommended - Manual extraction)" under Phase 1

**Verify:**
```bash
python dutchbay_cli.py --help
# Should show: usage: dutchbay_cli.py [-h] --mode {baseline,monte-carlo,sensitivity,optimize,validate,export}
```

---

#### **3.2-3.5 Create Test Files**

**Reference:** Testing-Samples-Validation.md [282]

**Create these 4 files:**

**File 1:** `/tests/test_monte_carlo.py`
- Source: [282] Part 2 "File: /tests/test_monte_carlo.py"
- Copy entire Python code block

**File 2:** `/tests/test_sensitivity.py`
- Source: [282] Part 2 "File: /tests/test_sensitivity.py"
- Copy entire Python code block

**File 3:** `/tests/test_optimization.py`
- Source: [282] Part 2 "File: /tests/test_optimization.py"
- Copy entire Python code block

**File 4:** `/tests/run_full_validation.py`
- Source: [282] Part 3 "PART 3: VALIDATION SCRIPT"
- Copy entire Python code block

---

#### **3.6 Append Tests to Existing File**

**Reference:** Testing-Samples-Validation.md [282] - Part 1

**Action:** 
1. Open existing `/tests/test_dutchbay_model.py`
2. Go to END of file
3. Append these test classes from [282] Part 1:
   - `TestBaselineScenario`
   - `TestMonteCarloModule`
   - `TestSensitivityModule`
   - `TestOptimizationModule`

**Do NOT overwrite** - only append

**Verify:**
```bash
pytest tests/test_dutchbay_model.py -v
# Should show 15+ tests passing
```

---

### **Step 4: Run Validation - Phase 3-5 Testing**

**Reference:** Corrected-Deployment-Checklist [285] - Phases 2-5

#### **4.1 Install Dependencies (Phase 2)**
```bash
cd /Users/aruna/Desktop/DutchBay_Financials_V11/
pip install -r requirements.txt
```

#### **4.2 Test Each CLI Mode (Phase 3)**
```bash
# Baseline (should complete in 30 seconds)
python dutchbay_cli.py --mode=baseline
# Expected: ✓ Output saved to ./outputs/dutchbay_baseline_v12.csv

# Monte Carlo (100 scenarios, should complete in 1-2 minutes)
python dutchbay_cli.py --mode=monte-carlo --iterations=100
# Expected: MC scenarios saved to ./outputs/dutchbay_monte_carlo.csv

# Sensitivity (should complete in 30 seconds)
python dutchbay_cli.py --mode=sensitivity
# Expected: Sensitivity results saved to ./outputs/dutchbay_sensitivity.csv

# Optimization (should complete in 1-2 minutes)
python dutchbay_cli.py --mode=optimize
# Expected: Optimized scenario saved to ./outputs/dutchbay_optimized.csv

# Run all tests
pytest tests/ -v
# Expected: All 35+ tests pass
```

#### **4.3 Run Full Validation Suite (Phase 4-5)**
```bash
# Type checking
mypy scripts/dutchbay_model_v12.py --strict
# Expected: Success: no issues found

# Code quality
pylint scripts/dutchbay_model_v12.py
# Expected: Rating > 9.0/10

# Code style
flake8 scripts/
# Expected: No output (no issues)

# Test coverage
pytest tests/ --cov=scripts --cov-report=html
# Expected: Coverage > 60-75%

# Full validation script
python tests/run_full_validation.py
# Expected: All 4 checks pass
```

---

### **Step 5: Reference [284] - If You Encounter Issues**

**Document:** Deployment-Audit-Report.md (Artifact [284])

**Use this document for:**
- Understanding why certain tests fail
- Realistic expectations for code quality ratings
- Troubleshooting file creation steps
- Understanding sequencing dependencies

**Key sections:**
- "CRITICAL ISSUES SUMMARY" - Lists 10 common problems and fixes
- "DETAILED LINE-BY-LINE AUDIT" - Explains each component
- "Recommended Corrected Deployment Checklist" - Alternative approach if stuck

---

## QUICK REFERENCE - ARTIFACT MAPPING

| Step | Document | Artifact | Purpose |
|------|----------|----------|---------|
| 1 | Corrected-Deployment-Checklist.md | [285] | Main deployment guide (START HERE) |
| 2.1-2.2 | Corrected-Deployment-Checklist.md | [285] Phase 0 | Create sensitivity.py, optimization.py |
| 3.1 | Enhanced-CLI-Docstrings.md | [281] | Updated CLI code |
| 3.2-3.5 | Testing-Samples-Validation.md | [282] | Test file templates |
| 4-5 | Corrected-Deployment-Checklist.md | [285] Phases 2-5 | Validation and testing |
| Troubleshooting | Deployment-Audit-Report.md | [284] | Issue resolution |

---

## IMPLEMENTATION TIMELINE

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 0 | Create sensitivity.py, optimization.py | 10-15 min | Do First |
| 1 | Update CLI, create test files | 10-15 min | After Phase 0 |
| 2 | Install dependencies | 5 min | After Phase 1 |
| 3 | Run CLI validation tests | 5-10 min | After Phase 2 |
| 4-5 | Production deployment & verification | 5-10 min | Final |
| **TOTAL** | | **30-60 min** | **Ready for Production** |

---

## CRITICAL SUCCESS FACTORS

✅ **Phase 0 MUST complete before Phase 1** (sensitivity.py and optimization.py must exist)

✅ **Follow [285] sequentially** (do not skip phases)

✅ **Verify each phase** before proceeding to next

✅ **Use [284] for troubleshooting** only if issues arise

✅ **All 35+ tests must pass** before declaring "production ready"

---

## YOUR NEXT IMMEDIATE ACTION

**➡️ START HERE:** Open artifact [285] (Corrected-Deployment-Checklist.md)

→ Follow **Phase 0** exactly as written  
→ Create `sensitivity.py` with code from [285]  
→ Create `optimization.py` with code from [285]  
→ Verify both files exist and load correctly  

**Then proceed to Phase 1.**

---

**You are ready to deploy. All templates and code are provided. Follow [285] step-by-step.**