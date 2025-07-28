# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

"""
Test suite for enhanced probability calculator functionality.

This module tests the new min/max parameter support added to the
evaluate_truth_table and parse_label_for_probability functions.
"""

import pytest

from test_shared_utilities import (CONSTRAINT_TEST_PARAMS, BaseProbabilityTest,
                                   validate_constraint_evaluation,
                                   validate_probability_parsing)


class TestEvaluateTruthTable(BaseProbabilityTest):
    """Test the enhanced evaluate_truth_table function."""

    @pytest.mark.parametrize("constraint", CONSTRAINT_TEST_PARAMS)
    def test_single_constraints(self, constraint):
        """Test individual constraint types."""
        # Create test values that satisfy the constraint
        if 'min_hits' in constraint and 'max_hits' in constraint:
            # Range constraint - use middle value
            hits = (constraint['min_hits'] + constraint['max_hits']) // 2
            validate_constraint_evaluation(hits, 1, 1, 1, constraint, True)
            # Test boundaries
            validate_constraint_evaluation(
                constraint['min_hits'], 1, 1, 1, constraint, True)
            validate_constraint_evaluation(
                constraint['max_hits'], 1, 1, 1, constraint, True)
            # Test failures
            validate_constraint_evaluation(
                constraint['min_hits'] - 1, 1, 1, 1, constraint, False)
            validate_constraint_evaluation(
                constraint['max_hits'] + 1, 1, 1, 1, constraint, False)
        elif 'min_damage' in constraint and 'max_damage' in constraint:
            # Range constraint - use middle value
            damage = (constraint['min_damage'] + constraint['max_damage']) // 2
            validate_constraint_evaluation(1, damage, 1, 1, constraint, True)
            # Test boundaries
            validate_constraint_evaluation(
                1, constraint['min_damage'], 1, 1, constraint, True)
            validate_constraint_evaluation(
                1, constraint['max_damage'], 1, 1, constraint, True)
            # Test failures
            validate_constraint_evaluation(
                1, constraint['min_damage'] - 1, 1, 1, constraint, False)
            validate_constraint_evaluation(
                1, constraint['max_damage'] + 1, 1, 1, constraint, False)
        elif 'min_hits' in constraint:
            validate_constraint_evaluation(
                constraint['min_hits'], 1, 1, 1, constraint, True)
            validate_constraint_evaluation(
                constraint['min_hits'] - 1, 1, 1, 1, constraint, False)
        elif 'max_hits' in constraint:
            validate_constraint_evaluation(
                constraint['max_hits'], 1, 1, 1, constraint, True)
            validate_constraint_evaluation(
                constraint['max_hits'] + 1, 1, 1, 1, constraint, False)
        elif 'min_damage' in constraint:
            validate_constraint_evaluation(
                1, constraint['min_damage'], 1, 1, constraint, True)
            validate_constraint_evaluation(
                1, constraint['min_damage'] - 1, 1, 1, constraint, False)
        elif 'max_damage' in constraint:
            validate_constraint_evaluation(
                1, constraint['max_damage'], 1, 1, constraint, True)
            validate_constraint_evaluation(
                1, constraint['max_damage'] + 1, 1, 1, constraint, False)
        elif 'min_keys' in constraint:
            validate_constraint_evaluation(
                1, 1, 1, constraint['min_keys'], constraint, True)
            validate_constraint_evaluation(
                1, 1, 1, constraint['min_keys'] - 1, constraint, False)
        elif 'max_keys' in constraint:
            validate_constraint_evaluation(
                1, 1, 1, constraint['max_keys'], constraint, True)
            validate_constraint_evaluation(
                1, 1, 1, constraint['max_keys'] + 1, constraint, False)
        elif 'min_building_hits' in constraint:
            validate_constraint_evaluation(
                1, 1, constraint['min_building_hits'], 1, constraint, True)
            validate_constraint_evaluation(
                1, 1, constraint['min_building_hits'] - 1, 1, constraint,
                False)
        elif 'max_building_hits' in constraint:
            validate_constraint_evaluation(
                1, 1, constraint['max_building_hits'], 1, constraint, True)
            validate_constraint_evaluation(
                1, 1, constraint['max_building_hits'] + 1, 1, constraint,
                False)

    def test_range_constraints(self):
        """Test min/max range constraints together."""
        # Test hits range: 2-4 hits
        constraint = {'min_hits': 2, 'max_hits': 4}
        validate_constraint_evaluation(2, 0, 0, 0, constraint, True)
        validate_constraint_evaluation(3, 0, 0, 0, constraint, True)
        validate_constraint_evaluation(4, 0, 0, 0, constraint, True)
        validate_constraint_evaluation(1, 0, 0, 0, constraint, False)
        validate_constraint_evaluation(5, 0, 0, 0, constraint, False)

    def test_multiple_constraints(self):
        """Test multiple constraints working together."""
        constraint = {
            'min_hits': 2, 'min_damage': 1, 'max_keys': 2
        }

        # Should pass all constraints
        validate_constraint_evaluation(3, 2, 0, 1, constraint, True)

        # Should fail min_hits constraint
        validate_constraint_evaluation(1, 2, 0, 1, constraint, False)

        # Should fail max_keys constraint
        validate_constraint_evaluation(3, 2, 0, 3, constraint, False)


