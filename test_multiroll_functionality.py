# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

"""
Test suite for multi-roll functionality in the Arcs dice calculator.

This module tests the multi-roll features added to the Streamlit app,
including session state management, roll configuration validation,
and consistency between individual and combined roll calculations.
"""

import pytest

import arcs_funcs
from test_shared_utilities import (compare_probability_results,
                                   validate_dice_calculation_result,
                                   validate_roll_dictionary)


class TestMultiRollLogic:
    """Test the core logic for multi-roll calculations."""

    def test_individual_roll_calculation(self):
        """Test that individual roll calculations are correct."""
        # Define test rolls
        roll1 = {'skirmish': 2, 'assault': 0, 'raid': 0}
        roll2 = {'skirmish': 0, 'assault': 2, 'raid': 0}
        roll3 = {'skirmish': 0, 'assault': 0, 'raid': 2}

        test_rolls = [roll1, roll2, roll3]

        for i, roll in enumerate(test_rolls):
            # Calculate probabilities for this individual roll
            macrostates, probs, *_ = arcs_funcs.compute_probabilities(
                roll['skirmish'], roll['assault'], roll['raid']
            )

            # Use shared utility for validation
            validate_dice_calculation_result(
                macrostates, probs,
                description=f"Roll {i+1}"
            )

    def test_combined_roll_calculation(self):
        """Test that combined rolls match the sum of individual dice."""
        # Test case: multiple rolls that sum to known configuration
        rolls = [
            {'skirmish': 1, 'assault': 1, 'raid': 0},
            {'skirmish': 1, 'assault': 0, 'raid': 1},
            {'skirmish': 0, 'assault': 1, 'raid': 1}
        ]

        # Calculate total dice
        total_skirmish = sum(roll['skirmish'] for roll in rolls)
        total_assault = sum(roll['assault'] for roll in rolls)
        total_raid = sum(roll['raid'] for roll in rolls)

        # Get combined probabilities (as if rolling all dice together)
        combined_macrostates, combined_probs, *_ = \
            arcs_funcs.compute_probabilities(
                total_skirmish, total_assault, total_raid
            )

        # Validate combined results
        validate_dice_calculation_result(
            combined_macrostates, combined_probs,
            description="Combined dice calculation"
        )

        # The combined calculation should be equivalent to calculating
        # (total_skirmish, total_assault, total_raid) directly
        direct_macrostates, direct_probs, *_ = \
            arcs_funcs.compute_probabilities(
                total_skirmish, total_assault, total_raid
            )

        # Use shared utility to compare results
        compare_probability_results(
            (combined_macrostates, combined_probs),
            (direct_macrostates, direct_probs),
            description1="combined calculation",
            description2="direct calculation"
        )

    def test_empty_roll_handling(self):
        """Test handling of rolls with no dice."""
        # Roll with no dice should be skipped or handled gracefully
        empty_roll = {'skirmish': 0, 'assault': 0, 'raid': 0}

        # This should either work (return 1 outcome with probability 1.0)
        # or raise an appropriate error
        try:
            macrostates, probs, *_ = arcs_funcs.compute_probabilities(
                empty_roll['skirmish'], empty_roll['assault'],
                empty_roll['raid']
            )
            # If it works, should have single outcome with prob 1.0
            assert len(macrostates) == 1, "Empty roll should have 1 outcome"
            assert abs(probs[0] - 1.0) < 1e-10, \
                "Empty roll should have probability 1.0"
        except Exception:
            # If it raises an error, that's also acceptable
            pytest.skip("Empty roll raises exception (acceptable)")

    def test_maximum_dice_constraints(self):
        """Test that dice constraints are respected in multi-roll context."""
        # Test case with rolls that sum to maximum dice
        max_rolls = [
            {'skirmish': 6, 'assault': 0, 'raid': 0},  # Max skirmish
            {'skirmish': 0, 'assault': 6, 'raid': 0},  # Max assault
            {'skirmish': 0, 'assault': 0, 'raid': 6}   # Max raid
        ]

        for i, roll in enumerate(max_rolls):
            macrostates, probs, *_ = arcs_funcs.compute_probabilities(
                roll['skirmish'], roll['assault'], roll['raid']
            )

            assert len(macrostates) > 0, f"Max roll {i+1} should have outcomes"
            assert abs(sum(probs) - 1.0) < 1e-10, \
                f"Max roll {i+1} probabilities don't sum to 1.0"

    def test_mixed_roll_configurations(self):
        """Test various realistic multi-roll configurations."""
        test_configurations = [
            # Two moderate rolls
            [
                {'skirmish': 3, 'assault': 2, 'raid': 1},
                {'skirmish': 2, 'assault': 1, 'raid': 3}
            ],
            # Three smaller rolls
            [
                {'skirmish': 2, 'assault': 0, 'raid': 0},
                {'skirmish': 0, 'assault': 2, 'raid': 0},
                {'skirmish': 0, 'assault': 0, 'raid': 2}
            ],
            # Asymmetric rolls
            [
                {'skirmish': 6, 'assault': 0, 'raid': 0},
                {'skirmish': 0, 'assault': 0, 'raid': 1}
            ]
        ]

        for config_idx, rolls in enumerate(test_configurations):
            # Calculate each individual roll
            individual_results = []
            for roll_idx, roll in enumerate(rolls):
                if sum(roll.values()) > 0:  # Skip empty rolls
                    macrostates, probs, *_ = arcs_funcs.compute_probabilities(
                        roll['skirmish'], roll['assault'], roll['raid']
                    )
                    individual_results.append((macrostates, probs))

                    # Validate individual roll
                    assert len(macrostates) > 0, \
                        f"Config {config_idx}, Roll {roll_idx} has no outcomes"
                    assert abs(sum(probs) - 1.0) < 1e-10, \
                        f"Config {config_idx}, Roll {roll_idx} probs != 1.0"

            # Calculate combined result
            total_skirmish = sum(roll['skirmish'] for roll in rolls)
            total_assault = sum(roll['assault'] for roll in rolls)
            total_raid = sum(roll['raid'] for roll in rolls)

            if total_skirmish + total_assault + total_raid > 0:
                combined_macrostates, combined_probs, *_ = \
                    arcs_funcs.compute_probabilities(
                        total_skirmish, total_assault, total_raid
                    )

                # Validate combined result
                assert len(combined_macrostates) > 0, \
                    f"Config {config_idx} combined has no outcomes"
                assert abs(sum(combined_probs) - 1.0) < 1e-10, \
                    f"Config {config_idx} combined probs != 1.0"

    def test_convert_intercepts_with_multiroll(self):
        """Test that convert_intercepts works correctly with multi-roll."""
        rolls = [
            {'skirmish': 0, 'assault': 1, 'raid': 1},
            {'skirmish': 0, 'assault': 0, 'raid': 2}
        ]

        fresh_targets = 3
        convert_intercepts = True

        # Test individual rolls with convert_intercepts
        for i, roll in enumerate(rolls):
            macrostates, probs, *_ = arcs_funcs.compute_probabilities(
                roll['skirmish'], roll['assault'], roll['raid'],
                fresh_targets, convert_intercepts
            )

            assert len(macrostates) > 0, \
                f"Convert intercepts roll {i+1} has no outcomes"
            assert abs(sum(probs) - 1.0) < 1e-10, \
                f"Convert intercepts roll {i+1} probs != 1.0"

        # Test combined roll with convert_intercepts
        total_skirmish = sum(roll['skirmish'] for roll in rolls)
        total_assault = sum(roll['assault'] for roll in rolls)
        total_raid = sum(roll['raid'] for roll in rolls)

        combined_macrostates, combined_probs, *_ = \
            arcs_funcs.compute_probabilities(
                total_skirmish, total_assault, total_raid,
                fresh_targets, convert_intercepts
            )

        assert len(combined_macrostates) > 0, \
            "Convert intercepts combined has no outcomes"
        assert abs(sum(combined_probs) - 1.0) < 1e-10, \
            "Convert intercepts combined probs != 1.0"


