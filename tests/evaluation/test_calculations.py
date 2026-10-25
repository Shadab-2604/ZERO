"""
Tests for Deterministic Calculations and Mathematical Operations.
Phase 4 Evaluation: Calculation Engine & Accuracy.
"""

import pytest
from app.core.calculator import LocalCalculator, CalculationResult


def test_calc_001_percentage_of():
    """MATH-001: What is 18% of 450? Expected: 81."""
    res = LocalCalculator.try_calculate("What is 18% of 450?")
    assert res.is_calculation is True
    assert res.result == 81
    assert "81" in res.formatted_result


def test_calc_002_percentage_discount():
    """MATH-002: Discount 1200 by 15%. Expected: 1020."""
    res = LocalCalculator.try_calculate("discount 1200 by 15%")
    assert res.is_calculation is True
    assert res.result == 1020


def test_calc_003_division_speed():
    """MATH-003: 1000 / 80. Expected: 12.5."""
    res = LocalCalculator.try_calculate("what is 1000 / 80")
    assert res.is_calculation is True
    assert res.result == 12.5


def test_calc_004_percentage_decrease_skipped_records():
    """MATH-004: 240 records skipped 5% -> reduce 240 by 5%. Expected: 228."""
    res = LocalCalculator.try_calculate("reduce 240 by 5%")
    assert res.is_calculation is True
    assert res.result == 228


def test_calc_005_arithmetic_average():
    """MATH-005: Average of 12, 19, 25, 44, 50. (12 + 19 + 25 + 44 + 50) / 5 = 30."""
    res = LocalCalculator.try_calculate("calculate: (12 + 19 + 25 + 44 + 50) / 5")
    assert res.is_calculation is True
    assert res.result == 30


def test_calc_006_unit_time_conversion():
    """MATH-007: Convert 2.5 hours to minutes -> 2.5 * 60 = 150."""
    res = LocalCalculator.try_calculate("calculate: 2.5 * 60")
    assert res.is_calculation is True
    assert res.result == 150


def test_calc_007_combined_percentages():
    """MATH-008: (0.10 * 250) + (0.20 * 100) = 25 + 20 = 45."""
    res = LocalCalculator.try_calculate("calculate: (0.10 * 250) + (0.20 * 100)")
    assert res.is_calculation is True
    assert res.result == 45


def test_calc_008_negative_numbers():
    """MATH-010: -45 + 18 - (-12) = -15."""
    res = LocalCalculator.try_calculate("calculate: -45 + 18 - (-12)")
    assert res.is_calculation is True
    assert res.result == -15


def test_calc_009_division_by_zero_fails_safely():
    """MATH-009: Division by zero must not crash the evaluator or application."""
    res = LocalCalculator.try_calculate("calculate: 100 / 0")
    # Should safely fail and return is_calculation=False or handle error without crashing
    assert res.is_calculation is False


def test_calc_010_ast_evaluator_rejects_unsafe_attributes():
    """Verify evaluator strictly rejects arbitrary code or object lookups."""
    res = LocalCalculator.try_calculate("calculate: __import__('os').system('dir')")
    assert res.is_calculation is False
