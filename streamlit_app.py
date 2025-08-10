# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import time

import streamlit as st

import arcs_funcs
import streamlit_funcs

st.set_page_config(
    page_title="Arcs Dice Calculator",
    page_icon="images/sworn_guardians_avatar.png",
    layout="wide"
)

st.title("Arcs Dice Calculator")
st.markdown("Calculate probabilities for Arcs dice rolls with interactive "
            "charts! Arcs is designed by Cole Wehrle, illustrated by Kyle "
            "Ferrin, and published by Leder Games.")

# Sidebar for dice configuration
st.sidebar.header("Roll Configuration")

# Multi-roll mode toggle
multi_roll_mode = st.sidebar.checkbox(
    "Multi-Roll Mode", value=False,
    help="Configure multiple sequential rolls (WARNING: DOES NOT ALLOW FRESH "
         "TARGETS TO CHANGE BETWEEN ROLLS, USER BEWARE)")

# Set up number of each type of dice
if multi_roll_mode:
    st.sidebar.subheader("Sequential Rolls")

    # Initialize session state for rolls
    if 'rolls' not in st.session_state:
        st.session_state.rolls = [{'skirmish': 0, 'assault': 2, 'raid': 0}]

    # Add/remove roll buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Add Roll", key="add_roll"):
            st.session_state.rolls.append({
                'skirmish': 0, 'assault': 0, 'raid': 0})
    with col2:
        if (st.button("Remove Roll", key="remove_roll") and
                len(st.session_state.rolls) > 1):
            st.session_state.rolls.pop()

    # Configure each roll
    for i, roll in enumerate(st.session_state.rolls):
        st.sidebar.markdown(f"**Roll {i+1}:**")
        roll['skirmish'] = st.sidebar.slider(
            "Skirmish Dice", min_value=0, max_value=6,
            value=roll['skirmish'], key=f"skirmish_{i}")
        roll['assault'] = st.sidebar.slider(
            "Assault Dice", min_value=0, max_value=6,
            value=roll['assault'], key=f"assault_{i}")
        roll['raid'] = st.sidebar.slider(
            "Raid Dice", min_value=0, max_value=6,
            value=roll['raid'], key=f"raid_{i}")
        if i < len(st.session_state.rolls) - 1:
            st.sidebar.markdown("---")

    # FIXME Naive method, just use totals
    skirmish_dice = sum(roll['skirmish'] for roll in st.session_state.rolls)
    assault_dice = sum(roll['assault'] for roll in st.session_state.rolls)
    raid_dice = sum(roll['raid'] for roll in st.session_state.rolls)
else:
    st.sidebar.subheader("Single Roll")
    skirmish_dice = st.sidebar.slider("Skirmish Dice", min_value=0,
                                      max_value=6, value=0)
    assault_dice = st.sidebar.slider("Assault Dice", min_value=0,
                                     max_value=6, value=2)
    raid_dice = st.sidebar.slider("Raid Dice", min_value=0, max_value=6,
                                  value=0)

st.sidebar.header("Battle Configuration")
fresh_targets = st.sidebar.number_input("Fresh Target Ships",
                                        min_value=0, max_value=30, value=2)
convert_intercepts = st.sidebar.checkbox("Convert Intercepts to Damage",
                                         value=True)

st.sidebar.header("Display Options")
cumulative_plots = st.sidebar.checkbox("Cumulative Dashboard Plots",
                                       value=False)

show_all_outcomes = st.sidebar.checkbox(
    "Show All Possible Outcomes", value=False)
if not show_all_outcomes:
    truncate_length = st.sidebar.slider("Max Results to Show in Plot",
                                        min_value=10, max_value=100,
                                        value=20)

    summary_table_truncate_length = st.sidebar.slider(
        "Max Results to Show in Summary Table", min_value=10, max_value=100,
        value=10)
else:
    truncate_length = None
    summary_table_truncate_length = None


debugging_info = st.sidebar.checkbox(
    "Show Execution Timing (For Debugging)", value=False)

theme_option = streamlit_funcs.get_streamlit_theme()

# Load images once
dice_images = streamlit_funcs.load_dice_images()

# Probability Calculator Section
st.subheader("Custom Probability Calculator")
st.markdown("Calculate the probability of specific outcomes:")

prob_col1, prob_col2 = st.columns(2)

with prob_col1:
    st.markdown("**Hits**")
    min_hits, max_hits = \
        streamlit_funcs.probability_calculator_inputs("Min Hits", "Max Hits")

    st.markdown("**Damage to Self**")
    min_damage, max_damage = \
        streamlit_funcs.probability_calculator_inputs(
                                                      "Min Damage",
                                                      "Max Damage"
                                                     )

with prob_col2:
    st.markdown("**Keys**")
    min_keys, max_keys = \
        streamlit_funcs.probability_calculator_inputs("Min Keys", "Max Keys")

    st.markdown("**Building Hits**")
    min_building_hits, max_building_hits = \
        streamlit_funcs.probability_calculator_inputs("Min Building Hits",
                                                      "Max Building Hits")

if st.button("Calculate Custom Probability", type="primary"):
    if skirmish_dice + assault_dice + raid_dice == 0:
        st.error("Please select at least one die to roll first!")
    elif (convert_intercepts is False and
          ((min_damage is not None and min_damage > 0) or
           (max_damage is not None and max_damage > 0))):
        st.error("Please select Convert Intercepts to use damage features!")
    else:
        try:
            macrostates, probs, *_ = \
                streamlit_funcs.cached_compute_probabilities(
                    skirmish_dice, assault_dice, raid_dice, fresh_targets,
                    convert_intercepts
                )
            # Use updated function with all min/max parameters
            st.success(arcs_funcs.parse_label_for_probability(
                macrostates, probs, min_hits, max_hits, min_damage,
                max_damage, min_keys, max_keys, min_building_hits,
                max_building_hits))
        except Exception as e:
            st.error(f"Error calculating probability: {str(e)}")

