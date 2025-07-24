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
import time
from functools import lru_cache

from scipy.special import factorial
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib import figure
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import pandas as pd

# Dice face definitions (shared)
SKIRMISH_DICE = [
	('blank',),
	('hit',)
] # identical statistical properties to the full six sided die

ASSAULT_DICE = [
	('hit', 'flame'),
	('hit', 'hit'),
	('hit', 'hit', 'flame'),
	('blank',),
	('hit', 'intercept'),
	('hit', 'flame')
]
UNIQUE_ASSAULT_DICE = [
	('hit', 'flame'),
	('hit', 'hit'),
	('hit', 'hit', 'flame'),
	('blank',),
	('hit', 'intercept')
]

RAID_DICE = [
	('hitb', 'flame'),
	('intercept',),
	('intercept', 'key', 'key'),
	('key', 'flame'),
	('key', 'hitb'),
	('hitb', 'flame')
]
UNIQUE_RAID_DICE = [
	('hitb', 'flame'),
	('intercept',),
	('intercept', 'key', 'key'),
	('key', 'flame'),
	('key', 'hitb')
]

FACE_FREQUENCIES = {
	'skirmish': Counter(SKIRMISH_DICE),
	'assault': Counter(ASSAULT_DICE),
	'raid': Counter(RAID_DICE)
}

@lru_cache(maxsize=8192)
def parse_dice(skirmish_combination, assault_combination, raid_combination, fresh_targets, convert_intercepts=False):
	roll_dict = {'skirmish': skirmish_combination, 'assault': assault_combination, 'raid': raid_combination}
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

	# Build result efficiently using list join instead of string concatenation
	parts = []
	dice = set(roll_dict.keys())
	if dice == {'skirmish'}:
		assert intercepts is False
		if hits > 0:
			parts.append(f'{hits}H')
	elif dice == {'raid'}:
		if hitbs > 0:
			parts.append(f'{hitbs}B')
		if damage > 0:
			parts.append(f'{damage}D')
		if keys > 0:
			parts.append(f'{keys}K')
	elif 'raid' in dice:
		# Only symbol not on raid dice is hit symbol, which is on both skirmish and assault dice
		if hits > 0:
			parts.append(f'{hits}H')
		if hitbs > 0:
			parts.append(f'{hitbs}B')
		if damage > 0:
			parts.append(f'{damage}D')
		if keys > 0:
			parts.append(f'{keys}K')
	else:
		# Return same set of symbols regardless if assault dice or assault + skirmish dice
		assert 'assault' in dice # sanity check
		if hits > 0:
			parts.append(f'{hits}H')
		if damage > 0:
			parts.append(f'{damage}D')

	if intercepts is True and convert_intercepts is False:
		parts.append('I')

	return ''.join(parts) if parts else '0'

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

@lru_cache(maxsize=None)
def adjusted_multinomial_coefficient(combination, dice_str):
	combination_counts = Counter(combination)

	## Compute multinomial coefficient N!/k1!k2!...km! where k1+k2+...+km=N
	## N is number of dice, ki is number of each type of die that was rolled
	total = factorial(len(combination))
	for count in combination_counts.values():
		total /= factorial(count)

	## Multiply by frequency^count for each face
	for face, count in combination_counts.items():
		freq_in_dice = FACE_FREQUENCIES[dice_str][face]
		total *= freq_in_dice ** count

	return total

