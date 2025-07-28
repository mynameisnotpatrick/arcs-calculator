# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

"""
Shared test utilities for Arcs dice calculator test suite.

This module provides common validation functions used across multiple
test files to reduce code duplication and ensure consistent testing
standards.
"""

import pytest

import arcs_funcs

# Standard test case patterns for reuse across test files
STANDARD_TEST_CASES = [
    (1, 0, 0),  # Single skirmish
    (0, 1, 0),  # Single assault
    (0, 0, 1),  # Single raid
    (1, 1, 0),  # Skirmish + assault
    (1, 0, 1),  # Skirmish + raid
    (0, 1, 1),  # Assault + raid
    (1, 1, 1),  # One of each
    (2, 1, 0),  # Multiple skirmish
    (0, 2, 1),  # Multiple assault
    (1, 0, 2),  # Multiple raid
]

STANDARD_MULTIROLL_CONFIGS = [
    {'skirmish': 2, 'assault': 1, 'raid': 0},
    {'skirmish': 0, 'assault': 2, 'raid': 1},
    {'skirmish': 1, 'assault': 0, 'raid': 2},
    {'skirmish': 1, 'assault': 1, 'raid': 1},
]

# Standard constraint test parameters
CONSTRAINT_TEST_PARAMS = [
    {'min_hits': 1},
    {'max_hits': 3},
    {'min_damage': 1},
    {'max_damage': 2},
    {'min_keys': 1},
    {'max_keys': 2},
    {'min_building_hits': 1},
    {'max_building_hits': 2},
    {'min_hits': 1, 'max_hits': 3},
    {'min_damage': 0, 'max_damage': 2},
]


def validate_standard_probability_calculation(test_cases, description=""):
    """
    Validate probability calculations for standard test cases.

    Args:
        test_cases: List of (skirmish, assault, raid) tuples
        description: Optional description for error messages

    Returns:
        dict: Results for each test case
    """
    results = {}

    for i, (skirmish, assault, raid) in enumerate(test_cases):
        if skirmish + assault + raid == 0:
            continue  # Skip empty dice combinations

        desc = f"{description} case {i+1}" if description else f"case {i+1}"

        try:
            macrostates, probs, *_ = arcs_funcs.compute_probabilities(
                skirmish, assault, raid, fresh_targets=0,
                convert_intercepts=False
            )

            validate_dice_calculation_result(macrostates, probs, desc)
            results[(skirmish, assault, raid)] = (macrostates, probs)

        except Exception as e:
            raise AssertionError(f"Failed {desc}: {e}")

    return results


def validate_constraint_evaluation(hits, damage, buildings, keys,
                                   constraint_params, expected_result):
    """
    Validate constraint evaluation for given parameters.

    Args:
        hits, damage, buildings, keys: Outcome values
        constraint_params: Dict of constraint parameters
        expected_result: Expected boolean result

    Returns:
        bool: Actual result from evaluate_truth_table
    """
    result = arcs_funcs.evaluate_truth_table(
        hits, damage, buildings, keys, **constraint_params)

    assert result == expected_result, \
        f"Constraint evaluation failed: hits={hits}, damage={damage}, " \
        f"buildings={buildings}, keys={keys}, " \
        f"constraints={constraint_params}, " \
        f"expected={expected_result}, got={result}"

    return result


def validate_probability_parsing(labels, probs, constraints,
                                 expected_conditions=None):
    """
    Validate probability parsing with constraint combinations.

    Args:
        labels: List of outcome labels
        probs: List of probabilities
        constraints: Dict of constraint parameters
        expected_conditions: Expected condition strings (optional)

    Returns:
        str: Result string from parse_label_for_probability
    """
    result = arcs_funcs.parse_label_for_probability(
        labels, probs, **constraints)

    # Basic validation
    assert isinstance(result, str), "Result should be a string"
    assert "Probability of" in result, "Result should contain probability text"

    # Extract probability value
    try:
        prob_value = float(result.split()[-1])
        assert 0 <= prob_value <= 1, \
            f"Probability value {prob_value} outside valid range [0,1]"
    except (ValueError, IndexError):
        raise AssertionError(f"Could not extract probability from: {result}")

    # Check expected conditions if provided
    if expected_conditions:
        for condition in expected_conditions:
            assert condition in result, \
                f"Expected condition '{condition}' not found in " \
                f"result: {result}"

    return result


def validate_multiroll_equivalence(individual_rolls, combined_totals):
    """
    Validate that multi-roll totals match combined calculations.

    Args:
        individual_rolls: List of roll dictionaries
        combined_totals: Expected total dice counts

    Returns:
        tuple: (actual_totals, matches_expected)
    """
    actual_totals = {
        'skirmish': sum(roll['skirmish'] for roll in individual_rolls),
        'assault': sum(roll['assault'] for roll in individual_rolls),
        'raid': sum(roll['raid'] for roll in individual_rolls)
    }

    matches = all(
        actual_totals[dice_type] == combined_totals.get(dice_type, 0)
        for dice_type in ['skirmish', 'assault', 'raid']
    )

    assert matches, \
        f"Multi-roll totals don't match: actual={actual_totals}, " \
        f"expected={combined_totals}"

    return actual_totals, matches