# Multi-roll summary display
if multi_roll_mode and st.session_state.rolls:
    st.subheader("Multi-Roll Configuration")
    st.warning("Note that this calculation does not attempt to compute effects"
               "from either the attacker or defending losing ships between "
               "rolls!")
    total_dice = 0
    for i, roll in enumerate(st.session_state.rolls):
        roll_total = roll['skirmish'] + roll['assault'] + roll['raid']
        if roll_total > 0:
            total_dice += roll_total
            st.markdown(
                f"**Roll {i+1}:** {roll['skirmish']} skirmish, "
                f"{roll['assault']} assault, {roll['raid']} raid dice")

    if total_dice > 0:
        st.info(f"**Total dice across all rolls:** {skirmish_dice} skirmish, "
                f"{assault_dice} assault, {raid_dice} raid")

# Interactive Dashboard Section
if skirmish_dice + assault_dice + raid_dice == 0:
    st.warning("Please select at least one die to roll!")
else:
    try:
        st.markdown("---")
        st.subheader("Probability Dashboard")
        st.markdown("Explore probability distributions and relationships "
                    "between different outcomes:")
        # Dashboard controls
        x_axis, y_axis = streamlit_funcs.get_dashboard_axes()

        # Generate dashboard
        streamlit_funcs.create_2D_and_marginal_plots(
            skirmish_dice,
            assault_dice,
            raid_dice,
            fresh_targets,
            convert_intercepts,
            x_axis,
            y_axis,
            theme_option,
            cumulative_plots
        )

        # Individual roll results (if in multi-roll mode)
        if multi_roll_mode and st.session_state.rolls:
            st.subheader("Individual Roll Outcomes")
            streamlit_funcs.show_probable_individual_rolls(
                st.session_state,
                fresh_targets,
                convert_intercepts,
                dice_images,
                theme_option
            )

        st.markdown("---")

        # Calculate probabilities
        if debugging_info:
            start_time = time.time()
        with st.spinner('Calculating probabilities...'):
            macrostates, probs, parse_time, coefficient_time, loop_count = \
                streamlit_funcs.cached_compute_probabilities(
                    skirmish_dice, assault_dice, raid_dice, fresh_targets,
                    convert_intercepts
                )

            if debugging_info:
                calc_time = time.time() - start_time
                st.write(f"Calculation took {calc_time:.2f} seconds")
                st.write(f"Parse time: {parse_time:.2f}s, Coefficient time: "
                         f"{coefficient_time:.2f}s")
                st.write(f"Loop iterations: {loop_count:,}")

        # Create two columns for layout
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Most Likely Outcomes")

            # Generate plot with timing
            if debugging_info:
                plot_start = time.time()
            with streamlit_funcs.temp_plot_file() as tmp_filename:
                arcs_funcs.plot_most_likely_states(
                    macrostates, probs, skirmish_dice, assault_dice, raid_dice,
                    fresh_targets, tmp_filename, convert_intercepts,
                    truncate_length, show_all_outcomes, theme_option
                )
                st.image(tmp_filename)
            if debugging_info:
                plot_time = time.time() - plot_start
                st.write(f"Plot generation took {plot_time:.2f} seconds")

        with col2:
            st.subheader("Summary")
            st.metric("Total Possible Outcomes", len(macrostates))

            if summary_table_truncate_length is None:
                summary_table_truncate_length = len(macrostates)

            if len(macrostates) > summary_table_truncate_length:
                st.info(f"Showing top {summary_table_truncate_length} most "
                        "likely outcomes")

            # Show top results in a nice table
            plot_states = (
                macrostates[-summary_table_truncate_length:]
                if not show_all_outcomes and
                len(macrostates) > summary_table_truncate_length
                else macrostates
            )
            plot_probs = (
                probs[-summary_table_truncate_length:]
                if not show_all_outcomes and
                len(probs) > summary_table_truncate_length
                else probs
            )

            st.subheader("Most Likely Results")

            # Calculate plot height to match left column
            ylength = (len(plot_states) if not show_all_outcomes
                       else len(macrostates))
            plot_height = max(4.8, 0.15 * ylength)
            container_height = int(plot_height * 37.8)  # Convert matplotlib
            # inches to pixels (roughly 37.8 px/inch)

            # Display results with images instead of table
            for i, (state, prob) in enumerate(
                    reversed(list(zip(plot_states, plot_probs)))):
                if i < summary_table_truncate_length:
                    # Create columns for each result
                    result_col1, result_col2 = st.columns([3, 1])

                    with result_col1:
                        # Use secure HTML generation
                        safe_html = streamlit_funcs.safe_dice_display_html(
                            state, dice_images, theme_option)
                        st.markdown(safe_html, unsafe_allow_html=True)

                    with result_col2:
                        st.markdown(f"**{prob:.4f}**")

                    if i < summary_table_truncate_length - 1:
                        # Don't add separator after last item
                        st.divider()

    except Exception as e:
        st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*Built with Streamlit for Arcs dice probability calculations*")

# Copyright information
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.8em;
     padding: 20px 0;'>
    <p>© 2025 Cody Messick. Licensed under the Mozilla Public License 2.0.</p>
    <p>Arcs is designed by Cole Wehrle, illustrated by Kyle Ferrin,
       and published by Leder Games.</p>
    <p>This calculator is an independent tool and is not affiliated
       with Leder Games.</p>
</div>
""", unsafe_allow_html=True)
