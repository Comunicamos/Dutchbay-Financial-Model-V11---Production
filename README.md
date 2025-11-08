# Dutch Bay Financial Model (V11)

## Overview
This repository contains the code, test suite, and configuration for the Dutch Bay 150MW Wind Farm financial model. The model supports robust IRR/NPV calculations via multiple solver methods, production-level static analysis, and a comprehensive Python test battery.

---

## Quickstart

### Requirements
- Python 3.8+
- numpy
- pandas
- scipy
- pytest (for testing)
- hypothesis (for property-based testing)
- pytest-cov (for code coverage)
- flake8, pylint (for code quality)
- mypy (for type checking, see notes below)

### Project Structure

- `/scripts/dutchbay_finmodel_enhanced.py` — Main model code (with type hints)
- `/tests/test_dutchbay_model.py` — Test suite using pytest/hypothesis
- `/outputs/irr_validation_cashflows.csv`, `/outputs/dutchbay_full_model.csv` — Example cash flow exports
- `/.pylintrc`, `/.flake8` — Lint/static analysis config

### Running the Model
You can run the main script for scenario analysis (see code comments for further options).

### Running Tests
From the project root, run:
```
pip install pytest hypothesis pytest-cov numpy pandas scipy flake8 pylint mypy
pytest tests/test_dutchbay_model.py -v --cov=scripts/dutchbay_finmodel_enhanced
```
You can also generate an HTML coverage report:
```
pytest --cov=scripts/dutchbay_finmodel_enhanced --cov-report=html
```

### Static Analysis
- Run `flake8 .` for PEP8/static code warnings
- Run `pylint scripts/dutchbay_finmodel_enhanced.py` for comprehensive linting

### Type Checking
Type checking is available if type hints are added to the scripts (see next steps).
```
mypy scripts/dutchbay_finmodel_enhanced.py
```

---
## Recommendations and Next Steps
- Add more type hints to functions for improved mypy results
- Add CI integration (pre-commit, Github Actions) for push/build hooks
- Expand property-based and integration testing
- Review the code with a third-party auditor for final investment sign-off

---
## Contact
For technical support or to report issues, contact the project sponsor or lead analyst.