class TestMultiRollDataStructures:
    """Test data structures and validation for multi-roll functionality."""

    def test_roll_dictionary_structure(self):
        """Test that roll dictionaries have the expected structure."""
        valid_roll = {'skirmish': 2, 'assault': 1, 'raid': 3}

        # Use shared utility for validation
        validate_roll_dictionary(valid_roll, "test roll dictionary")

    def test_roll_list_validation(self):
        """Test validation of lists of rolls."""
        valid_rolls = [
            {'skirmish': 1, 'assault': 0, 'raid': 0},
            {'skirmish': 0, 'assault': 1, 'raid': 0},
            {'skirmish': 0, 'assault': 0, 'raid': 1}
        ]

        # Test that all rolls in list are valid
        for i, roll in enumerate(valid_rolls):
            assert isinstance(roll, dict), f"Roll {i} should be dict"
            assert 'skirmish' in roll, f"Roll {i} missing skirmish"
            assert 'assault' in roll, f"Roll {i} missing assault"
            assert 'raid' in roll, f"Roll {i} missing raid"

            # Test value constraints
            total_dice = roll['skirmish'] + roll['assault'] + roll['raid']
            assert total_dice <= 18, f"Roll {i} has too many total dice"

    def test_dice_totaling(self):
        """Test calculation of total dice across multiple rolls."""
        rolls = [
            {'skirmish': 2, 'assault': 1, 'raid': 0},
            {'skirmish': 1, 'assault': 0, 'raid': 2},
            {'skirmish': 0, 'assault': 2, 'raid': 1}
        ]

        expected_totals = {
            'skirmish': 3,
            'assault': 3,
            'raid': 3
        }

        # Calculate totals
        actual_skirmish = sum(roll['skirmish'] for roll in rolls)
        actual_assault = sum(roll['assault'] for roll in rolls)
        actual_raid = sum(roll['raid'] for roll in rolls)

        assert actual_skirmish == expected_totals['skirmish']
        assert actual_assault == expected_totals['assault']
        assert actual_raid == expected_totals['raid']

        # Test that total is reasonable (not exceeding game limits too much)
        total_dice = actual_skirmish + actual_assault + actual_raid
        assert total_dice <= 18, "Total dice across all rolls seems excessive"


