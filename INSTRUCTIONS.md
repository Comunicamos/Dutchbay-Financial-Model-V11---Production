# Dutch Bay Wind Farm Financial Model - Integration & Documentation Guide

## 1. Directory Structure
- `inputs/` — CSV for input variables and scenarios (input_variables.csv, scenario_matrix.csv)
- `outputs/` — Model and scenario results, audit files (montecarlo_summary_SAMPLE.csv, scenario_1_SAMPLE.csv, Audit_Template.xlsx)
- `scripts/` — Python scripts, tests, requirements.txt
- `docs/` — README.md, Excel_Merge_QuickInstructions.txt, Excel_Audit_Guide.txt, this file

## 2. Setup
- Run `bash install.sh` from the root package directory (creates a .venv, installs dependencies).
- Use Python 3.10+ (Apple M1 native or via Miniforge).

## 3. Running the Model
- To run the core model for default variables: `python scripts/dutch_bay_financial_model.py`
  - Output: `outputs/dutchbay_20yr_outputs.csv`
- To run all scenarios (Monte Carlo sweep): `python scripts/montecarlo_scenarios.py` or `python scripts/montecarlo_grid.py`

## 4. Testing
- Run `pytest scripts/` to run all unittests and property-based tests.
- Run `pytest --cov=scripts scripts/` for coverage.
- Run code quality checks: `flake8 scripts/` and `pylint scripts/`.
- Static typing: `mypy scripts/`

## 5. Excel Auditing
- Detailed merge and audit instructions are in `docs/Excel_Merge_QuickInstructions.txt` and `outputs/Excel_Audit_Guide.txt`.

## 6. Extending the Model
- To add scenarios, update `inputs/scenario_matrix.csv` and rerun scenario scripts.
- All parameters are modular; scripts are designed for scalable extension, robustness, and reproducibility.

---

**For full documentation and latest update, see README.md**
