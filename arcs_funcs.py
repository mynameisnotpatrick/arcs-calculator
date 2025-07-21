# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

from collections import Counter
import itertools
import re

from scipy.special import factorial
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib import figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg

skirmish_dice = [('blank',), ('hit',)] # identical statistical properties to the full six sided die

assault_dice = [('hit', 'flame'), ('hit', 'hit'), ('hit', 'hit', 'flame'), ('blank',), ('hit', 'intercept'), ('hit', 'hit')]
unique_assault_dice = [('hit', 'flame'), ('hit', 'hit'), ('hit', 'hit', 'flame'), ('blank',), ('hit', 'intercept')]

raid_dice = [('hitb', 'flame'), ('intercept',), ('intercept', 'key', 'key'), ('key', 'flame'), ('key', 'hitb'), ('hitb', 'flame')]
unique_raid_dice = [('hitb', 'flame'), ('intercept',), ('intercept', 'key', 'key'), ('key', 'flame'), ('key', 'hitb')]

face_frequencies = {'skirmish': Counter(skirmish_dice), 'assault': Counter(assault_dice), 'raid': Counter(raid_dice)}

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
	
	condition_str = ' and '.join(conditions)
	result_str = f'Probability of {condition_str} is {result:.4f}'

	return result_str

def adjusted_multinomial_coefficient(combination, dice_str):
	combination_counts = Counter(combination)

	## Compute multinomial coefficient N!/k1!k2!...km! where k1+k2+...+km=N
	## N is number of dice, ki is number of each type of die that was rolled
	total = factorial(len(combination))
	for count in combination_counts.values():
		total /= factorial(count)

	## Multiply by frequency^count for each face
	for face, count in combination_counts.items():
		freq_in_dice = face_frequencies[dice_str][face]
		total *= freq_in_dice ** count

	return total

def compute_probabilities(num_skirmish, num_assault, num_raid, fresh_targets = 0, convert_intercepts = False):
	macrostates_set = set()
	macrostates_dict = {}
	total_states = 0
	for skirmish_combination in itertools.combinations_with_replacement(skirmish_dice, r=num_skirmish):
		skirmish_coefficient = adjusted_multinomial_coefficient(skirmish_combination, 'skirmish')
		for assault_combination in itertools.combinations_with_replacement(unique_assault_dice, r=num_assault):
			assault_coefficient = adjusted_multinomial_coefficient(assault_combination, 'assault')
			for raid_combination in itertools.combinations_with_replacement(unique_raid_dice, r=num_raid):
				combination = parse_dice({'skirmish': skirmish_combination, 'assault': assault_combination, 'raid': raid_combination}, fresh_targets, convert_intercepts=convert_intercepts)
				num_microstates = skirmish_coefficient * assault_coefficient * adjusted_multinomial_coefficient(raid_combination, 'raid')
				if combination not in macrostates_set:
					macrostates_dict[combination] = 0
					macrostates_set.add(combination)
				macrostates_dict[combination] += num_microstates
				total_states += num_microstates

	assert total_states == 2**num_skirmish*6**(num_assault + num_raid),f'total_states = {total_states}, 2**{num_skirmish}*6**{num_assault + num_raid} = {2**num_skirmish*6**(num_assault + num_raid)}'

	sorted_macrostates = sorted(list(macrostates_dict.keys()), key = lambda k: macrostates_dict[k], reverse=False)
	sorted_probs = sorted([count / total_states for count in macrostates_dict.values()])

	return sorted_macrostates, sorted_probs

def plot_most_likely_states(macrostates, probs, num_skirmish, num_assault, num_raid, fresh_targets, fname, convert_intercepts = False, truncate_length = 100,  show_full_plot = False):

	# Load your images with matplotlib.image
	img_H = mpimg.imread('images/hit_black.png')
	img_D = mpimg.imread('images/hit_self_black.png')
	img_I = mpimg.imread('images/intercept_black.png')
	img_B = mpimg.imread('images/hit_building_black.png')
	img_K = mpimg.imread('images/key_black.png')

	if show_full_plot is False:
		if len(macrostates) > truncate_length:
			macrostates = macrostates[-truncate_length:]
			probs = probs[-truncate_length:]
	ylength = len(macrostates)

	fig_height = max(4.8, 0.15 * ylength)

	fig = figure.Figure(figsize=(6.4, fig_height))
	FigureCanvas(fig)

	ax1 = fig.add_subplot(111)
	title = []
	if num_skirmish > 0:
		title.append(f'{num_skirmish} Skirmish')
	if num_assault > 0:
		title.append(f'{num_assault} Assault')
	if num_raid > 0:
		title.append(f'{num_raid} Raid')
	if convert_intercepts:
		title.append(f'{fresh_targets} Fresh Target Ships')

	ax1.set_title(', '.join(title))

	ax1.barh(macrostates, probs, color=[(204/255,121/255,167/255)])
	ax1.set_yticklabels([])
	ax1.set_ylim(-1, len(macrostates))


	offset_diff = 0.018
	# Create custom labels with images
	max_label_length = max([len(label) for label in macrostates])
	for i, label in enumerate(macrostates):
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
	fig.savefig(fname)
