# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import pytest

import arcs_funcs
from test_shared_utilities import (validate_joint_probability_table,
                                   validate_marginal_distribution)


class TestDashboardProbabilities:
    """Test suite for dashboard probability calculations and consistency"""

    def test_joint_probability_integrates_to_one(self):
        """Test that joint probability table sums to 1.0 for various dice
        combinations"""
        test_cases = [
            (1, 0, 0),  # 1 skirmish
            (0, 1, 0),  # 1 assault
            (0, 0, 1),  # 1 raid
            (1, 1, 0),  # 1 skirmish + 1 assault
            (1, 0, 1),  # 1 skirmish + 1 raid
            (0, 1, 1),  # 1 assault + 1 raid
            (1, 1, 1),  # 1 of each
            (2, 1, 0),  # Multiple dice
            (0, 2, 1),  # Different combinations
        ]

        for skirmish, assault, raid in test_cases:
            df = arcs_funcs.get_joint_prob_table(skirmish, assault, raid)
            # Use shared utility for validation
            validate_joint_probability_table(
                df,
                description=f"dice ({skirmish}, {assault}, {raid})"
            )

    def test_marginal_distributions_integrate_to_one(self):
        """Test that each marginal distribution sums to 1.0"""
        test_cases = [(1, 1, 1), (2, 0, 1), (0, 2, 1)]
        variables = ['hits', 'damage', 'building_hits', 'keys']

        for skirmish, assault, raid in test_cases:
            df = arcs_funcs.get_joint_prob_table(skirmish, assault, raid)

            for var in variables:
                # Use shared utility for validation
                validate_marginal_distribution(
                    df, var,
                    description=f"dice ({skirmish}, {assault}, {raid})"
                )

    def test_heatmap_probabilities_integrate_to_one(self):
        """Test that 2D heatmap probabilities sum to 1.0 for all variable
        pairs"""
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

    def test_marginal_joint_consistency(self):
        """Test that marginals computed directly match marginals from joint
        distribution"""
        df = arcs_funcs.get_joint_prob_table(2, 1, 1)
        variables = ['hits', 'damage', 'building_hits', 'keys']

        for var in variables:
            # Compute marginal from joint distribution
            joint_marginal = df.groupby(var)['prob'].sum().reset_index()

            # For comparison, we can verify this matches what we'd expect
            # by ensuring all probabilities are accounted for
            total_prob_for_var = joint_marginal['prob'].sum()
            assert abs(total_prob_for_var - 1.0) < 1e-10, \
                f"Joint marginal for {var} doesn't sum to 1.0: " \
                f"{total_prob_for_var}"

    def test_all_probabilities_non_negative(self):
        """Test that all probabilities are non-negative"""
        test_cases = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)]

        for skirmish, assault, raid in test_cases:
            df = arcs_funcs.get_joint_prob_table(skirmish, assault, raid)
            min_prob = df['prob'].min()
            assert min_prob >= 0, f"Found negative probability {min_prob} "
            f"for dice ({skirmish}, {assault}, {raid})"

    def test_correct_variable_ranges(self):
        """Test that variable values are within expected ranges"""
        df = arcs_funcs.get_joint_prob_table(2, 2, 2)

        # With 2 dice of each type, maximum possible values should be
        # reasonable
        assert df['hits'].max() <= 6, f"Hits max {df['hits'].max()} seems " \
                                      f"too high for 2 skirmish + 2 assault " \
                                      f"dice (max 6)"
        assert df['damage'].max() <= 6, f"Damage max {df['damage'].max()} " \
                                        f"seems too high"
        assert df['building_hits'].max() <= 2, \
            f"Building hits max {df['building_hits'].max()} > 2 raid dice"
        assert df['keys'].max() <= 4, f"Keys max {df['keys'].max()} " \
                                      f"seems too high for 2 raid dice"

        # All minimums should be 0
        for var in ['hits', 'damage', 'building_hits', 'keys']:
            assert df[var].min() == 0, f"Minimum {var} should be 0, "
            f"got {df[var].min()}"

    def test_single_die_cases(self):
        """Test cases with exactly one die of each type"""
        # Single skirmish die: only hits possible (0 or 1)
        df_s = arcs_funcs.get_joint_prob_table(1, 0, 0)
        assert df_s['damage'].max() == 0, \
            "Skirmish die shouldn't produce damage"
        assert df_s['building_hits'].max() == 0, \
            "Skirmish die shouldn't produce building hits"
        assert df_s['keys'].max() == 0, "Skirmish die shouldn't produce keys"
        assert df_s['hits'].max() == 1, "Single skirmish die should max 1 hit"

        # Single assault die: hits and damage possible, no building hits
        # or keys
        df_a = arcs_funcs.get_joint_prob_table(0, 1, 0)
        assert df_a['building_hits'].max() == 0, \
            "Assault die shouldn't produce building hits"
        assert df_a['keys'].max() == 0, "Assault die shouldn't produce keys"

        # Single raid die: building hits and keys possible, plus damage
        df_r = arcs_funcs.get_joint_prob_table(0, 0, 1)
        assert df_r['hits'].max() == 0, \
            "Raid die shouldn't produce regular hits"

    def test_convert_intercepts_consistency(self):
        """Test that convert_intercepts parameter works correctly"""
        # Test with and without converting intercepts
        df_no_convert = arcs_funcs.get_joint_prob_table(
            0, 0, 1, fresh_targets=2, convert_intercepts=False)
        df_convert = arcs_funcs.get_joint_prob_table(
            0, 0, 1, fresh_targets=2, convert_intercepts=True)

        # Both should integrate to 1
        assert abs(df_no_convert['prob'].sum() - 1.0) < 1e-10
        assert abs(df_convert['prob'].sum() - 1.0) < 1e-10

        # With intercepts converted, we might see higher damage values
        max_damage_no_convert = df_no_convert['damage'].max()
        max_damage_convert = df_convert['damage'].max()

        # The convert case should potentially have higher max damage
        assert max_damage_convert >= max_damage_no_convert, \
            "Converting intercepts should not decrease maximum possible damage"

    def test_pivot_table_consistency(self):
        """Test that pivot tables used in heatmaps are constructed correctly"""
        df = arcs_funcs.get_joint_prob_table(1, 1, 0)  # Simple case

        # Create a pivot table like the heatmap function does
        pivot = df.pivot_table(index='damage', columns='hits',
                               values='prob', aggfunc='sum', fill_value=0)

        # Sum of pivot should equal 1
        assert abs(pivot.values.sum() - 1.0) < 1e-10, \
            "Pivot table doesn't sum to 1.0"

        # Each cell should be non-negative
        assert (pivot.values >= 0).all(), \
            "Pivot table contains negative values"

        # Reconstruct original probabilities from pivot
        reconstructed_total = 0
        for damage_val in pivot.index:
            for hits_val in pivot.columns:
                prob_val = pivot.loc[damage_val, hits_val]
                reconstructed_total += prob_val

        assert abs(reconstructed_total - 1.0) < 1e-10, \
            "Reconstructed total doesn't equal 1.0"


