# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import itertools
import re
import time
from collections import Counter
from functools import lru_cache

import matplotlib.image as mpimg
import pandas as pd
from matplotlib import figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.ticker import MaxNLocator
from scipy.special import factorial


class ThemeManager:
    """Centralized theme management for consistent styling across all plots"""

    @staticmethod
    def get_theme_colors(theme="light"):
        """Get theme-appropriate colors for plots"""
        if theme == "dark":
            return {
                'bg_color': '#0e1117',
                'text_color': 'white',
                'bar_color': '#ff4b4b'
            }
        else:
            return {
                'bg_color': 'white',
                'text_color': 'black',
                'bar_color': '#ff4b4b'
            }

    @staticmethod
    def get_theme_images(theme="light"):
        """Get theme-appropriate image paths"""
        if theme == "dark":
            return {
                'H': 'images/hit_white.png',
                'D': 'images/hit_self_white.png',
                'I': 'images/intercept_white.png',
                'B': 'images/hit_building_white.png',
                'K': 'images/key_white.png'
            }
        else:
            return {
                'H': 'images/hit_black.png',
                'D': 'images/hit_self_black.png',
                'I': 'images/intercept_black.png',
                'B': 'images/hit_building_black.png',
                'K': 'images/key_black.png'
            }

    @staticmethod
    def setup_figure(figsize, theme="light"):
        """Create and setup a themed matplotlib figure"""
        colors = ThemeManager.get_theme_colors(theme)
        fig = figure.Figure(figsize=figsize, facecolor=colors['bg_color'])
        FigureCanvas(fig)
        ax = fig.add_subplot(111, facecolor=colors['bg_color'])
        return fig, ax, colors

    @staticmethod
    def style_axes(ax, colors):
        """Apply consistent axis styling"""
        ax.tick_params(colors=colors['text_color'])
        for spine in ax.spines.values():
            spine.set_color(colors['text_color'])

    @staticmethod
    def add_colorbar(fig, im, ax, colors, label='Probability'):
        """Add a consistently styled colorbar"""
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(label, color=colors['text_color'])
        cbar.ax.tick_params(colors=colors['text_color'])
        return cbar

    @staticmethod
    def set_labels_and_title(ax, colors, xlabel=None, ylabel=None, title=None):
        """Set axis labels and title with consistent styling"""
        if xlabel:
            ax.set_xlabel(xlabel, color=colors['text_color'])
        if ylabel:
            ax.set_ylabel(ylabel, color=colors['text_color'])
        if title:
            ax.set_title(title, color=colors['text_color'])

    @staticmethod
    def load_theme_images(theme="light"):
        """Load all theme-appropriate images into a dictionary"""
        image_paths = ThemeManager.get_theme_images(theme)
        return {
            key: mpimg.imread(path)
            for key, path in image_paths.items()
        }

    @staticmethod
    def parse_dice_label(label):
        """Parse dice result label into component values"""
        matches = re.findall(r'(\d+)([HDBK])', label)
        return {letter: int(number) for number, letter in matches}

    @staticmethod
    def get_variable_symbol(variable_name, theme="light"):
        """Get the symbol image for a variable name"""
        variable_to_symbol = {
            'hits': 'H',
            'damage': 'D',
            'building_hits': 'B',
            'keys': 'K'
        }
        symbol = variable_to_symbol.get(variable_name)
        if symbol:
            images = ThemeManager.get_theme_images(theme)
            return images.get(symbol)
        return None


