import argparse
import itertools
import json
import re

import warnings
from dateutil.parser import UnknownTimezoneWarning

warnings.filterwarnings("ignore", category=UnknownTimezoneWarning)

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
parser.add_argument('--min-hits', type=int, help='Compute probability of getting a minimum of this many hits on ships.')
parser.add_argument('--max-damage', type=int, help='Compute probability of taking a maximum of this much damage.')
args = parser.parse_args()
if args.max_damage is not None and args.convert_intercepts is False:
	raise ValueError('Cannot *accurately* compute --max-damage without converting intercepts')

num_assault_dice = args.assault_dice
num_rolls = args.num_draws

assault_dice = [('hit', 'flame'), ('hit', 'hit'), ('hit', 'hit', 'flame'), ('blank'), ('hit', 'intercept'), ('hit', 'hit')]
raid_dice = [('hitb', 'flame'), ('intercept'), ('intercept', 'key', 'key'), ('key', 'flame'), ('key', 'hitb'), ('intercept',)]

hits = 0
flames = 0
hits_squared_deviation = 0
flames_squared_deviation = 0
macrostates = set()

def parse_assault_dice(roll_dict, fresh_targets, dice_types, convert_intercepts=False):
	r'''Parse the rolled values of dice.

	Parameters
	----------
	roll_dict : dict
	'''
	hits = 0
	hitbs = 0
	damage = 0
	keys = 0
	intercepts = False
	blanks = 0
	for die in roll:
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
	if 'assault' in dice_types:
	return f'{hits}H{damage}DI' if intercepts is True and convert_intercepts is False else f'{hits}H{damage}D'

def parse_label_for_probability(labels, probs, min_hits, max_damage):
	pattern = r'(\d+)([HD])'

	result = 0
	for label, prob in zip(labels, probs):
		matches = re.findall(pattern, label)
		label_dict = {}
		for number, letter in matches:
			label_dict[letter] = int(number)
		hits = label_dict['H']
		damage = label_dict['D']
		if (min_hits is not None and max_damage is not None and hits >= min_hits and damage <= max_damage) or (min_hits is None and max_damage is not None and damage <= max_damage) or (min_hits is not None and max_damage is None and hits >= min_hits):
			result += prob

	if min_hits is not None and max_damage is not None:
		print(f'Probability of hitting at least {min_hits} times while taking no more than {max_damage} damage is {result:.4f}')
	elif min_hits is not None and max_damage is None:
		print(f'Probability of hitting at least {min_hits} times is {result:.4f}')
	elif min_hits is None and max_damage is not None:
		print(f'Probability taking no more than {max_damage} damage is {result:.4f}')

#for microstate in itertools.product(assault_dice, assault_dice):
for microstate in itertools.combinations_with_replacement(assault_dice, r=num_assault_dice):
	#macrostates.add(tuple(sorted(microstate)))
	#macrostates.add(' '.join([str(y) for y in sorted(microstate)]))
	macrostates.add(parse_assault_dice(microstate, args.fresh_targets, convert_intercepts=args.convert_intercepts))

roll_hist = dict((macrostate, 0) for macrostate in macrostates)

# start dealing with only assault dice case
for roll in stats.randint.rvs(0, 6, size=(num_rolls, num_assault_dice)):
	result = [assault_dice[r] for r in roll]
	'''
	# FIXME Get this information from parsing the assault dice
	hits_this_roll = 0
	flames_this_roll = 0
	for die in result:
		for symbol in die:
			if symbol == 'hit':
				hits_this_roll += 1
			elif symbol == 'flame':
				flames_this_roll += 1

	hits += hits_this_roll
	flames += flames_this_roll
	hits_squared_deviation += (hits_this_roll - num_assault_dice * 4/3)**2.
	flames_squared_deviation += (flames_this_roll - num_assault_dice * 1/3)**2.
	'''

	macrostate = parse_assault_dice(result, args.fresh_targets, convert_intercepts=args.convert_intercepts)
	roll_hist[macrostate] += 1

#print('Expectation value of hits:', hits / num_rolls, '+-', (hits_squared_deviation / (num_rolls * num_assault_dice))**.5)
#print('Expectation value of flames:', flames / num_rolls, '+-', ((flames_squared_deviation) / (num_rolls * num_assault_dice))**.5)

#with open('arcs_test.json', 'w') as fo:
#	json.dump(roll_hist, fo, indent=4)






# Load your images with matplotlib.image
img_H = mpimg.imread('images/hit_black.png')
img_D = mpimg.imread('images/hit_self_black.png')
img_I = mpimg.imread('images/intercept_black.png')

sorted_keys = sorted(list(roll_hist.keys()), key = lambda k: roll_hist[k], reverse=False)
sorted_probs = sorted([count / num_rolls for count in roll_hist.values()])

parse_label_for_probability(sorted_keys, sorted_probs, args.min_hits, args.max_damage)

fig_height = max(4.8, 0.15 * len(list(roll_hist.keys())))

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
for i, label in enumerate(sorted_keys):
	y_pos = i
	x_offset = -0.1

	for j, char in enumerate(label):
		if char == 'H':
			imagebox = OffsetImage(img_H, zoom=0.1)
			ab = AnnotationBbox(imagebox, (x_offset, y_pos), frameon=False,
			                    clip_on=False,
					    xycoords=('axes fraction', 'data'))
			ax1.add_artist(ab)
		elif char == 'D':
			imagebox = OffsetImage(img_D, zoom=0.09)
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
