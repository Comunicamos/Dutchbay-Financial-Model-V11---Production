#!/usr/bin/env python3
"""
Comprehensive Validation Suite for Dutch Bay Financial Model
Runs all tests, linting, type checking, and validation
"""
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import os

project_root = Path(__file__).parent.parent
os.chdir(project_root)

class Colors:
    """Terminal colors for output formatting."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(title: str) -> None:
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def run_command(cmd: List[str], name: str) -> Tuple[bool, str]:
    """
    Run a command and return success status.
    
    Args:
        cmd: Command and arguments to run
        name: Name of the validation step
        
    Returns:
        Tuple of (success, output_message)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return (True, f"{name} passed")
        else:
            return (False, f"{name} failed with return code {result.returncode}")
    
    except FileNotFoundError:
        return (False, f"{name} tool not found. Install with: pip install {cmd[0]}")
    except subprocess.TimeoutExpired:
        return (False, f"{name} timed out after 5 minutes")
    except Exception as e:
        return (False, f"{name} error: {str(e)}")


def run_tests() -> Dict[str, bool]:
    """Run all validation steps and collect results."""
    results = {}
    
    # 1. Unit Tests
    print_header("UNIT TESTS")
    success, msg = run_command(
        ['pytest', 'tests/', '-v', '--tb=short', '-x'],
        'Unit Tests'
    )
    results['unit_tests'] = success
    if success:
        print_success(msg)
    else:
        print_error(msg)
    
    # 2. Test Coverage
    print_header("TEST COVERAGE ANALYSIS")
    success, msg = run_command(
        ['pytest', 'tests/', '--cov=scripts', '--cov-report=term-missing', '--cov-fail-under=70'],
        'Coverage Analysis'
    )
    results['coverage'] = success
    if success:
        print_success(msg + " (>70% coverage)")
    else:
        print_warning(msg + " (coverage below 70%)")
    
    # 3. Flake8 Code Style
    print_header("CODE STYLE (FLAKE8)")
    success, msg = run_command(
        ['flake8', 'scripts/', '--count', '--statistics'],
        'Flake8'
    )
    results['flake8'] = success
    if success:
        print_success(msg)
    else:
        print_warning(msg)
    
    # 4. Pylint Code Quality
    print_header("CODE QUALITY (PYLINT)")
    success, msg = run_command(
        ['pylint', 'scripts/dutch_bay_financial_model.py', '--fail-under=7.0'],
        'Pylint'
    )
    results['pylint'] = success
    if success:
        print_success(msg + " (rating >= 7.0)")
    else:
        print_warning(msg + " (rating < 7.0)")
    
    # 5. Type Checking (mypy) - V12 modules only
    print_header("TYPE CHECKING (MYPY)")
    success, msg = run_command(
        ['mypy', 'scripts/dutchbay_model_v12.py', '--ignore-missing-imports'],
        'Mypy'
    )
    results['mypy'] = success
    if success:
        print_success(msg)
    else:
        print_warning(msg)
    
    # 6. Critical Fixes Tests
    print_header("CRITICAL FIXES VALIDATION")
    success, msg = run_command(
        ['pytest', 'tests/test_critical_fixes.py', '-v'],
        'Critical Fixes Tests'
    )
    results['critical_fixes'] = success
    if success:
        print_success(msg)
    else:
        print_error(msg + " - CRITICAL ISSUES DETECTED")
    
    # 7. Additional Coverage Tests
    print_header("ADDITIONAL COVERAGE VALIDATION")
    success, msg = run_command(
        ['pytest', 'tests/test_additional_coverage.py', '-v'],
        'Additional Coverage Tests'
    )
    results['additional_coverage'] = success
    if success:
        print_success(msg)
    else:
        print_error(msg)
    
    # 8. Import Tests
    print_header("MODULE IMPORT VALIDATION")
    try:
        sys.path.insert(0, str(project_root / 'scripts'))
        import dutch_bay_financial_model
        import dutchbay_model_v12
        import monte_carlo
        import monte_carlo_enhanced
        import optimization
        import optimization_enhanced
        import sensitivity
        import sensitivity_enhanced
        import parameter_validation
        
        print_success("All modules import successfully")
        results['imports'] = True
    except ImportError as e:
        print_error(f"Module import failed: {e}")
        results['imports'] = False
    
    return results


def print_summary(results: Dict[str, bool]) -> None:
    """Print validation summary."""
    print_header("VALIDATION SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"Total validation steps: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    print(f"\nPass rate: {passed/total*100:.1f}%\n")
    
    # Critical checks
    critical_checks = ['unit_tests', 'critical_fixes', 'imports']
    critical_passed = all(results.get(k, False) for k in critical_checks)
    
    if critical_passed:
        print_success("All critical checks PASSED - Ready for production")
    else:
        print_error("Critical checks FAILED - Not ready for production")
        print("\nFailed critical checks:")
        for check in critical_checks:
            if not results.get(check, False):
                print(f"  - {check}")
    
    # Overall status
    print("\n" + "="*80)
    if passed == total:
        print(f"{Colors.BOLD}{Colors.GREEN}ALL VALIDATIONS PASSED ✓{Colors.RESET}")
        print("Model is production-ready and audit-compliant")
    elif critical_passed:
        print(f"{Colors.BOLD}{Colors.YELLOW}CORE VALIDATIONS PASSED{Colors.RESET}")
        print("Model is functional but has minor quality issues")
    else:
        print(f"{Colors.BOLD}{Colors.RED}VALIDATION FAILED{Colors.RESET}")
        print("Model requires fixes before production use")
    print("="*80 + "\n")


def main() -> int:
    """Main validation runner."""
    print(f"\n{Colors.BOLD}Dutch Bay Financial Model V11 - Comprehensive Validation Suite{Colors.RESET}")
    print(f"Working directory: {project_root}\n")
    
    results = run_tests()
    print_summary(results)
    
    # Return exit code based on critical checks
    critical_checks = ['unit_tests', 'critical_fixes', 'imports']
    critical_passed = all(results.get(k, False) for k in critical_checks)
    
    return 0 if critical_passed else 1


if __name__ == "__main__":
    sys.exit(main())
