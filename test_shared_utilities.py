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


def compare_probability_results(result1, result2, tolerance=1e-10,
                                description1="result1",
                                description2="result2"):
    """
    Compare two probability calculation results for equivalence.

    Args:
        result1: Tuple of (macrostates, probs, ...)
        result2: Tuple of (macrostates, probs, ...)
        tolerance: Numerical tolerance for probability comparison
        description1: Description of first result
        description2: Description of second result

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