class TestParseLabelForProbability(BaseProbabilityTest):
    """Test the enhanced parse_label_for_probability function."""

    def test_basic_functionality(self):
        """Test basic probability calculation with constraints."""
        labels = ['2H1D', '1H', '3H']
        probs = [0.4, 0.3, 0.3]

        result = validate_probability_parsing(
            labels, probs, {'min_hits': 1},
            expected_conditions=['hitting at least 1 times']
        )
        assert "1.0000" in result

    def test_max_parameters(self):
        """Test max constraint parameters."""
        labels = ['1H', '2H', '3H', '4H']
        probs = [0.25, 0.25, 0.25, 0.25]

        result = validate_probability_parsing(
            labels, probs, {'max_hits': 2},
            expected_conditions=['hitting no more than 2 times']
        )
        assert "0.5000" in result

    def test_damage_range(self):
        """Test min and max damage constraints."""
        labels = ['1D', '2D', '3D', '4D']
        probs = [0.25, 0.25, 0.25, 0.25]

        result = validate_probability_parsing(
            labels, probs, {'min_damage': 2, 'max_damage': 3},
            expected_conditions=['taking at least 2 damage',
                                 'taking no more than 3 damage']
        )
        assert "0.5000" in result

    def test_keys_range(self):
        """Test min and max keys constraints."""
        labels = ['1K', '2K', '3K']
        probs = [0.4, 0.4, 0.2]

        result = validate_probability_parsing(
            labels, probs, {'min_keys': 1, 'max_keys': 2},
            expected_conditions=['getting at least 1 keys',
                                 'getting no more than 2 keys']
        )
        assert "0.8000" in result

    def test_complex_constraints(self):
        """Test multiple constraints working together."""
        labels = ['2H1D', 'H2D', '3HK', 'HDB']
        probs = [0.25, 0.25, 0.25, 0.25]

        result = validate_probability_parsing(
            labels, probs,
            {'min_hits': 1, 'max_hits': 3, 'min_damage': 0,
             'max_damage': 2, 'max_keys': 1}
        )

        # Should have multiple conditions joined with "and"
        assert "and" in result
        prob_value = float(result.split()[-1])
        assert 0 <= prob_value <= 1

    def test_no_matching_outcomes(self):
        """Test when no outcomes match the constraints."""
        labels = ['1H', '2H']
        probs = [0.5, 0.5]

        result = validate_probability_parsing(
            labels, probs, {'min_hits': 5}  # Impossible constraint
        )
        assert "0.0000" in result

    def test_all_outcomes_match(self):
        """Test when all outcomes match the constraints."""
        labels = ['1H', '2H', '3H']
        probs = [0.3, 0.4, 0.3]

        result = validate_probability_parsing(
            labels, probs, {'min_hits': 0}  # Very permissive
        )
        assert "1.0000" in result


class TestEnhancedFunctionality(BaseProbabilityTest):
    """Test enhanced functionality specific to new parameters."""

    @pytest.mark.parametrize("skirmish,assault,raid", [
        (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)
    ])
    def test_enhanced_parameters_integration(self, skirmish, assault, raid):
        """Test that enhanced parameters work with actual calculations."""
        macrostates, probs = self.validate_basic_calculation(
            skirmish, assault, raid
        )

        # Test various constraint combinations
        constraints = [
            {'min_hits': 1},
            {'max_damage': 1},
            {'min_hits': 1, 'max_damage': 2}
        ]

        for constraint in constraints:
            result = validate_probability_parsing(
                macrostates, probs, constraint
            )
            # Should return valid probability result
            assert "Probability of" in result

    def test_backward_compatibility(self):
        """Test that enhanced functions maintain backward compatibility."""
        labels = ['2H1D', '1H']
        probs = [0.6, 0.4]

        # Old-style call with explicit None values should work
        result = validate_probability_parsing(
            labels, probs,
            {'min_hits': 1, 'max_damage': 2, 'min_keys': None,
             'min_building_hits': None, 'max_building_hits': None}
        )
        assert "1.0000" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
