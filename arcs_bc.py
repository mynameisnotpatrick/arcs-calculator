import argparse

import arcs_funcs

parser = argparse.ArgumentParser(description='Roll arcs dice')
parser.add_argument('--assault-dice', '-a', default=0, type=int, help='Number of assault dice to roll (max 6)')
parser.add_argument('--raid-dice', '-r', default=0, type=int, help='Number of raid dice to roll (max 6)')
parser.add_argument('--skirmish-dice', '-s', default=0, type=int, help='Number of skirmish dice to roll (max 6)')
parser.add_argument('--fresh-targets', '-f', default=0, type=int, help='Number of fresh loyal ships you are attacking (makes no difference unless --convert-intercepts is True)')
parser.add_argument('--convert-intercepts', '-c', action='store_true', help='Convert intercepts to hits (default: False)')
parser.add_argument('--min-hits', type=int, help='Compute probability of getting a minimum of this many hits.')
parser.add_argument('--max-damage', type=int, help='Compute probability of taking a maximum of this much damage.')
parser.add_argument('--min-keys', type=int, help='Compute probability of getting a minimum of this many keys.')
parser.add_argument('--min-building-hits', type=int, help='Compute probability of dealing a minimum of this many building hits.')
parser.add_argument('--max-building-hits', type=int, help='Compute probability of dealing a maximum of this many building hits.')
parser.add_argument('--show-full-plot', action='store_true', help='Dont truncate plot to top 50 most probable outcomes. (default: False)')
parser.add_argument('--truncate-length', default=100, type=int, help='Truncate plot so this many of the most probable results will be shown (default: 100). Will be ignored if --show-full-plot is provided.')
args = parser.parse_args()
if args.max_damage is not None and args.convert_intercepts is False:
	raise ValueError('Cannot *accurately* compute --max-damage without converting intercepts')


macrostates, probs = arcs_funcs.compute_probabilities(args.skirmish_dice, args.assault_dice, args.raid_dice, args.fresh_targets, args.convert_intercepts)

if args.min_hits is not None or args.max_damage is not None or args.min_keys is not None or args.min_building_hits is not None or args.max_building_hits is not None:
	print(arcs_funcs.parse_label_for_probability(macrostates, probs, args.min_hits, args.max_damage, args.min_keys, args.min_building_hits, args.max_building_hits))

arcs_funcs.plot_most_likely_states(macrostates, probs, args.skirmish_dice, args.assault_dice, args.raid_dice, args.fresh_targets, 'arcs_test.png', args.convert_intercepts, args.truncate_length, args.show_full_plot)
