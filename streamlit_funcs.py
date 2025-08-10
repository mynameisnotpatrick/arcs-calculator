# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import base64
import html
import os
import re
import tempfile
from contextlib import contextmanager

import streamlit as st

import arcs_funcs


# Theme detection helper function
def get_streamlit_theme():
    """Get current Streamlit theme, with fallback"""
    try:
        theme_type = st.context.theme.type
        # Assume anything that isn't dark is light
        return "dark" if theme_type == "dark" else "light"
    except Exception:
        return "dark"  # Fallback theme


def _validate_dice_state(state):
    """
    Validate dice state string to ensure it only contains expected characters.

    Args:
        state: String representing dice state

    Returns:
        bool: True if state is safe, False otherwise
    """
    if not isinstance(state, str):
        return False

    # Only allow expected dice characters and numbers
    allowed_pattern = r'^[HDBKI0-9]*$'
    return bool(re.match(allowed_pattern, state))


def _validate_base64_image(base64_string):
    """
    Validate that a base64 string represents a valid PNG image.

    Args:
        base64_string: Base64 encoded string

    Returns:
        bool: True if valid base64 PNG, False otherwise
    """
    if not isinstance(base64_string, str):
        return False

    try:
        # Check if it's valid base64
        decoded = base64.b64decode(base64_string, validate=True)

        # Check PNG signature (first 8 bytes)
        png_signature = b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'
        return decoded.startswith(png_signature)
    except Exception:
        return False


def safe_dice_display_html(state, dice_images, theme_option):
    """
    Generate safe HTML for dice state display with security validations.

    Args:
        state: String representing dice state (e.g., "3H2D")
        dice_images: Dictionary of base64 encoded images
        theme_option: Current theme ('light' or 'dark')

    Returns:
        str: Safe HTML string for display
    """
    # Validate inputs
    if not _validate_dice_state(state):
        escaped_state = html.escape(str(state))
        return f"<span style='color: red;'>Invalid dice state: " \
               f"{escaped_state}</span>"

    if theme_option not in ['light', 'dark']:
        theme_option = 'dark'  # Safe fallback

    current_images = dice_images.get(theme_option, {})

    html_content = ("<div style='display: flex; align-items: center; "
                    "gap: 2px;'>")

    for char in state:
        # Escape the character for safe HTML output
        escaped_char = html.escape(char)

        if char in current_images and current_images[char]:
            # Validate base64 image data
            base64_img = current_images[char]
            if _validate_base64_image(base64_img):
                html_content += (
                    f"<img src='data:image/png;base64,{base64_img}' "
                    f"width='15' style='margin: 0;' alt='{escaped_char}'>")
            else:
                # Fallback if image validation fails
                html_content += (
                    f"<span style='font-weight: bold; margin: 0 2px; "
                    f"background-color: #ff9999; padding: 2px; "
                    f"border-radius: 2px;' title='Invalid image data'>"
                    f"{escaped_char}</span>")
        elif char.isalpha():
            # Fallback for missing images - show styled letter
            html_content += (
                f"<span style='font-weight: bold; margin: 0 2px; "
                f"background-color: #ddd; padding: 2px; "
                f"border-radius: 2px;'>"
                f"{escaped_char}</span>")
        else:
            # Numbers and other characters
            html_content += (
                f"<span style='font-weight: bold; margin: 0 2px;'>"
                f"{escaped_char}</span>")

    html_content += "</div>"
    return html_content


# Temporary file context manager


@contextmanager
def temp_plot_file():
    """Context manager for temporary plot files with automatic cleanup"""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        try:
            yield tmp_file.name
        finally:
            os.unlink(tmp_file.name)


# Cache probability calculations based on dice configuration
@st.cache_data
def cached_compute_probabilities(skirmish_dice, assault_dice, raid_dice,
                                 fresh_targets, convert_intercepts):
    return arcs_funcs.compute_probabilities(skirmish_dice, assault_dice,
                                            raid_dice, fresh_targets,
                                            convert_intercepts)

# Pre-load and cache all images at app startup


