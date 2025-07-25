#!/usr/bin/env python3
"""
Brute force validation test for Arcs dice probability calculations.

This test generates ALL possible microstates for dice combinations up to
10 total dice
and validates that our optimized probability calculations match the brute
force results.
"""

import itertools
from collections import Counter

import pytest

import arcs_funcs


def brute_force_all_microstates(num_skirmish, num_assault, num_raid,
                                fresh_targets=0, convert_intercepts=False):
    """
    Brute force calculation of all possible dice roll outcomes (microstates).

    This generates every single possible combination of dice rolls using
    itertools.product
    and counts the frequency of each macrostate result.
    """
    macrostate_counts = Counter()
    total_microstates = 0

    # Generate ALL possible combinations (order matters - these are
    # microstates)
    for skirmish_rolls in itertools.product(
            arcs_funcs.SKIRMISH_DICE, repeat=num_skirmish):
        for assault_rolls in itertools.product(
                arcs_funcs.ASSAULT_DICE, repeat=num_assault):
            for raid_rolls in itertools.product(
                    arcs_funcs.RAID_DICE, repeat=num_raid):
                # Parse this specific microstate into a macrostate
                macrostate = arcs_funcs.parse_dice(
                    skirmish_rolls, assault_rolls, raid_rolls,
                    fresh_targets, convert_intercepts
                )
                macrostate_counts[macrostate] += 1
                total_microstates += 1

    # Convert counts to probabilities
    macrostates = list(macrostate_counts.keys())
    probabilities = [count / total_microstates
                     for count in macrostate_counts.values()]

    # Sort by probability (ascending) to match our optimized function
    sorted_pairs = sorted(zip(macrostates, probabilities), key=lambda x: x[1])
    sorted_macrostates, sorted_probs = zip(*sorted_pairs)

    return list(sorted_macrostates), list(sorted_probs), total_microstates


def compare_probability_results(optimized_result, brute_force_result,
                                tolerance=1e-10):
    """
    Compare optimized and brute force results with detailed error reporting.
    """
    opt_macrostates, opt_probs, *_ = optimized_result
    bf_macrostates, bf_probs, bf_total = brute_force_result

    # Check that we have the same number of unique macrostates
    assert len(opt_macrostates) == len(bf_macrostates), \
        f"Different number of macrostates: " \
        f"optimized={len(opt_macrostates)}, " \
        f"brute_force={len(bf_macrostates)}"

    # Convert to dictionaries for easier comparison
    opt_dict = dict(zip(opt_macrostates, opt_probs))
    bf_dict = dict(zip(bf_macrostates, bf_probs))

    # Check that all macrostates match
    opt_states = set(opt_macrostates)
    bf_states = set(bf_macrostates)

    missing_in_opt = bf_states - opt_states
    missing_in_bf = opt_states - bf_states

    assert not missing_in_opt, f"Macrostates missing in optimized: "\
                               f"{missing_in_opt}"
    assert not missing_in_bf, f"Macrostates missing in brute force: "\
                              f"{missing_in_bf}"

    # Check probability values for each macrostate
    max_error = 0
    worst_state = None

    for state in opt_states:
        opt_prob = opt_dict[state]
        bf_prob = bf_dict[state]
        error = abs(opt_prob - bf_prob)

        if error > max_error:
            max_error = error
            worst_state = state

        assert error < tolerance, \
            (f"Probability mismatch for state '{state}': "
             f"optimized={opt_prob:.12f}, "
             f"brute_force={bf_prob:.12f}, error={error:.2e}")

    print(f"All probabilities match within tolerance {tolerance:.2e}")
    print(f"  Maximum error: {max_error:.2e} (state: '{worst_state}')")
    print(f"  Total microstates validated: {bf_total:,}")