def validate_multiroll_configuration(rolls):
    """
    Validate a complete multi-roll configuration.

    Args:
        rolls: List of roll dictionaries

    Returns:
        dict: Summary statistics
    """
    assert isinstance(rolls, list), "Rolls should be a list"
    assert len(rolls) > 0, "Should have at least one roll"

    total_dice = 0
    non_empty_rolls = 0

    for i, roll in enumerate(rolls):
        validate_roll_dictionary(roll, f"roll {i+1}")

        roll_total = roll['skirmish'] + roll['assault'] + roll['raid']
        if roll_total > 0:
            non_empty_rolls += 1
            total_dice += roll_total

    assert non_empty_rolls > 0, "Should have at least one non-empty roll"

    return {
        'total_rolls': len(rolls),
        'non_empty_rolls': non_empty_rolls,
        'total_dice': total_dice
    }


@pytest.fixture
def standard_dice_combinations():
    """Pytest fixture providing standard dice combinations."""
    return STANDARD_TEST_CASES


@pytest.fixture
def standard_multiroll_configs():
    """Pytest fixture providing standard multi-roll configurations."""
    return STANDARD_MULTIROLL_CONFIGS


@pytest.fixture
def constraint_test_params():
    """Pytest fixture providing standard constraint test parameters."""
    return CONSTRAINT_TEST_PARAMS


class BaseProbabilityTest:
    """Base class for probability calculation testing."""

    def setup_method(self):
        """Setup method called before each test."""
        self.tolerance = 1e-10
        self.standard_cases = STANDARD_TEST_CASES
        self.standard_configs = STANDARD_MULTIROLL_CONFIGS

    def validate_basic_calculation(self, skirmish, assault, raid,
                                   fresh_targets=0, convert_intercepts=False):
        """Common validation logic for basic probability calculations."""
        macrostates, probs, *_ = arcs_funcs.compute_probabilities(
            skirmish, assault, raid, fresh_targets, convert_intercepts
        )

        validate_dice_calculation_result(
            macrostates, probs,
            f"calculation({skirmish}, {assault}, {raid})"
        )

        return macrostates, probs


def validate_probability_distribution(
        probs, tolerance=1e-10, description="probability distribution"):
    """
    Validate that a list of probabilities forms a valid probability
    distribution.

    Args:
        probs: List of probability values
        tolerance: Numerical tolerance for sum validation
        description: Description for error messages

    Raises:
        AssertionError: If probabilities are invalid
    """
    assert len(probs) > 0, f"{description} should have at least one value"

    # Check for non-negative probabilities
    negative_probs = [p for p in probs if p < 0]
    assert not negative_probs, \
        f"{description} has negative probabilities: {negative_probs}"

    # Check that probabilities sum to 1.0
    total_prob = sum(probs)
    assert abs(total_prob - 1.0) < tolerance, \
        f"{description} probabilities sum to {total_prob:.12f}, " \
        f"expected 1.0 (tolerance: {tolerance})"


def validate_macrostate_structure(macrostates, description="macrostates"):
    """
    Validate that macrostates have the expected structure.

    Args:
        macrostates: List of macrostate strings
        description: Description for error messages

    Raises:
        AssertionError: If macrostates are invalid
    """
    assert len(macrostates) > 0, \
        f"{description} should have at least one state"

    # Check that all macrostates are strings
    non_strings = [m for m in macrostates if not isinstance(m, str)]
    assert not non_strings, \
        f"{description} contains non-string values: {non_strings}"

    # Check for duplicates
    unique_states = set(macrostates)
    assert len(unique_states) == len(macrostates), \
        f"{description} contains {len(macrostates) - len(unique_states)} " \
        f"duplicate states"


def validate_dice_calculation_result(macrostates, probs,
                                     description="dice calculation"):
    """
    Comprehensive validation of dice calculation results.

    Args:
        macrostates: List of macrostate strings
        probs: List of corresponding probabilities
        description: Description for error messages

    Raises:
        AssertionError: If results are invalid
    """
    # Validate basic structure
    assert len(macrostates) == len(probs), \
        f"{description}: macrostates length ({len(macrostates)}) != " \
        f"probabilities length ({len(probs)})"

    # Validate macrostates
    validate_macrostate_structure(macrostates, f"{description} macrostates")

    # Validate probability distribution
    validate_probability_distribution(
        probs, description=f"{description} probs")