@st.cache_data
def load_dice_images():
    def img_to_base64(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()

    result = {}
    for theme in ['dark', 'light']:
        image_paths = arcs_funcs.ThemeManager.get_theme_images(theme)
        result[theme] = {key: img_to_base64(path)
                         for key, path in image_paths.items()}
    return result


def probability_calculator_inputs(label1, label2):
    hits_col1, hits_col2 = st.columns(2)
    with hits_col1:
        input1 = st.number_input(label1, min_value=0, value=None,
                                 placeholder="Any")
    with hits_col2:
        input2 = st.number_input(label2, min_value=0, value=None,
                                 placeholder="Any")

    return input1, input2


def get_dashboard_axes():
    dash_col1, dash_col2 = st.columns(2)
    all_variables = ['hits', 'damage', 'building hits', 'keys']
    # Get current selections from session state to handle
    # initialization order
    current_y = st.session_state.get("dashboard_y_axis",
                                     all_variables[0])
    current_x = st.session_state.get("dashboard_x_axis",
                                     all_variables[1])
    with dash_col1:
        y_axis_options = [var for var in all_variables
                          if var != current_x]
        y_axis = st.selectbox("Y-axis variable:",
                              options=y_axis_options,
                              index=y_axis_options.index(current_y)
                              if current_y in y_axis_options else 0,
                              key="dashboard_y_axis")
    with dash_col2:
        x_axis_options = [var for var in all_variables if var != y_axis]
        x_axis = st.selectbox("X-axis variable:",
                              options=x_axis_options,
                              index=x_axis_options.index(current_x)
                              if current_x in x_axis_options else 0,
                              key="dashboard_x_axis")

    return x_axis, y_axis


def create_2D_and_marginal_plots(skirmish_dice, assault_dice, raid_dice,
                                 fresh_targets, convert_intercepts, x_axis,
                                 y_axis, theme_option, cumulative_plots):
    # Get joint probability table
    df = arcs_funcs.get_joint_prob_table(
        skirmish_dice, assault_dice, raid_dice, fresh_targets,
        convert_intercepts
    )
    # Create dashboard layout
    heatmap_col, marginals_col = st.columns([3, 2])
    with heatmap_col:
        st.subheader(f"Probability Heatmap: {y_axis.title()} vs "
                     f"{x_axis.title()}")
        with temp_plot_file() as tmp_filename:
            arcs_funcs.plot_heatmap(
                df, x_axis.replace(' ', '_'), y_axis.replace(' ', '_'),
                tmp_filename, theme_option,
                cumulative=cumulative_plots)
            st.image(tmp_filename)
    with marginals_col:
        st.subheader("Marginal Distributions")
        variables = ['hits', 'damage', 'building_hits', 'keys']
        for var in variables:
            marginal = df.groupby(var)['prob'].sum().reset_index()
            if len(marginal) > 1:
                with temp_plot_file() as tmp_filename:
                    arcs_funcs.plot_marginal(
                        df, var, tmp_filename, theme_option,
                        cumulative=cumulative_plots
                    )
                    st.image(tmp_filename)


def show_probable_individual_rolls(session_state, fresh_targets,
                                   convert_intercepts, dice_images,
                                   theme_option):
    individual_cols = st.columns(min(len(session_state.rolls), 3))

    for i, roll in enumerate(session_state.rolls):
        roll_total = roll['skirmish'] + roll['assault'] + roll['raid']
        if roll_total > 0:
            col_idx = i % len(individual_cols)
            with individual_cols[col_idx]:
                st.markdown(f"**Five Most Likely Roll {i+1} Results**")
                roll_macrostates, roll_probs, *_ = \
                    cached_compute_probabilities(
                        roll['skirmish'], roll['assault'],
                        roll['raid'], fresh_targets,
                        convert_intercepts)

                # Show top 5 outcomes for this roll
                top_outcomes = list(zip(roll_macrostates[-5:],
                                        roll_probs[-5:]))
                for state, prob in reversed(top_outcomes):
                    # Create columns for state and probability
                    state_col, prob_col = st.columns([3, 1])

                    with state_col:
                        # Use secure HTML generation
                        safe_html = safe_dice_display_html(
                            state, dice_images, theme_option)
                        st.markdown(
                            safe_html, unsafe_allow_html=True)

                    with prob_col:
                        st.markdown(f"**{prob:.3f}**")