def compute_probabilities(num_skirmish, num_assault, num_raid, fresh_targets = 0, convert_intercepts = False):
	macrostates_dict = {}
	total_states = 0
	parse_time = 0
	coefficient_time = 0
	loop_count = 0
	for skirmish_combination in itertools.combinations_with_replacement(SKIRMISH_DICE, r=num_skirmish):
		coeff_start = time.time()
		skirmish_coefficient = adjusted_multinomial_coefficient(skirmish_combination, 'skirmish')
		coefficient_time += time.time() - coeff_start
		for assault_combination in itertools.combinations_with_replacement(UNIQUE_ASSAULT_DICE, r=num_assault):
			coeff_start = time.time()
			assault_coefficient = adjusted_multinomial_coefficient(assault_combination, 'assault')
			coefficient_time += time.time() - coeff_start
			for raid_combination in itertools.combinations_with_replacement(UNIQUE_RAID_DICE, r=num_raid):
				parse_start = time.time()
				combination = parse_dice(skirmish_combination, assault_combination, raid_combination, fresh_targets, convert_intercepts)
				parse_time += time.time() - parse_start
				coeff_start = time.time()
				num_microstates = skirmish_coefficient * assault_coefficient * adjusted_multinomial_coefficient(raid_combination, 'raid')
				coefficient_time += time.time() - coeff_start
				macrostates_dict[combination] = macrostates_dict.get(combination, 0) + num_microstates
				total_states += num_microstates
				loop_count += 1

	assert total_states == 2**num_skirmish*6**(num_assault + num_raid),f'total_states = {total_states}, 2**{num_skirmish}*6**{num_assault + num_raid} = {2**num_skirmish*6**(num_assault + num_raid)}'

	sorted_macrostates = sorted(list(macrostates_dict.keys()), key = lambda k: macrostates_dict[k], reverse=False)
	sorted_probs = sorted([count / total_states for count in macrostates_dict.values()])

	return sorted_macrostates, sorted_probs, parse_time, coefficient_time, loop_count

def plot_most_likely_states(macrostates, probs, num_skirmish, num_assault, num_raid, fresh_targets, fname, convert_intercepts = False, truncate_length = 100,  show_full_plot = False, theme = "light"):

	# Load theme-appropriate images
	if theme == "dark":
		img_H = mpimg.imread('images/hit_white.png')
		img_D = mpimg.imread('images/hit_self_white.png')
		img_I = mpimg.imread('images/intercept_white.png')
		img_B = mpimg.imread('images/hit_building_white.png')
		img_K = mpimg.imread('images/key_white.png')
	else:
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
	# Set up theme colors
	if theme == "dark":
		bg_color = '#0e1117'
		text_color = 'white'
	else:
		bg_color = 'white'
		text_color = 'black'
	bar_color = '#ff4b4b'

	fig = figure.Figure(figsize=(6.4, fig_height), facecolor=bg_color)
	FigureCanvas(fig)

	ax1 = fig.add_subplot(111, facecolor=bg_color)
	title = []
	if num_skirmish > 0:
		title.append(f'{num_skirmish} Skirmish')
	if num_assault > 0:
		title.append(f'{num_assault} Assault')
	if num_raid > 0:
		title.append(f'{num_raid} Raid')
	if convert_intercepts:
		title.append(f'{fresh_targets} Fresh Target Ships')
	ax1.set_title(', '.join(title), color=text_color)

	ax1.barh(macrostates, probs, color=bar_color)
	ax1.set_yticklabels([])
	ax1.set_ylim(-1, len(macrostates))


	# Style the axes for dark mode
	ax1.tick_params(colors=text_color)
	ax1.spines['bottom'].set_color(text_color)
	ax1.spines['top'].set_color(text_color)
	ax1.spines['right'].set_color(text_color)
	ax1.spines['left'].set_color(text_color)
	ax1.xaxis.label.set_color(text_color)
	ax1.yaxis.label.set_color(text_color)
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
				ax1.text(x_offset, y_pos, char, ha='center', va='center', clip_on=False, transform=ax1.get_yaxis_transform(), color=text_color)

			x_offset += offset_diff

	fig.tight_layout()
	fig.savefig(fname)

def get_joint_prob_table(
	skirmish_dice_count, assault_dice_count, raid_dice_count,
	fresh_targets=0, convert_intercepts=False):
	"""
	Returns a DataFrame of all unique result tuples and their probabilities.
	Columns: 'hits', 'damage', 'building_hits', 'keys', 'prob'
	"""
	macrostates, probs, *_ = compute_probabilities(
		skirmish_dice_count, assault_dice_count, raid_dice_count,
		fresh_targets, convert_intercepts
	)
	table = []
	for label, prob in zip(macrostates, probs):
		matches = re.findall(r'(\d+)([HDBK])', label)
		label_dict = {letter: int(number) for number, letter in matches}
		table.append({
			'hits': label_dict.get('H', 0),
			'damage': label_dict.get('D', 0),
			'building_hits': label_dict.get('B', 0),
			'keys': label_dict.get('K', 0),
			'prob': prob
		})
	return pd.DataFrame(table)

