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

import arcs_funcs


class TestEvaluateTruthTable:
    """Test the enhanced evaluate_truth_table function."""

    def test_no_constraints_always_true(self):
        """Test that no constraints means all outcomes are valid."""
        # All parameters None should always return True
        assert arcs_funcs.evaluate_truth_table(0, 0, 0, 0) is True
        assert arcs_funcs.evaluate_truth_table(5, 3, 2, 1) is True
        assert arcs_funcs.evaluate_truth_table(10, 10, 10, 10) is True

    def test_min_constraints(self):
        """Test minimum constraint validation."""
        # Test min_hits
        assert arcs_funcs.evaluate_truth_table(
            2, 0, 0, 0, min_hits=2) is True
        assert arcs_funcs.evaluate_truth_table(
            1, 0, 0, 0, min_hits=2) is False

        # Test min_damage
        assert arcs_funcs.evaluate_truth_table(
            0, 3, 0, 0, min_damage=3) is True
        assert arcs_funcs.evaluate_truth_table(
            0, 2, 0, 0, min_damage=3) is False

        # Test min_keys
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 0, 2, min_keys=2) is True
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 0, 1, min_keys=2) is False

        # Test min_building_hits
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 3, 0, min_building_hits=3) is True
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 2, 0, min_building_hits=3) is False

    def test_max_constraints(self):
        """Test maximum constraint validation."""
        # Test max_hits
        assert arcs_funcs.evaluate_truth_table(
            2, 0, 0, 0, max_hits=2) is True
        assert arcs_funcs.evaluate_truth_table(
            3, 0, 0, 0, max_hits=2) is False

        # Test max_damage
        assert arcs_funcs.evaluate_truth_table(
            0, 2, 0, 0, max_damage=2) is True
        assert arcs_funcs.evaluate_truth_table(
            0, 3, 0, 0, max_damage=2) is False

        # Test max_keys
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 0, 2, max_keys=2) is True
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 0, 3, max_keys=2) is False

        # Test max_building_hits
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 2, 0, max_building_hits=2) is True
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 3, 0, max_building_hits=2) is False

    def test_range_constraints(self):
        """Test min/max range constraints together."""
        # Test hits range: 2-4 hits
        assert arcs_funcs.evaluate_truth_table(
            2, 0, 0, 0, min_hits=2, max_hits=4) is True
        assert arcs_funcs.evaluate_truth_table(
            3, 0, 0, 0, min_hits=2, max_hits=4) is True
        assert arcs_funcs.evaluate_truth_table(
            4, 0, 0, 0, min_hits=2, max_hits=4) is True
        assert arcs_funcs.evaluate_truth_table(
            1, 0, 0, 0, min_hits=2, max_hits=4) is False
        assert arcs_funcs.evaluate_truth_table(
            5, 0, 0, 0, min_hits=2, max_hits=4) is False

        # Test damage range: 1-3 damage
        assert arcs_funcs.evaluate_truth_table(
            0, 1, 0, 0, min_damage=1, max_damage=3) is True
        assert arcs_funcs.evaluate_truth_table(
            0, 0, 0, 0, min_damage=1, max_damage=3) is False
        assert arcs_funcs.evaluate_truth_table(
            0, 4, 0, 0, min_damage=1, max_damage=3) is False

    def test_multiple_constraints(self):
        """Test multiple constraints working together."""
        # Must have 2+ hits AND 1+ damage AND 0-2 keys
        result = arcs_funcs.evaluate_truth_table(
            3, 2, 0, 1, min_hits=2, min_damage=1, max_keys=2)
        assert result is True

        # Fails min_hits constraint
        result = arcs_funcs.evaluate_truth_table(
            1, 2, 0, 1, min_hits=2, min_damage=1, max_keys=2)
        assert result is False

        # Fails max_keys constraint
        result = arcs_funcs.evaluate_truth_table(
            3, 2, 0, 3, min_hits=2, min_damage=1, max_keys=2)
        assert result is False

    def test_backward_compatibility(self):
        """Test that old function calls still work."""
        # Named parameters (should work)
        assert arcs_funcs.evaluate_truth_table(
            2, 1, 1, 1, min_hits=2, max_damage=2, min_keys=1,
            min_building_hits=1, max_building_hits=2) is True
        # Test case that should fail max_damage constraint
        assert arcs_funcs.evaluate_truth_table(
            2, 3, 1, 1, min_hits=2, max_damage=2, min_keys=1,
            min_building_hits=1, max_building_hits=2) is False


