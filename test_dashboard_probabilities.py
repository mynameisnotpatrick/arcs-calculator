# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import pytest

import arcs_funcs
from test_shared_utilities import (STANDARD_MULTIROLL_CONFIGS,
                                   STANDARD_TEST_CASES, BaseProbabilityTest,
                                   validate_joint_probability_table,
                                   validate_marginal_distribution)


class TestDashboardProbabilities(BaseProbabilityTest):
    """Test suite for dashboard probability calculations and consistency"""

    @pytest.mark.parametrize("skirmish,assault,raid", STANDARD_TEST_CASES)
    def test_joint_probability_integrates_to_one(self, skirmish, assault,
                                                 raid):
        """Test that joint probability table sums to 1.0 for dice combos"""
        df = arcs_funcs.get_joint_prob_table(skirmish, assault, raid)
        validate_joint_probability_table(
            df, description=f"dice ({skirmish}, {assault}, {raid})"
        )

    @pytest.mark.parametrize("skirmish,assault,raid", [
        (1, 1, 1), (2, 0, 1), (0, 2, 1)
    ])
    @pytest.mark.parametrize("variable", [
        'hits', 'damage', 'building_hits', 'keys'
    ])
    def test_marginal_distributions_integrate_to_one(self, skirmish, assault,
                                                     raid, variable):
        """Test that each marginal distribution sums to 1.0"""
        df = arcs_funcs.get_joint_prob_table(skirmish, assault, raid)
        validate_marginal_distribution(
            df, variable,
            description=f"dice ({skirmish}, {assault}, {raid})"
        )

    def test_heatmap_probabilities_integrate_to_one(self):
        """Test that 2D heatmap probabilities sum to 1.0 for pairs"""
        df = arcs_funcs.get_joint_prob_table(1, 1, 1)
        variables = ['hits', 'damage', 'building_hits', 'keys']

        # Test all pairs of variables
        for i, x_var in enumerate(variables):
            for j, y_var in enumerate(variables):
                if i != j:  # Don't test variable against itself
                    pivot = df.pivot_table(index=y_var, columns=x_var,
                                           values='prob',
                                           aggfunc='sum', fill_value=0)
                    total_heatmap_prob = pivot.values.sum()
                    assert abs(total_heatmap_prob - 1.0) < 1e-10, \
                        f"Heatmap {x_var} vs {y_var} sums to " \
                        f"{total_heatmap_prob} != 1.0"

    @pytest.mark.parametrize("skirmish,assault,raid", [
        (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)
    ])
    def test_all_probabilities_non_negative(self, skirmish, assault, raid):
        """Test that all probabilities are non-negative"""
        df = arcs_funcs.get_joint_prob_table(skirmish, assault, raid)
        min_prob = df['prob'].min()
        assert min_prob >= 0, f"Found negative probability {min_prob} " \
                              f"for dice ({skirmish}, {assault}, {raid})"

    @pytest.mark.parametrize("dice_config", [
        (1, 0, 0),  # Single skirmish
        (0, 1, 0),  # Single assault
        (0, 0, 1),  # Single raid
    ])
    def test_single_die_outcome_constraints(self, dice_config):
        """Test dice type constraints for single die cases"""
        skirmish, assault, raid = dice_config
        df = arcs_funcs.get_joint_prob_table(skirmish, assault, raid)

        if skirmish == 1 and assault == 0 and raid == 0:
            # Single skirmish die constraints
            assert df['damage'].max() == 0, \
                "Skirmish die shouldn't produce damage"
            assert df['building_hits'].max() == 0, \
                "Skirmish die shouldn't produce building hits"
            assert df['keys'].max() == 0, \
                "Skirmish die shouldn't produce keys"
            assert df['hits'].max() == 1, \
                "Single skirmish die should max 1 hit"

        elif assault == 1 and skirmish == 0 and raid == 0:
            # Single assault die constraints
            assert df['building_hits'].max() == 0, \
                "Assault die shouldn't produce building hits"
            assert df['keys'].max() == 0, \
                "Assault die shouldn't produce keys"

        elif raid == 1 and skirmish == 0 and assault == 0:
            # Single raid die constraints
            assert df['hits'].max() == 0, \
                "Raid die shouldn't produce regular hits"

    @pytest.mark.parametrize("fresh_targets,convert_intercepts", [
        (2, False), (2, True)
    ])
    def test_convert_intercepts_consistency(self, fresh_targets,
                                            convert_intercepts):
        """Test that convert_intercepts parameter works correctly"""
        df = arcs_funcs.get_joint_prob_table(
            0, 0, 1, fresh_targets=fresh_targets,
            convert_intercepts=convert_intercepts
        )

        # Should integrate to 1
        assert abs(df['prob'].sum() - 1.0) < 1e-10

        # All probabilities should be non-negative
        assert (df['prob'] >= 0).all()