# Dice face definitions (shared)
SKIRMISH_DICE = [
    ('blank',),
    ('hit',)
]  # identical statistical properties to the full six sided die

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
def parse_dice(skirmish_combination, assault_combination, raid_combination,
               fresh_targets, convert_intercepts=False):
    roll_dict = {'skirmish': skirmish_combination,
                 'assault': assault_combination,
                 'raid': raid_combination}
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
                            raise ValueError(
                                "Cannot convert intercepts if fresh targets "
                                "not set")
                        damage += fresh_targets
                elif symbol == 'blank':
                    blanks += 1
                elif symbol == 'hitb':
                    hitbs += 1
                elif symbol == 'key':
                    keys += 1
                else:
                    raise NotImplementedError(
                        f'symbol {symbol} from FIXME die not implemented')

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
        # Only symbol not on raid dice is hit symbol, which is on both
        # skirmish and assault dice
        if hits > 0:
            parts.append(f'{hits}H')
        if hitbs > 0:
            parts.append(f'{hitbs}B')
        if damage > 0:
            parts.append(f'{damage}D')
        if keys > 0:
            parts.append(f'{keys}K')
    else:
        # Return same set of symbols regardless if assault dice or
        # assault + skirmish dice
        assert 'assault' in dice  # sanity check
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
    result = 0
    for label, prob in zip(labels, probs):
        label_dict = ThemeManager.parse_dice_label(label)
        hits = label_dict.get('H', 0)
        damage = label_dict.get('D', 0)
        buildings = label_dict.get('B', 0)
        keys = label_dict.get('K', 0)
        if evaluate_truth_table(hits, damage, buildings, keys, min_hits,
                                max_damage, min_keys, min_building_hits,
                                max_building_hits):
            result += prob

    conditions = []
    if min_hits is not None:
        conditions.append(f'hitting at least {min_hits} times')
    if max_damage is not None:
        conditions.append(f'taking no more than {max_damage} damage')
    if min_keys is not None:
        conditions.append(f'getting at least {min_keys} keys')
    if min_building_hits is not None:
        conditions.append(
            f'hitting buildings at least {min_building_hits} times')
    if max_building_hits is not None:
        conditions.append(
            f'hitting buildings no more than {max_building_hits} times')

    condition_str = ' and '.join(conditions)
    result_str = f'Probability of {condition_str} is {result:.4f}'

    return result_str


@lru_cache(maxsize=None)
def adjusted_multinomial_coefficient(combination, dice_str):
    combination_counts = Counter(combination)

    # Compute multinomial coefficient N!/k1!k2!...km! where k1+k2+...+km=N
    # N is number of dice, ki is number of each type of die that was rolled
    total = factorial(len(combination))
    for count in combination_counts.values():
        total /= factorial(count)

    # Multiply by frequency^count for each face
    for face, count in combination_counts.items():
        freq_in_dice = FACE_FREQUENCIES[dice_str][face]
        total *= freq_in_dice ** count

    return total


def compute_probabilities(num_skirmish, num_assault, num_raid,
                          fresh_targets=0, convert_intercepts=False):
    macrostates_dict = {}
    total_states = 0
    parse_time = 0
    coefficient_time = 0
    loop_count = 0
    for skirmish_combination in itertools.combinations_with_replacement(
            SKIRMISH_DICE, r=num_skirmish):
        coeff_start = time.time()
        skirmish_coefficient = adjusted_multinomial_coefficient(
            skirmish_combination, 'skirmish')
        coefficient_time += time.time() - coeff_start
        for assault_combination in itertools.combinations_with_replacement(
                UNIQUE_ASSAULT_DICE, r=num_assault):
            coeff_start = time.time()
            assault_coefficient = adjusted_multinomial_coefficient(
                assault_combination, 'assault')
            coefficient_time += time.time() - coeff_start
            for raid_combination in itertools.combinations_with_replacement(
                    UNIQUE_RAID_DICE, r=num_raid):
                parse_start = time.time()
                combination = parse_dice(
                    skirmish_combination, assault_combination,
                    raid_combination, fresh_targets, convert_intercepts)
                parse_time += time.time() - parse_start
                coeff_start = time.time()
                num_microstates = (
                    skirmish_coefficient * assault_coefficient *
                    adjusted_multinomial_coefficient(raid_combination, 'raid'))
                coefficient_time += time.time() - coeff_start
                macrostates_dict[combination] = (
                    macrostates_dict.get(combination, 0) + num_microstates)
                total_states += num_microstates
                loop_count += 1

    assert total_states == 2**num_skirmish * 6**(num_assault + num_raid)

    sorted_macrostates = sorted(list(macrostates_dict.keys()),
                                key=lambda k: macrostates_dict[k],
                                reverse=False)
    sorted_probs = sorted([count / total_states
                          for count in macrostates_dict.values()])

    return (sorted_macrostates, sorted_probs, parse_time, coefficient_time,
            loop_count)