class TestParseLabelForProbability:
    """Test the enhanced parse_label_for_probability function."""

    def test_basic_functionality(self):
        """Test basic probability calculation."""
        labels = ['2H1D', '1H', '3H']
        probs = [0.4, 0.3, 0.3]

        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_hits=1)
        # Should include all: '2H1D' (2 hits), '1H' (1 hit), '3H' = 1.0
        assert "1.0000" in result
        assert "hitting at least 1 times" in result

    def test_new_max_parameters(self):
        """Test the new max_hits parameter."""
        labels = ['1H', '2H', '3H', '4H']
        probs = [0.25, 0.25, 0.25, 0.25]

        result = arcs_funcs.parse_label_for_probability(
            labels, probs, max_hits=2)

        # Should include '1H' (1 hit) and '2H' (2 hits) = 0.25 + 0.25 = 0.5
        assert "0.5000" in result
        assert "hitting no more than 2 times" in result

    def test_damage_range(self):
        """Test min and max damage constraints."""
        labels = ['1D', '2D', '3D', '4D']
        probs = [0.25, 0.25, 0.25, 0.25]

        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_damage=2, max_damage=3)

        # Should include '2D' and '3D' = 0.25 + 0.25 = 0.5
        assert "0.5000" in result
        assert "taking at least 2 damage" in result
        assert "taking no more than 3 damage" in result

    def test_keys_range(self):
        """Test min and max keys constraints."""
        labels = ['1K', '2K', '3K']
        probs = [0.4, 0.4, 0.2]

        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_keys=1, max_keys=2)

        # Should include '1K' (1 key) and '2K' (2 keys) = 0.4 + 0.4 = 0.8
        assert "0.8000" in result
        assert "getting at least 1 keys" in result
        assert "getting no more than 2 keys" in result

    def test_complex_constraints(self):
        """Test multiple constraints working together."""
        labels = ['2H1D', 'H2D', '3HK', 'HDB']
        probs = [0.25, 0.25, 0.25, 0.25]

        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_hits=1, max_hits=3,
            min_damage=0, max_damage=2, max_keys=1)

        # Should include outcomes that meet all constraints
        assert "and" in result  # Multiple conditions joined
        prob_value = float(result.split()[-1])  # Extract final probability
        assert 0 <= prob_value <= 1

    def test_no_matching_outcomes(self):
        """Test when no outcomes match the constraints."""
        labels = ['H', '2H']
        probs = [0.5, 0.5]

        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_hits=5)  # Impossible constraint

        assert "0.0000" in result

    def test_all_outcomes_match(self):
        """Test when all outcomes match the constraints."""
        labels = ['H', '2H', '3H']
        probs = [0.3, 0.4, 0.3]

        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_hits=0)  # Very permissive constraint

        assert "1.0000" in result

    def test_backward_compatibility(self):
        """Test that old function calls still work."""
        labels = ['2H1D', '1H']  # Use proper label format
        probs = [0.6, 0.4]

        # Old style call
        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_hits=1, max_damage=2, min_keys=None,
            min_building_hits=None, max_building_hits=None)
        # Both should match: '2H1D' (2 hits, 1 damage) and '1H' (1 hit)
        assert "1.0000" in result


class TestParameterValidation:
    """Test parameter validation and edge cases."""

    def test_empty_inputs(self):
        """Test behavior with empty labels/probabilities."""
        result = arcs_funcs.parse_label_for_probability(
            [], [], min_hits=1)
        assert "0.0000" in result

    def test_probability_distribution_validity(self):
        """Test that function doesn't break probability math."""
        labels = ['1H', '2H', '3H', '1D', '2D']
        probs = [0.2, 0.2, 0.2, 0.2, 0.2]
        # Test that probabilities sum correctly for any constraint
        result = arcs_funcs.parse_label_for_probability(
            labels, probs, min_hits=1, max_hits=10)
        prob_value = float(result.split()[-1])
        # Should match '1H', '2H', '3H' = 0.2 + 0.2 + 0.2 = 0.6
        assert abs(prob_value - 0.6) < 1e-10

    def test_single_constraint_types(self):
        """Test each constraint type individually."""
        labels = ['2H1D1B1K']
        probs = [1.0]
        # Test each constraint type individually
        constraints = [
            {'min_hits': 2},
            {'max_hits': 2},
            {'min_damage': 1},
            {'max_damage': 1},
            {'min_keys': 1},
            {'max_keys': 1},
            {'min_building_hits': 1},
            {'max_building_hits': 1}
        ]
        for constraint in constraints:
            result = arcs_funcs.parse_label_for_probability(
                labels, probs, **constraint)
            # Should match the single outcome
            assert "1.0000" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