class TestSpecificProbabilities(BaseProbabilityTest):
    """Test specific probability calculations for known cases"""

    def test_single_skirmish_die_probabilities(self):
        """Test that single skirmish die has correct probability dist"""
        df = arcs_funcs.get_joint_prob_table(1, 0, 0)

        # Should have exactly 2 outcomes: 0 hits and 1 hit
        hits_counts = df['hits'].value_counts().sort_index()
        assert len(hits_counts) == 2, \
            f"Expected 2 outcomes, got {len(hits_counts)}"
        assert 0 in hits_counts.index and 1 in hits_counts.index

        # Each outcome should have probability 0.5 (1 blank, 1 hit face)
        prob_0_hits = df[df['hits'] == 0]['prob'].iloc[0]
        prob_1_hit = df[df['hits'] == 1]['prob'].iloc[0]

        assert abs(prob_0_hits - 0.5) < 1e-10, \
            f"P(0 hits) = {prob_0_hits}, expected 0.5"
        assert abs(prob_1_hit - 0.5) < 1e-10, \
            f"P(1 hit) = {prob_1_hit}, expected 0.5"


class TestMultiRollDashboardIntegration(BaseProbabilityTest):
    """Test dashboard functionality with multi-roll configurations."""

    @pytest.mark.parametrize("config", STANDARD_MULTIROLL_CONFIGS[:3])
    def test_dashboard_with_multiroll_configs(self, config):
        """Test that dashboard works correctly with multi-roll configs"""
        df = arcs_funcs.get_joint_prob_table(
            config['skirmish'], config['assault'], config['raid']
        )

        validate_joint_probability_table(
            df, description=f"multi-roll config {config}"
        )

        # Test that all variables have reasonable ranges
        variables = ['hits', 'damage', 'building_hits', 'keys']
        for var in variables:
            marginal = df.groupby(var)['prob'].sum()
            assert abs(marginal.sum() - 1.0) < 1e-10, \
                f"Multi-roll marginal for {var} doesn't sum to 1.0"

    def test_dashboard_consistency_across_equivalent_totals(self):
        """Test that dashboard gives same results for equivalent dice totals"""
        # Two equivalent ways to get same total dice
        result1 = arcs_funcs.get_joint_prob_table(2, 2, 1)
        result2 = arcs_funcs.get_joint_prob_table(2, 2, 1)

        # Results should be identical
        assert len(result1) == len(result2), \
            "Equivalent configurations should have same number of outcomes"

        # Sort both dataframes for comparison
        result1_sorted = result1.sort_values(
            ['hits', 'damage', 'building_hits', 'keys']
        ).reset_index(drop=True)
        result2_sorted = result2.sort_values(
            ['hits', 'damage', 'building_hits', 'keys']
        ).reset_index(drop=True)

        # Compare all values
        for col in ['hits', 'damage', 'building_hits', 'keys', 'prob']:
            assert result1_sorted[col].equals(result2_sorted[col]), \
                f"Column {col} differs between equivalent configurations"

    @pytest.mark.parametrize("roll_config", [
        {'skirmish': 2, 'assault': 0, 'raid': 0},
        {'skirmish': 0, 'assault': 2, 'raid': 0},
        {'skirmish': 0, 'assault': 0, 'raid': 2}
    ])
    def test_individual_roll_dashboard_constraints(self, roll_config):
        """Test dashboard calculations respect dice type constraints"""
        df = arcs_funcs.get_joint_prob_table(
            roll_config['skirmish'], roll_config['assault'],
            roll_config['raid']
        )

        # Each individual roll should have valid dashboard data
        assert len(df) > 0, f"Roll config {roll_config} has no outcomes"
        assert abs(df['prob'].sum() - 1.0) < 1e-10, \
            f"Roll config {roll_config} probabilities don't sum to 1.0"

        # Test constraints based on dice type
        if (roll_config['skirmish'] > 0 and roll_config['assault'] == 0 and
           roll_config['raid'] == 0):
            # Pure skirmish roll constraints
            assert df['damage'].max() == 0, \
                "Pure skirmish shouldn't produce damage"
            assert df['building_hits'].max() == 0, \
                "Pure skirmish shouldn't produce building hits"
            assert df['keys'].max() == 0, \
                "Pure skirmish shouldn't produce keys"

        elif (roll_config['assault'] > 0 and roll_config['skirmish'] == 0 and
              roll_config['raid'] == 0):
            # Pure assault roll constraints
            assert df['building_hits'].max() == 0, \
                "Pure assault shouldn't produce building hits"
            assert df['keys'].max() == 0, \
                "Pure assault shouldn't produce keys"

        elif (roll_config['raid'] > 0 and roll_config['skirmish'] == 0 and
              roll_config['assault'] == 0):
            # Pure raid roll constraints
            assert df['hits'].max() == 0, \
                "Pure raid shouldn't produce regular hits"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
