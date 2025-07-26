# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import argparse
import json
import warnings

from dateutil.parser import UnknownTimezoneWarning

import arcs_funcs

warnings.filterwarnings("ignore", category=UnknownTimezoneWarning)


def main():
    parser = argparse.ArgumentParser(description='Roll arcs dice')
    parser.add_argument('--assault-dice', '-a', default=0, type=int,
                        help='Number of assault dice to roll (max 6)')
    parser.add_argument('--raid-dice', '-r', default=0, type=int,
                        help='Number of raid dice to roll (max 6)')
    parser.add_argument('--skirmish-dice', '-s', default=0, type=int,
                        help='Number of skirmish dice to roll (max 6)')
    parser.add_argument('--fresh-targets', '-f', default=0, type=int,
                        help='Number of fresh loyal ships you are attacking '
                             '(makes no difference unless '
                             '--convert-intercepts '
                             'is True)')
    parser.add_argument('--convert-intercepts', '-c', action='store_true',
                        help='Convert intercepts to hits (default: False)')
    parser.add_argument('--min-hits', type=int,
                        help='Compute probability of getting a minimum of '
                             'this many hits.')
    parser.add_argument('--max-damage', type=int,
                        help='Compute probability of taking a maximum of '
                             'this much damage.')
    parser.add_argument('--min-keys', type=int,
                        help='Compute probability of getting a minimum of '
                             'this many keys.')
    parser.add_argument('--min-building-hits', type=int,
                        help='Compute probability of dealing a minimum of '
                             'this many building hits.')
    parser.add_argument('--max-building-hits', type=int,
                        help='Compute probability of dealing a maximum of '
                             'this many building hits.')
    parser.add_argument('--show-full-plot', action='store_true',
                        help='Dont truncate plot to top 50 most probable '
                             'outcomes. (default: False)')
    parser.add_argument('--truncate-length', default=100, type=int,
                        help='Truncate plot so this many of the most '
                             'probable results will be shown (default: 100). '
                             'Will be ignored if --show-full-plot is '
                             'provided.')
    parser.add_argument('--generate-table', type=str,
                        help='Generate json of macrostates and associated '
                             'number of microstates and save as this name.')
    parser.add_argument('--theme', choices=['light', 'dark'], default='light',
                        help='Theme for plots (default: light)')
    parser.add_argument('--output-filename', '-o',
                        default='arcs_probability.png', help='Output filename'
                        ' for probability plot (default: '
                        'arcs_probability.png)')
    parser.add_argument('--generate-dashboard', action='store_true',
                        help='Generate dashboard plots (heatmap and '
                             'marginals)')
    parser.add_argument('--dashboard-x',
                        choices=['hits', 'damage', 'building_hits', 'keys'],
                        default='hits',
                        help='X-axis variable for heatmap (default: hits)')
    parser.add_argument('--dashboard-y',
                        choices=['hits', 'damage', 'building_hits', 'keys'],
                        default='damage',
                        help='Y-axis variable for heatmap (default: damage)')
    parser.add_argument('--cumulative', action='store_true',
                        help='Generate cumulative plots (default: False)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output and timing information')
    args = parser.parse_args()

    if (args.max_damage is not None and
            args.convert_intercepts is False):
        raise ValueError('Cannot *accurately* compute --max-damage without '
                         'converting intercepts')

    # Validate dice counts
    if args.skirmish_dice + args.assault_dice + args.raid_dice == 0:
        print("Error: Please specify at least one die to roll")
        return 1

    if args.verbose:
        print(f"Computing probabilities for {args.skirmish_dice} skirmish, "
              f"{args.assault_dice} assault, {args.raid_dice} raid dice...")
        if args.convert_intercepts:
            print(f"Converting intercepts to damage with {args.fresh_targets} "
                  "fresh targets")

    # Compute probabilities
    macrostates, probs, parse_time, coefficient_time, loop_count = \
        arcs_funcs.compute_probabilities(
            args.skirmish_dice, args.assault_dice, args.raid_dice,
            args.fresh_targets, args.convert_intercepts)

    if args.verbose:
        print("Calculation completed:")
        print(f"  Parse time: {parse_time:.2f}s")
        print(f"  Coefficient time: {coefficient_time:.2f}s")
        print(f"  Loop iterations: {loop_count:,}")
        print(f"  Total unique outcomes: {len(macrostates)}")

    # Generate table output if requested
    if args.generate_table is not None:
        if args.verbose:
            print(f"Generating table: {args.generate_table}")
        with open(args.generate_table, 'w') as fo:
            json.dump([[macrostate, prob] for macrostate, prob in
                       zip(macrostates, probs)], fo, indent=2)

    # Calculate custom probabilities
    if (args.min_hits is not None or args.max_damage is not None or
            args.min_keys is not None or args.min_building_hits is not None or
            args.max_building_hits is not None):
        result = arcs_funcs.parse_label_for_probability(
            macrostates, probs, args.min_hits, args.max_damage,
            args.min_keys, args.min_building_hits, args.max_building_hits)
        print(result)

    # Generate main probability plot
    if args.verbose:
        print(f"Generating probability plot: {args.output_filename}")

    arcs_funcs.plot_most_likely_states(
        macrostates, probs, args.skirmish_dice, args.assault_dice,
        args.raid_dice, args.fresh_targets, args.output_filename,
        args.convert_intercepts, args.truncate_length, args.show_full_plot,
        args.theme)

    # Generate dashboard plots if requested
    if args.generate_dashboard:
        if args.verbose:
            print("Generating dashboard plots...")

        # Get joint probability table for dashboard
        df = arcs_funcs.get_joint_prob_table(
            args.skirmish_dice, args.assault_dice, args.raid_dice,
            args.fresh_targets, args.convert_intercepts
        )

        # Generate heatmap
        heatmap_filename = args.output_filename.replace('.png',
                                                        '_heatmap.png')
        if args.verbose:
            print(f"  Generating heatmap: {heatmap_filename}")

        arcs_funcs.plot_heatmap(
            df, args.dashboard_x, args.dashboard_y, heatmap_filename,
            args.theme, cumulative=args.cumulative
        )

        # Generate marginal plots
        variables = ['hits', 'damage', 'building_hits', 'keys']
        for var in variables:
            marginal = df.groupby(var)['prob'].sum().reset_index()
            if len(marginal) > 1:  # Only plot if there are multiple values
                marginal_filename = args.output_filename.replace(
                    '.png', f'_marginal_{var}.png')
                if args.verbose:
                    print(f"  Generating marginal plot: {marginal_filename}")

                arcs_funcs.plot_marginal(
                    df, var, marginal_filename, args.theme,
                    cumulative=args.cumulative
                )

    if args.verbose:
        print("Done!")


if __name__ == "__main__":
    main()