def plot_most_likely_states(macrostates, probs, num_skirmish, num_assault,
                            num_raid, fresh_targets, fname,
                            convert_intercepts=False, truncate_length=100,
                            show_full_plot=False, theme="light"):

    # Load theme-appropriate images
    images = ThemeManager.load_theme_images(theme)

    if show_full_plot is False:
        if len(macrostates) > truncate_length:
            macrostates = macrostates[-truncate_length:]
            probs = probs[-truncate_length:]
    ylength = len(macrostates)

    fig_height = max(4.8, 0.15 * ylength)
    fig, ax1, colors = ThemeManager.setup_figure((6.4, fig_height), theme)

    # Build title from dice configuration
    title_parts = []
    if num_skirmish > 0:
        title_parts.append(f'{num_skirmish} Skirmish')
    if num_assault > 0:
        title_parts.append(f'{num_assault} Assault')
    if num_raid > 0:
        title_parts.append(f'{num_raid} Raid')
    if convert_intercepts:
        title_parts.append(f'{fresh_targets} Fresh Target Ships')

    # Set up plot
    ax1.barh(macrostates, probs, color=colors['bar_color'])
    ax1.set_yticklabels([])
    ax1.set_ylim(-1, len(macrostates))
    ThemeManager.set_labels_and_title(ax1, colors,
                                      title=', '.join(title_parts))
    ThemeManager.style_axes(ax1, colors)
    ax1.xaxis.label.set_color(colors['text_color'])
    ax1.yaxis.label.set_color(colors['text_color'])
    offset_diff = 0.018
    # Create custom labels with images
    max_label_length = max([len(label) for label in macrostates])
    for i, label in enumerate(macrostates):
        y_pos = i
        x_offset = -0.02 * max_label_length

        for j, char in enumerate(label):
            if char in images:
                zoom = 0.1 if char in ['H', 'K'] else 0.09
                x_adjust = 0.003 if char in ['B', 'I'] else 0
                imagebox = OffsetImage(images[char], zoom=zoom)
                ab = AnnotationBbox(imagebox, (x_offset + x_adjust, y_pos),
                                    frameon=False, clip_on=False,
                                    xycoords=('axes fraction', 'data'))
                ax1.add_artist(ab)
            else:
                ax1.text(x_offset, y_pos, char, ha='center', va='center',
                         clip_on=False, transform=ax1.get_yaxis_transform(),
                         color=colors['text_color'])

            x_offset += offset_diff

    fig.tight_layout()
    fig.savefig(fname)


def get_joint_prob_table(skirmish_dice_count, assault_dice_count,
                         raid_dice_count, fresh_targets=0,
                         convert_intercepts=False):
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
        label_dict = ThemeManager.parse_dice_label(label)
        table.append({
            'hits': label_dict.get('H', 0),
            'damage': label_dict.get('D', 0),
            'building_hits': label_dict.get('B', 0),
            'keys': label_dict.get('K', 0),
            'prob': prob
        })
    return pd.DataFrame(table)


def plot_heatmap(df, x_axis, y_axis, fname, theme="light", cumulative=False):
    pivot = df.pivot_table(index=y_axis, columns=x_axis, values='prob',
                           aggfunc='sum', fill_value=0)
    if pivot.empty:
        return
    if cumulative:
        # Create joint cumulative distribution: P(X <= x, Y <= y)
        # First cumsum along axis 1 (columns/x-axis), then axis 0 (rows/y-axis)
        cumulative_pivot = pivot.cumsum(axis=1).cumsum(axis=0)
        pivot_values = cumulative_pivot.values
    else:
        pivot_values = pivot.values
    fig, ax, colors = ThemeManager.setup_figure((8, 6), theme)
    # Create heatmap
    im = ax.imshow(pivot_values, aspect='auto', origin='lower', cmap='viridis')
    # Add probability values as text
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            # Use darker text color for lighter cells
            value = pivot_values[i, j]
            max_value = pivot_values.max()
            normalized_value = value / max_value if max_value > 0 else 0
            text_color = 'black' if normalized_value > 0.5 else 'white'
            ax.text(j, i, f"{value:.3f}", ha='center', va='center',
                    color=text_color, fontsize=8)
    # Set labels and styling
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, color=colors['text_color'])
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, color=colors['text_color'])

    x_label = f"{x_axis.replace('_', ' ').title()}"
    y_label = f"{y_axis.replace('_', ' ').title()}"
    ax.set_xlabel(x_label, color=colors['text_color'])
    ax.set_ylabel(y_label, color=colors['text_color'])

    # Add symbols positioned relative to text labels (like main
    # probability plot)
    x_symbol_path = ThemeManager.get_variable_symbol(x_axis, theme)
    y_symbol_path = ThemeManager.get_variable_symbol(y_axis, theme)

    if x_symbol_path:
        x_symbol = mpimg.imread(x_symbol_path)
        imagebox = OffsetImage(x_symbol, zoom=0.1)
        # Position symbol at end of x-axis label - use specific positions
        # for each variable
        # FIXME Would be great to do something more generalizable here
        if len(x_label) == 4:  # "Hits" and "Keys" - start with base position
            x_symbol_x_offset = 0.535
        elif x_label == "Damage":
            x_symbol_x_offset = 0.555
        elif x_label == "Building Hits":
            x_symbol_x_offset = 0.59
        ab = AnnotationBbox(imagebox, (x_symbol_x_offset, -0.07),
                            frameon=False, clip_on=False,
                            xycoords='axes fraction')
        ax.add_artist(ab)

    if y_symbol_path:
        if max(pivot.index) < 10:
            y_symbol_x_offset = -0.05
        else:
            y_symbol_x_offset = -0.065
        y_symbol = mpimg.imread(y_symbol_path)
        # Transpose and flip to achieve 90-degree counter-clockwise rotation
        rotated_symbol = y_symbol.transpose(1, 0, 2)[::-1]
        imagebox = OffsetImage(rotated_symbol, zoom=0.1)
        # Position symbol at end of y-axis label - use specific positions
        # for each variable
        # FIXME Would be great to do something more generalizable here
        if len(y_label) == 4:  # "Hits" and "Keys" - perfect at 4 chars
            y_symbol_loc = 0.54
        elif y_label == "Damage":
            y_symbol_loc = 0.57
        elif y_label == "Building Hits":
            y_symbol_loc = 0.6
        ab = AnnotationBbox(imagebox, (y_symbol_x_offset, y_symbol_loc),
                            frameon=False, clip_on=False,
                            xycoords='axes fraction')
        ax.add_artist(ab)
    ThemeManager.style_axes(ax, colors)
    ThemeManager.add_colorbar(fig, im, ax, colors)
    fig.tight_layout()
    fig.savefig(fname)