def validate_joint_probability_table(
        df, description="joint probability table"):
    """
    Validate a joint probability table DataFrame.

    Args:
        df: DataFrame with columns ['hits', 'damage', 'building_hits',
            'keys', 'prob']
        description: Description for error messages

    Raises:
        AssertionError: If DataFrame is invalid
    """
    required_columns = {'hits', 'damage', 'building_hits', 'keys', 'prob'}
    missing_columns = required_columns - set(df.columns)
    assert not missing_columns, \
        f"{description} missing columns: {missing_columns}"

    # Validate probability column
    validate_probability_distribution(
        df['prob'].tolist(),
        description=f"{description} probabilities")

    # Validate that outcome variables are non-negative integers
    outcome_vars = ['hits', 'damage', 'building_hits', 'keys']
    for var in outcome_vars:
        assert (df[var] >= 0).all(), \
            f"{description} has negative {var} values"
        assert df[var].dtype.kind in 'iu', \
            f"{description} {var} should be integer type, got {df[var].dtype}"


def validate_dice_constraints(skirmish_dice, assault_dice, raid_dice,
                              max_dice_per_type=6):
    """
    Validate that dice counts respect game constraints.

    Args:
        skirmish_dice: Number of skirmish dice
        assault_dice: Number of assault dice
        raid_dice: Number of raid dice
        max_dice_per_type: Maximum dice allowed per type

    Raises:
        AssertionError: If dice counts are invalid
    """
    dice_types = {
        'skirmish': skirmish_dice,
        'assault': assault_dice,
        'raid': raid_dice
    }

    for dice_type, count in dice_types.items():
        assert isinstance(count, int), \
            f"{dice_type}_dice should be integer, got {type(count)}"
        assert count >= 0, \
            f"{dice_type}_dice should be non-negative, got {count}"
        assert count <= max_dice_per_type, \
            f"{dice_type}_dice should be <= {max_dice_per_type}, got {count}"


def compare_probability_results(result1, result2, description1="result1",
                                description2="result2", tolerance=1e-10):
    """
    Compare two probability calculation results for equivalence.

    Args:
        result1: Tuple of (macrostates, probs, ...)
        result2: Tuple of (macrostates, probs, ...)
        description1: Description of first result
        description2: Description of second result
        tolerance: Numerical tolerance for probability comparison

    Raises:
        AssertionError: If results differ significantly
    """
    macrostates1, probs1 = result1[0], result1[1]
    macrostates2, probs2 = result2[0], result2[1]

    # Validate both results first
    validate_dice_calculation_result(macrostates1, probs1, description1)
    validate_dice_calculation_result(macrostates2, probs2, description2)

    # Check same number of outcomes
    assert len(macrostates1) == len(macrostates2), \
        f"{description1} has {len(macrostates1)} outcomes, " \
        f"{description2} has {len(macrostates2)} outcomes"

    # Convert to dictionaries for comparison
    dict1 = dict(zip(macrostates1, probs1))
    dict2 = dict(zip(macrostates2, probs2))

    # Check that all states match
    states1 = set(macrostates1)
    states2 = set(macrostates2)

    missing_in_1 = states2 - states1
    missing_in_2 = states1 - states2

    assert not missing_in_1, \
        f"States in {description2} but not {description1}: {missing_in_1}"
    assert not missing_in_2, \
        f"States in {description1} but not {description2}: {missing_in_2}"

    # Compare probabilities for each state
    max_error = 0
    worst_state = None

    for state in states1:
        prob1 = dict1[state]
        prob2 = dict2[state]
        error = abs(prob1 - prob2)

        if error > max_error:
            max_error = error
            worst_state = state

        assert error < tolerance, \
            f"Probability mismatch for state '{state}': " \
            f"{description1}={prob1:.12f}, {description2}={prob2:.12f}, " \
            f"error={error:.2e}"

    return max_error, worst_state


def validate_marginal_distribution(
        df, variable, description="marginal distribution"):
    """
    Validate a marginal distribution from a joint probability table.

    Args:
        df: Joint probability DataFrame
        variable: Variable name to compute marginal for
        description: Description for error messages

    Raises:
        AssertionError: If marginal distribution is invalid
    """
    assert variable in df.columns, \
        f"Variable '{variable}' not found in DataFrame columns"

    marginal = df.groupby(variable)['prob'].sum()
    marginal_probs = marginal.values.tolist()

    validate_probability_distribution(
        marginal_probs,
        description=f"{description} for {variable}"
    )

    return marginal


def validate_roll_dictionary(roll, description="roll dictionary"):
    """
    Validate a roll dictionary structure for multi-roll functionality.

    Args:
        roll: Dictionary with keys 'skirmish', 'assault', 'raid'
        description: Description for error messages

    Raises:
        AssertionError: If roll dictionary is invalid
    """
    required_keys = {'skirmish', 'assault', 'raid'}

    assert isinstance(roll, dict), f"{description} should be a dictionary"

    missing_keys = required_keys - set(roll.keys())
    assert not missing_keys, f"{description} missing keys: {missing_keys}"

    # Validate dice counts
    validate_dice_constraints(
        roll['skirmish'], roll['assault'], roll['raid']
    )
