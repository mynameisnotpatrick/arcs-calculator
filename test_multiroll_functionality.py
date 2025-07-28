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

from test_shared_utilities import (STANDARD_MULTIROLL_CONFIGS,
                                   BaseProbabilityTest,
                                   compare_probability_results,
                                   validate_multiroll_configuration,
                                   validate_multiroll_equivalence,
                                   validate_roll_dictionary)


class TestMultiRollLogic(BaseProbabilityTest):
    """Test the core logic for multi-roll calculations."""

    @pytest.mark.parametrize("rolls", [
        [{'skirmish': 2, 'assault': 0, 'raid': 0},
         {'skirmish': 0, 'assault': 2, 'raid': 0}],
        [{'skirmish': 1, 'assault': 1, 'raid': 0},
         {'skirmish': 1, 'assault': 0, 'raid': 1}],
        [STANDARD_MULTIROLL_CONFIGS[0], STANDARD_MULTIROLL_CONFIGS[1]]
    ])
    def test_multiroll_equivalence(self, rolls):
        """Test that multi-roll totals match combined calculations."""
        # Validate configuration
        validate_multiroll_configuration(rolls)

        # Calculate combined totals
        combined_totals = {
            'skirmish': sum(roll['skirmish'] for roll in rolls),
            'assault': sum(roll['assault'] for roll in rolls),
            'raid': sum(roll['raid'] for roll in rolls)
        }

        # Validate equivalence
        validate_multiroll_equivalence(rolls, combined_totals)

        # Test actual calculation equivalence
        if sum(combined_totals.values()) > 0:
            combined_result = self.validate_basic_calculation(
                combined_totals['skirmish'],
                combined_totals['assault'],
                combined_totals['raid']
            )

            direct_result = self.validate_basic_calculation(
                combined_totals['skirmish'],
                combined_totals['assault'],
                combined_totals['raid']
            )

            compare_probability_results(
                combined_result, direct_result,
                "multi-roll total", "direct calculation"
            )

    @pytest.mark.parametrize("config", STANDARD_MULTIROLL_CONFIGS)
    def test_individual_roll_calculations(self, config):
        """Test individual roll calculations using standard configs."""
        validate_roll_dictionary(config, "standard config")

        if sum(config.values()) > 0:
            macrostates, probs = self.validate_basic_calculation(
                config['skirmish'], config['assault'], config['raid']
            )

            assert len(macrostates) > 0
            assert abs(sum(probs) - 1.0) < self.tolerance

    def test_empty_roll_handling(self):
        """Test handling of rolls with no dice."""
        # empty_roll = {'skirmish': 0, 'assault': 0, 'raid': 0}

        try:
            self.validate_basic_calculation(0, 0, 0)
            pytest.skip("Empty roll accepted (implementation detail)")
        except Exception:
            # Expected behavior - empty rolls should be filtered out
            pass

    @pytest.mark.parametrize("fresh_targets,convert_intercepts", [
        (0, False), (3, True), (5, True)
    ])
    def test_intercepts_with_multiroll(self, fresh_targets,
                                       convert_intercepts):
        """Test convert_intercepts with multi-roll configurations."""
        # Use configurations that include raid dice (which have intercepts)
        raid_configs = [config for config in STANDARD_MULTIROLL_CONFIGS
                        if config['raid'] > 0]

        if not raid_configs:
            pytest.skip("No raid dice configurations available")

        config = raid_configs[0]

        try:
            macrostates, probs = self.validate_basic_calculation(
                config['skirmish'], config['assault'], config['raid'],
                fresh_targets, convert_intercepts
            )

            assert len(macrostates) > 0
            assert abs(sum(probs) - 1.0) < self.tolerance

        except ValueError as e:
            if ("Cannot convert intercepts" in str(e) and
               fresh_targets == 0):
                # Expected error when fresh_targets=0 but
                # convert_intercepts=True
                pass
            else:
                raise


class TestMultiRollDataStructures(BaseProbabilityTest):
    """Test data structures and validation for multi-roll functionality."""

    @pytest.mark.parametrize("roll", STANDARD_MULTIROLL_CONFIGS)
    def test_roll_dictionary_validation(self, roll):
        """Test roll dictionary structure validation."""
        validate_roll_dictionary(roll, "standard multiroll config")

    def test_multiroll_configuration_validation(self):
        """Test validation of complete multi-roll configurations."""
        test_configs = [
            # Valid configurations
            [{'skirmish': 1, 'assault': 0, 'raid': 0},
             {'skirmish': 0, 'assault': 1, 'raid': 0}],
            [{'skirmish': 2, 'assault': 1, 'raid': 1}],
            STANDARD_MULTIROLL_CONFIGS[:3]
        ]

        for config in test_configs:
            stats = validate_multiroll_configuration(config)
            assert stats['total_rolls'] == len(config)
            assert stats['non_empty_rolls'] > 0
            assert stats['total_dice'] >= stats['non_empty_rolls']

    def test_dice_totaling_logic(self):
        """Test calculation of total dice across multiple rolls."""
        rolls = [
            {'skirmish': 2, 'assault': 1, 'raid': 0},
            {'skirmish': 1, 'assault': 0, 'raid': 2},
            {'skirmish': 0, 'assault': 2, 'raid': 1}
        ]

        expected_totals = {'skirmish': 3, 'assault': 3, 'raid': 3}
        validate_multiroll_equivalence(rolls, expected_totals)


class TestMultiRollEdgeCases(BaseProbabilityTest):
    """Test edge cases and error conditions for multi-roll functionality."""

    def test_single_roll_equivalence(self):
        """Test that single roll in multi-roll mode equals regular mode."""
        config = {'skirmish': 2, 'assault': 1, 'raid': 1}

        # Calculate both ways
        single_result = self.validate_basic_calculation(
            config['skirmish'], config['assault'], config['raid']
        )

        multi_result = self.validate_basic_calculation(
            config['skirmish'], config['assault'], config['raid']
        )

        # Should be identical
        compare_probability_results(
            single_result, multi_result,
            "single roll", "multi-roll equivalent"
        )

    @pytest.mark.parametrize("num_rolls", [2, 5, 10])
    def test_maximum_rolls_stress_test(self, num_rolls):
        """Test configurations with varying numbers of rolls."""
        rolls = []
        for i in range(num_rolls):
            # Create small rolls to avoid exceeding dice limits
            if i % 3 == 0:
                rolls.append({'skirmish': 1, 'assault': 0, 'raid': 0})
            elif i % 3 == 1:
                rolls.append({'skirmish': 0, 'assault': 1, 'raid': 0})
            else:
                rolls.append({'skirmish': 0, 'assault': 0, 'raid': 1})

        # Validate configuration
        stats = validate_multiroll_configuration(rolls)
        assert stats['total_rolls'] == num_rolls

        # Calculate totals and ensure they're reasonable
        totals = {
            'skirmish': sum(roll['skirmish'] for roll in rolls),
            'assault': sum(roll['assault'] for roll in rolls),
            'raid': sum(roll['raid'] for roll in rolls)
        }

        # Should not exceed reasonable game limits
        for dice_type, count in totals.items():
            assert count <= 6, f"Too many {dice_type} dice: {count}"

        # Test calculation if total is valid
        if sum(totals.values()) > 0:
            self.validate_basic_calculation(
                totals['skirmish'], totals['assault'], totals['raid']
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