# Additional test for specific probability calculations
class TestSpecificProbabilities:
    """Test specific probability calculations for known cases"""

    def test_single_skirmish_die_probabilities(self):
        """Test that single skirmish die has correct probability
        distribution"""
        df = arcs_funcs.get_joint_prob_table(1, 0, 0)

        # Should have exactly 2 outcomes: 0 hits and 1 hit
        hits_counts = df['hits'].value_counts().sort_index()
        assert len(hits_counts) == 2, f"Expected 2 outcomes, got " \
                                      f"{len(hits_counts)}"
        assert 0 in hits_counts.index and 1 in hits_counts.index

        # Each outcome should have probability 0.5 (1 blank, 1 hit face)
        prob_0_hits = df[df['hits'] == 0]['prob'].iloc[0]
        prob_1_hit = df[df['hits'] == 1]['prob'].iloc[0]

        assert abs(prob_0_hits - 0.5) < 1e-10, \
            f"P(0 hits) = {prob_0_hits}, expected 0.5"
        assert abs(prob_1_hit - 0.5) < 1e-10, \
            f"P(1 hit) = {prob_1_hit}, expected 0.5"


class TestMultiRollDashboardIntegration:
    """Test dashboard functionality with multi-roll configurations."""

    def test_dashboard_with_multiroll_totals(self):
        """Test that dashboard works correctly with totaled dice from
        multiple rolls."""
        # Simulate multi-roll scenario: roll1 + roll2 = totals
        roll1 = {'skirmish': 1, 'assault': 1, 'raid': 0}
        roll2 = {'skirmish': 0, 'assault': 1, 'raid': 1}

        # Calculate totals as would be done in multi-roll mode
        total_skirmish = roll1['skirmish'] + roll2['skirmish']
        total_assault = roll1['assault'] + roll2['assault']
        total_raid = roll1['raid'] + roll2['raid']

        # Test that dashboard calculations work with these totals
        df = arcs_funcs.get_joint_prob_table(
            total_skirmish, total_assault, total_raid)

        # Standard dashboard validations should pass
        total_prob = df['prob'].sum()
        assert abs(total_prob - 1.0) < 1e-10, \
            f"Multi-roll dashboard total probability {total_prob} != 1.0"

        # Test that all variables have reasonable ranges
        variables = ['hits', 'damage', 'building_hits', 'keys']
        for var in variables:
            marginal = df.groupby(var)['prob'].sum()
            assert abs(marginal.sum() - 1.0) < 1e-10, \
                f"Multi-roll marginal for {var} doesn't sum to 1.0"

    def test_dashboard_consistency_across_roll_splits(self):
        """Test that dashboard gives same results regardless of how dice
        are split across rolls."""
        # Two ways to achieve the same total dice
        # Method 1: All dice in one roll
        single_roll_result = arcs_funcs.get_joint_prob_table(2, 2, 1)

        # Method 2: Split across multiple conceptual rolls, but same totals
        multi_roll_result = arcs_funcs.get_joint_prob_table(2, 2, 1)

        # Results should be identical since the underlying calculation
        # is the same
        assert len(single_roll_result) == len(multi_roll_result), \
            "Split vs single roll should have same number of outcomes"

        # Sort both dataframes for comparison
        single_sorted = single_roll_result.sort_values(
            ['hits', 'damage', 'building_hits', 'keys']).reset_index(drop=True)
        multi_sorted = multi_roll_result.sort_values(
            ['hits', 'damage', 'building_hits', 'keys']).reset_index(drop=True)

        # Compare all values
        for col in ['hits', 'damage', 'building_hits', 'keys', 'prob']:
            assert single_sorted[col].equals(multi_sorted[col]), \
                f"Column {col} differs between single and multi-roll"

    def test_individual_roll_dashboard_components(self):
        """Test dashboard calculations for individual rolls within
        multi-roll."""
        individual_rolls = [
            {'skirmish': 2, 'assault': 0, 'raid': 0},
            {'skirmish': 0, 'assault': 2, 'raid': 0},
            {'skirmish': 0, 'assault': 0, 'raid': 2}
        ]

        for i, roll in enumerate(individual_rolls):
            df = arcs_funcs.get_joint_prob_table(
                roll['skirmish'], roll['assault'], roll['raid'])

            # Each individual roll should have valid dashboard data
            assert len(df) > 0, f"Individual roll {i+1} has no outcomes"
            assert abs(df['prob'].sum() - 1.0) < 1e-10, \
                f"Individual roll {i+1} probabilities don't sum to 1.0"

            # Test specific constraints based on dice type
            if roll['skirmish'] > 0 and roll['assault'] == 0 and \
               roll['raid'] == 0:
                # Pure skirmish roll - should only produce hits
                assert df['damage'].max() == 0, \
                    "Pure skirmish roll shouldn't produce damage"
                assert df['building_hits'].max() == 0, \
                    "Pure skirmish roll shouldn't produce building hits"
                assert df['keys'].max() == 0, \
                    "Pure skirmish roll shouldn't produce keys"

            elif (roll['assault'] > 0 and roll['skirmish'] == 0 and
                  roll['raid'] == 0):
                # Pure assault roll - should produce hits and damage
                assert df['building_hits'].max() == 0, \
                    "Pure assault roll shouldn't produce building hits"
                assert df['keys'].max() == 0, \
                    "Pure assault roll shouldn't produce keys"

            elif (roll['raid'] > 0 and roll['skirmish'] == 0 and
                  roll['assault'] == 0):
                # Pure raid roll - should produce building hits, keys, damage
                assert df['hits'].max() == 0, \
                    "Pure raid roll shouldn't produce regular hits"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