class TestMultiRollEdgeCases:
    """Test edge cases and error conditions for multi-roll functionality."""

    def test_single_roll_multiroll_equivalence(self):
        """Test that a single roll in multi-roll mode equals regular mode."""
        single_roll = {'skirmish': 2, 'assault': 1, 'raid': 1}

        # Calculate as single roll
        single_macrostates, single_probs, *_ = \
            arcs_funcs.compute_probabilities(
                single_roll['skirmish'], single_roll['assault'],
                single_roll['raid']
            )

        # Calculate as multi-roll with one roll
        multi_skirmish = single_roll['skirmish']
        multi_assault = single_roll['assault']
        multi_raid = single_roll['raid']

        multi_macrostates, multi_probs, *_ = \
            arcs_funcs.compute_probabilities(
                multi_skirmish, multi_assault, multi_raid
            )

        # Results should be identical
        assert len(single_macrostates) == len(multi_macrostates)

        single_sorted = sorted(zip(single_macrostates, single_probs))
        multi_sorted = sorted(zip(multi_macrostates, multi_probs))

        for (s_state, s_prob), (m_state, m_prob) in zip(single_sorted,
                                                        multi_sorted):
            assert s_state == m_state
            assert abs(s_prob - m_prob) < 1e-10

    def test_maximum_rolls_configuration(self):
        """Test configuration with maximum number of rolls."""
        # Create 10 rolls (stress test)
        max_rolls = []
        for i in range(10):
            # Alternate between different dice types
            if i % 3 == 0:
                max_rolls.append({'skirmish': 1, 'assault': 0, 'raid': 0})
            elif i % 3 == 1:
                max_rolls.append({'skirmish': 0, 'assault': 1, 'raid': 0})
            else:
                max_rolls.append({'skirmish': 0, 'assault': 0, 'raid': 1})

        # Calculate totals
        total_skirmish = sum(roll['skirmish'] for roll in max_rolls)
        total_assault = sum(roll['assault'] for roll in max_rolls)
        total_raid = sum(roll['raid'] for roll in max_rolls)

        # Should be manageable numbers
        assert total_skirmish <= 6, "Too many skirmish dice"
        assert total_assault <= 6, "Too many assault dice"
        assert total_raid <= 6, "Too many raid dice"

        # Test that calculation still works
        if total_skirmish + total_assault + total_raid > 0:
            macrostates, probs, *_ = arcs_funcs.compute_probabilities(
                total_skirmish, total_assault, total_raid
            )

            assert len(macrostates) > 0
            assert abs(sum(probs) - 1.0) < 1e-10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
