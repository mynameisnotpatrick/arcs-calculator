import argparse
import itertools
import json
import re

import warnings
from dateutil.parser import UnknownTimezoneWarning

warnings.filterwarnings("ignore", category=UnknownTimezoneWarning)

import numpy
from scipy import stats
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib import figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg

parser = argparse.ArgumentParser(description='Roll arcs dice')
parser.add_argument('--assault-dice', '-a', default=0, type=int, help='Number of assault dice to roll (max 6)')
parser.add_argument('--raid-dice', '-r', default=0, type=int, help='Number of raid dice to roll (max 6)')
parser.add_argument('--skirmish-dice', '-s', default=0, type=int, help='Number of skirmish dice to roll (max 6)')
parser.add_argument('--num-draws', '-n', default=10000, type=int, help='Number of samples to draw')
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

skirmish_dice = numpy.array([('blank',), ('hit',)], dtype=object) # identical statistical properties to the full six sided die
assault_dice = numpy.array([('hit', 'flame'), ('hit', 'hit'), ('hit', 'hit', 'flame'), ('blank',), ('hit', 'intercept'), ('hit', 'hit')], dtype=object)
raid_dice = numpy.array([('hitb', 'flame'), ('intercept',), ('intercept', 'key', 'key'), ('key', 'flame'), ('key', 'hitb'), ('intercept',)], dtype=object)

def parse_dice(roll_dict, fresh_targets, convert_intercepts=False):
	r'''Parse the rolled values of dice.

	Parameters
	----------
	roll_dict : dict
		Dictionary keyed by dice type with values of consisting of list
		of rolled dice values.

	fresh_targets: int, None
		Number of fresh ships being attacked. Only matters if
		convert_intercepts is True.

	convert_intercepts: bool
		If True, use fresh_targets to convert intercepts to damage to
		self. If False, display intercept as part of results. Default:
		False.
	'''
	hits = 0
	hitbs = 0
	damage = 0
	keys = 0
	intercepts = False
	blanks = 0
	for dice in roll_dict.values():
		for die in dice:
			for symbol in die:
				if symbol == 'hit':
					hits += 1
				elif symbol == 'flame':
					damage += 1
				elif symbol == 'intercept':
					if intercepts is True:
						# We've already processed an intercept
						continue
					intercepts = True
					if convert_intercepts is True:
						if fresh_targets is None:
							raise ValueError("Cannot convert intercepts if fresh targets not set")
						damage += fresh_targets
				elif symbol == 'blank':
					blanks += 1
				elif symbol == 'hitb':
					hitbs += 1
				elif symbol == 'key':
					keys += 1
				else:
					raise NotImplementedError(f'symbol {symbol} from FIXME die not implemented')

	return_str = ''
	dice = set(roll_dict.keys())
	if dice == {'skirmish'}:
		assert intercepts is False
		return_str = f'{hits}H'
	elif dice == {'raid'}:
		return_str = f'{hitbs}B{damage}D{keys}K'
	elif 'raid' in dice:
		# Only symbol not on raid dice is hit symbol, which is on both skirmish and assault dice
		return_str = f'{hits}H{hitbs}B{damage}D{keys}K'
	else:
		# Return same set of symbols regardless if assault dice or assault + skirmish dice
		assert 'assault' in dice # sanity check
		return_str =  f'{hits}H{damage}D'

	if intercepts is True and convert_intercepts is False:
		return_str += 'I'

	return return_str

def evaluate_truth_table(hits, damage, buildings, keys, min_hits, max_damage,
			 min_keys, min_building_hits, max_building_hits):
	# Check each condition if specified
	if min_hits is not None and hits < min_hits:
		return False

	if max_damage is not None and damage > max_damage:
		return False

	if min_keys is not None and keys < min_keys:
		return False

	if min_building_hits is not None and buildings < min_building_hits:
		return False

	if max_building_hits is not None and buildings > max_building_hits:
		return False

	return True

def parse_label_for_probability(labels, probs, min_hits, max_damage, min_keys,
				min_building_hits, max_building_hits):
	# FIXME Add building damage
	pattern = r'(\d+)([HDBK])'

	result = 0
	for label, prob in zip(labels, probs):
		matches = re.findall(pattern, label)
		label_dict = {}
		for number, letter in matches:
			label_dict[letter] = int(number)
		hits = label_dict.get('H', 0)
		damage = label_dict.get('D', 0)
		buildings = label_dict.get('B', 0)
		keys = label_dict.get('B', 0)
		if evaluate_truth_table(hits, damage, buildings, keys, min_hits, max_damage, min_keys, min_building_hits, max_building_hits):
			result += prob

	conditions = []
	if min_hits is not None:
	      conditions.append(f'hitting at least {min_hits} times')
	if max_damage is not None:
	      conditions.append(f'taking no more than {max_damage} damage')
	if min_keys is not None:
	      conditions.append(f'getting at least {min_keys} keys')
	if min_building_hits is not None:
		conditions.append(f'hitting buildings at least {min_building_hits} times')
	if max_building_hits is not None:
		conditions.append(f'hitting buildings no more than {max_building_hits} times')
	
	if conditions:
		condition_str = ' and '.join(conditions)
		print(f'Probability of {condition_str} is {result:.4f}')
	else:
		print(f'Overall probability is {result:.4f}')