def plot_heatmap(df, x_axis, y_axis, fname, theme="light"):
	pivot = df.pivot_table(index=y_axis, columns=x_axis, values='prob', aggfunc='sum', fill_value=0)
	if pivot.empty:
		return
	# Set up theme colors
	if theme == "dark":
		bg_color = '#0e1117'
		text_color = 'white'
	else:
		bg_color = 'white'
		text_color = 'black'
	fig = figure.Figure(figsize=(8, 6), facecolor=bg_color)
	FigureCanvas(fig)
	ax = fig.add_subplot(111, facecolor=bg_color)
	# Create heatmap
	im = ax.imshow(pivot.values, aspect='auto', origin='upper', cmap='viridis')
	# Add probability values as text
	for i in range(len(pivot.index)):
		for j in range(len(pivot.columns)):
			# Use darker text color for lighter cells
			value = pivot.values[i, j]
			max_value = pivot.values.max()
			normalized_value = value / max_value if max_value > 0 else 0
			text_color = 'black' if normalized_value > 0.5 else 'white'
			ax.text(j, i, f"{value:.3f}",
				ha='center', va='center', color=text_color, fontsize=8)
	# Set labels and styling
	ax.set_xticks(range(len(pivot.columns)))
	ax.set_xticklabels(pivot.columns, color=text_color)
	ax.set_yticks(range(len(pivot.index)))
	ax.set_yticklabels(pivot.index, color=text_color)
	ax.set_xlabel(x_axis.replace('_', ' ').title(), color=text_color)
	ax.set_ylabel(y_axis.replace('_', ' ').title(), color=text_color)
	# Style the axes
	ax.tick_params(colors=text_color)
	for spine in ax.spines.values():
		spine.set_color(text_color)
	# Add colorbar
	cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
	cbar.set_label('Probability', color=text_color)
	cbar.ax.tick_params(colors=text_color)
	fig.tight_layout()
	fig.savefig(fname)

def plot_marginal(df, var, fname, theme="light"):
	marginal = df.groupby(var)['prob'].sum().reset_index()
	if marginal.empty:
		return
	# Set up theme colors
	if theme == "dark":
		bg_color = '#0e1117'
		text_color = 'white'
		bar_color = '#ff4b4b'
	else:
		bg_color = 'white'
		text_color = 'black'
		bar_color = '#ff4b4b'
	fig = figure.Figure(figsize=(4, 2.5), facecolor=bg_color)
	FigureCanvas(fig)
	ax = fig.add_subplot(111, facecolor=bg_color)
	# Create bar chart
	bars = ax.bar(marginal[var], marginal['prob'], color=bar_color, alpha=0.8)
	# Add probability text on top of each bar
	max_height = max(marginal['prob'])
	for i, bar in enumerate(bars):
		height = bar.get_height()
		# Only show text for bars above a certain threshold to avoid crowding
		if height > max_height * 0.03:  # Only show if bar is at least 5% of max height
			ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
				f'{height:.2f}', ha='center', va='bottom', color=text_color, fontsize=8)
	# Adjust y-axis limit to make room for text labels
	ax.set_ylim(0, max_height * 1.15)
	# Style the plot
	ax.set_xlabel(var.replace('_', ' ').title(), color=text_color)
	ax.set_ylabel('Probability', color=text_color)
	ax.set_title(f'{var.replace("_", " ").title()} Distribution', color=text_color, fontsize=10)
	ax.tick_params(colors=text_color)
	for spine in ax.spines.values():
		spine.set_color(text_color)
	# Set integer ticks for discrete variables
	if len(marginal[var]) <= 10:
		ax.set_xticks(marginal[var])
	fig.tight_layout()
	fig.savefig(fname)