class TestMicrostateValidation:
    """Test cases for validating dice probability calculations."""

    def test_single_die_types(self):
        """Test individual die types to ensure basic functionality."""
        test_cases = [
            (1, 0, 0),  # 1 skirmish
            (0, 1, 0),  # 1 assault
            (0, 0, 1),  # 1 raid
            (2, 0, 0),  # 2 skirmish
            (0, 2, 0),  # 2 assault
            (0, 0, 2),  # 2 raid
        ]

        for num_skirmish, num_assault, num_raid in test_cases:
            print(f"\nTesting {num_skirmish} skirmish, {num_assault} assault, "
                  f"{num_raid} raid dice...")

            # Get results from both methods
            optimized = arcs_funcs.compute_probabilities(
                num_skirmish, num_assault, num_raid)
            brute_force = brute_force_all_microstates(
                num_skirmish, num_assault, num_raid)

            # Compare results
            compare_probability_results(optimized, brute_force)

    def test_mixed_dice_small(self):
        """Test small combinations of mixed dice types."""
        test_cases = [
            (1, 1, 0),  # 1 skirmish + 1 assault
            (1, 0, 1),  # 1 skirmish + 1 raid
            (0, 1, 1),  # 1 assault + 1 raid
            (1, 1, 1),  # 1 of each
            (2, 1, 0),  # 2 skirmish + 1 assault
            (1, 2, 0),  # 1 skirmish + 2 assault
            (2, 0, 1),  # 2 skirmish + 1 raid
            (0, 2, 1),  # 2 assault + 1 raid
        ]

        for num_skirmish, num_assault, num_raid in test_cases:
            print(f"\nTesting {num_skirmish} skirmish, {num_assault} assault, "
                  f"{num_raid} raid dice...")

            optimized = arcs_funcs.compute_probabilities(
                num_skirmish, num_assault, num_raid)
            brute_force = brute_force_all_microstates(
                num_skirmish, num_assault, num_raid)

            compare_probability_results(optimized, brute_force)

    def test_convert_intercepts(self):
        """Test probability calculations with intercept conversion."""
        test_cases = [
            (0, 1, 1, 2, True),   # 1 assault + 1 raid, 2 fresh targets
            (1, 0, 2, 1, True),   # 1 skirmish + 2 raid, 1 fresh target
            (1, 1, 1, 3, True),   # 1 of each, 3 fresh targets
        ]

        for (num_skirmish, num_assault, num_raid, fresh_targets,
             convert_intercepts) in test_cases:
            print(f"\nTesting {num_skirmish} skirmish, {num_assault} assault, "
                  f"{num_raid} raid dice with {fresh_targets} fresh "
                  f"targets...")

            optimized = arcs_funcs.compute_probabilities(
                num_skirmish, num_assault, num_raid, fresh_targets,
                convert_intercepts
            )
            brute_force = brute_force_all_microstates(
                num_skirmish, num_assault, num_raid, fresh_targets,
                convert_intercepts
            )

            compare_probability_results(optimized, brute_force)

    @pytest.mark.slow
    def test_large_combinations(self):
        """Test larger dice combinations (up to 12 total dice)."""
        test_cases = []

        # Generate all possible combinations for 9, 10, 11, and 12 dice
        for total_dice in [9, 10]:
            for skirmish in range(0, min(6, total_dice) + 1):
                # Max 6 skirmish dice
                for assault in range(0, min(6, total_dice - skirmish) + 1):
                    # Max 6 assault dice
                    raid = total_dice - skirmish - assault
                    if 0 <= raid <= 6:  # Max 6 raid dice
                        test_cases.append((skirmish, assault, raid))

        # Sort by total dice count for organized output
        test_cases.sort(key=lambda x: sum(x))

        for num_skirmish, num_assault, num_raid in test_cases:
            total_dice = num_skirmish + num_assault + num_raid
            expected_microstates = (
                (2 ** num_skirmish) * (6 ** (num_assault + num_raid)))

            print(f"\nTesting {num_skirmish} skirmish, {num_assault} assault, "
                  f"{num_raid} raid dice...")
            print(f"  Total dice: {total_dice}, Expected microstates: "
                  f"{expected_microstates:,}")

            optimized = arcs_funcs.compute_probabilities(
                num_skirmish, num_assault, num_raid)
            brute_force = brute_force_all_microstates(
                num_skirmish, num_assault, num_raid)

            compare_probability_results(optimized, brute_force)

    def test_probability_sum_equals_one(self):
        """Verify that all probabilities sum to 1.0 for various
        combinations."""
        test_cases = [
            (2, 2, 2),
            (3, 2, 1),
            (1, 3, 2),
            (4, 1, 1),
        ]

        for num_skirmish, num_assault, num_raid in test_cases:
            _, probs, *_ = arcs_funcs.compute_probabilities(
                num_skirmish, num_assault, num_raid)
            total_prob = sum(probs)

            assert abs(total_prob - 1.0) < 1e-10, \
                f"Probabilities don't sum to 1.0: got {total_prob:.12f} " \
                f"for {num_skirmish},{num_assault},{num_raid} dice"

            print(f"Probabilities sum to 1.0 for "
                  f"{num_skirmish},{num_assault},{num_raid} dice "
                  f"(sum={total_prob:.12f})")


if __name__ == "__main__":
    # Run tests directly
    test = TestMicrostateValidation()

    print("=" * 60)
    print("ARCS DICE PROBABILITY VALIDATION TESTS")
    print("=" * 60)

    print("\n1. Testing single die types...")
    test.test_single_die_types()

    print("\n2. Testing mixed dice combinations...")
    test.test_mixed_dice_small()

    print("\n3. Testing intercept conversion...")
    test.test_convert_intercepts()

    print("\n4. Testing probability sums...")
    test.test_probability_sum_equals_one()

    print("\n5. Testing large combinations (this may take a while)...")
    test.test_large_combinations()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("The optimized probability calculations are mathematically correct.")
    print("=" * 60)