macrostates = set()
# FIXME There's definitely a smarter way to do this, but ipython3 timed it this
# for loop with the inner most loop just running pass as only taking 44ms, so
# it probably doesn't matter
for skirmish_microstate in itertools.combinations_with_replacement(skirmish_dice, r=args.skirmish_dice):
	for assault_microstate in itertools.combinations_with_replacement(assault_dice, r=args.assault_dice):
		for raid_microstate in itertools.combinations_with_replacement(raid_dice, r=args.raid_dice):
			macrostates.add(parse_dice({'skirmish': skirmish_microstate, 'assault': assault_microstate, 'raid': raid_microstate}, args.fresh_targets, convert_intercepts=args.convert_intercepts))

roll_hist = dict((macrostate, 0) for macrostate in macrostates)

skirmish_dice_rolls = skirmish_dice[stats.randint.rvs(0, 2, size=(args.num_draws, args.skirmish_dice))]
assault_dice_rolls = assault_dice[stats.randint.rvs(0, 6, size=(args.num_draws, args.assault_dice))]
raid_dice_rolls = raid_dice[stats.randint.rvs(0, 6, size=(args.num_draws, args.raid_dice))]
for skirmish_roll, assault_roll, raid_roll in zip(skirmish_dice_rolls, assault_dice_rolls, raid_dice_rolls):
	macrostate = parse_dice({'skirmish': skirmish_roll, 'assault': assault_roll, 'raid': raid_roll}, args.fresh_targets, convert_intercepts=args.convert_intercepts)
	roll_hist[macrostate] += 1

sorted_keys = sorted(list(roll_hist.keys()), key = lambda k: roll_hist[k], reverse=False)
sorted_probs = sorted([count / args.num_draws for count in roll_hist.values()])

if args.min_hits is not None or args.max_damage is not None or args.min_keys is not None or args.min_building_hits is not None or args.max_building_hits is not None:
	parse_label_for_probability(sorted_keys, sorted_probs, args.min_hits, args.max_damage, args.min_keys, args.min_building_hits, args.max_building_hits)

# Load your images with matplotlib.image
img_H = mpimg.imread('images/hit_black.png')
img_D = mpimg.imread('images/hit_self_black.png')
img_I = mpimg.imread('images/intercept_black.png')
img_B = mpimg.imread('images/hit_building_black.png')
img_K = mpimg.imread('images/key_black.png')

if args.show_full_plot is False:
	if len(sorted_keys) > args.truncate_length:
		sorted_keys = sorted_keys[-args.truncate_length:]
		sorted_probs = sorted_probs[-args.truncate_length:]
ylength = len(sorted_keys)

fig_height = max(4.8, 0.15 * ylength)

fig = figure.Figure(figsize=(6.4, fig_height))
FigureCanvas(fig)

ax1 = fig.add_subplot(111)
title = []
if args.skirmish_dice > 0:
	title.append(f'{args.skirmish_dice} Skirmish')
if args.assault_dice > 0:
	title.append(f'{args.assault_dice} Assault')
if args.raid_dice > 0:
	title.append(f'{args.raid_dice} Raid')
if args.convert_intercepts:
	title.append(f'{args.fresh_targets} Fresh Target Ships')

ax1.set_title(', '.join(title))

ax1.barh(sorted_keys, sorted_probs, color=[(204/255,121/255,167/255)])
ax1.set_yticklabels([])
ax1.set_ylim(-1, len(sorted_keys))


offset_diff = 0.018
# Create custom labels with images
max_label_length = max([len(label) for label in sorted_keys])
for i, label in enumerate(sorted_keys):
	y_pos = i
	x_offset = -0.02 * max_label_length

	for j, char in enumerate(label):
		if char == 'H':
			imagebox = OffsetImage(img_H, zoom=0.1)
			ab = AnnotationBbox(imagebox, (x_offset, y_pos), frameon=False,
			                    clip_on=False,
					    xycoords=('axes fraction', 'data'))
			ax1.add_artist(ab)
		elif char == 'B':
			imagebox = OffsetImage(img_B, zoom=0.09)
			ab = AnnotationBbox(imagebox, (x_offset + 0.003, y_pos), frameon=False,
			                    clip_on=False,
					    xycoords=('axes fraction', 'data'))
			ax1.add_artist(ab)
		elif char == 'D':
			imagebox = OffsetImage(img_D, zoom=0.09)
			ab = AnnotationBbox(imagebox, (x_offset, y_pos), frameon=False,
			                    clip_on=False,
					    xycoords=('axes fraction', 'data'))
			ax1.add_artist(ab)
		elif char == 'K':
			imagebox = OffsetImage(img_K, zoom=0.1)
			ab = AnnotationBbox(imagebox, (x_offset, y_pos), frameon=False,
			                    clip_on=False,
					    xycoords=('axes fraction', 'data'))
			ax1.add_artist(ab)
		elif char == 'I':
			imagebox = OffsetImage(img_I, zoom=0.09)
			ab = AnnotationBbox(imagebox, (x_offset + 0.003, y_pos), frameon=False,
			                    clip_on=False,
					    xycoords=('axes fraction', 'data'))
			ax1.add_artist(ab)
		else:
			ax1.text(x_offset, y_pos, char, ha='center', va='center', clip_on=False, transform=ax1.get_yaxis_transform())

		x_offset += offset_diff



fig.tight_layout()
fig.savefig('arcs_test.png')