def plot_marginal(df, var, fname, theme="light", cumulative=False):
    marginal = df.groupby(var)['prob'].sum().reset_index()
    if marginal.empty:
        return
    fig, ax, colors = ThemeManager.setup_figure((4, 2.5), theme)
    if cumulative is False:
        # Create bar chart
        bars = ax.bar(marginal[var], marginal['prob'],
                      color=colors['bar_color'], alpha=0.8)
        # Add probability text on top of each bar
        max_height = max(marginal['prob'])
        for i, bar in enumerate(bars):
            height = bar.get_height()
            # Only show text for bars above a certain threshold to avoid
            # crowding
            if height > max_height * 0.03:  # Only show if bar is at least
                # 3% of max height
                ax.text(bar.get_x() + bar.get_width() / 2.,
                        height + height * 0.01, f'{height:.2f}',
                        ha='center', va='bottom',
                        color=colors['text_color'], fontsize=8)
        # Adjust y-axis limit to make room for text labels
        ax.set_ylim(0, max_height * 1.15)

    else:
        ax.step(marginal[var], marginal['prob'].cumsum(),
                color=colors['bar_color'], alpha=0.8)
    # Style the plot with parentheses for symbol
    x_label = f"{var.replace('_', ' ').title()}"
    ThemeManager.set_labels_and_title(ax, colors,
                                      xlabel=x_label,
                                      ylabel='Probability',
                                      title=f'{var.replace("_", " ").title()}'
                                            ' Distribution')
    # Add symbol image at end of x-axis label
    symbol_path = ThemeManager.get_variable_symbol(var, theme)
    if symbol_path:
        symbol = mpimg.imread(symbol_path)
        imagebox = OffsetImage(symbol, zoom=0.08)
        # Position symbol at end of x-axis label - use specific positions
        # for each variable
        # FIXME Would be great to do something more generalizable here
        if len(x_label) == 4:  # "Hits" and "Keys" - base position for
            # 4-character words
            x_symbol_x_offset = 0.57
        elif x_label == "Damage":
            x_symbol_x_offset = 0.615
        elif x_label == "Building Hits":
            x_symbol_x_offset = 0.665
        ab = AnnotationBbox(imagebox, (x_symbol_x_offset, -0.25),
                            frameon=False, clip_on=False,
                            xycoords='axes fraction')
        ax.add_artist(ab)
    ax.set_title(ax.get_title(), fontsize=10)  # Adjust title font size
    ThemeManager.style_axes(ax, colors)
    # Set integer ticks for discrete variables (dice outcomes are always
    # integers)
    ax.set_xticks(marginal[var])
    # Ensure x-axis only shows integer labels
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    fig.tight_layout()
    fig.savefig(fname)
