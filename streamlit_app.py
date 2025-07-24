# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

import streamlit as st
import arcs_funcs
import base64
import json
import tempfile
import time
import os

st.set_page_config(
	page_title="Arcs Dice Calculator",
	page_icon="images/sworn_guardians_avatar.png",
	layout="wide"
)

st.title("Arcs Dice Calculator")
st.markdown("Calculate probabilities for Arcs dice rolls with interactive charts! Arcs is designed by Cole Wehrle, illustrated by Kyle Ferrin, and published by Leder Games.")

# Sidebar for dice configuration
st.sidebar.header("Dice Configuration")

skirmish_dice = st.sidebar.slider("Skirmish Dice", min_value=0, max_value=6, value=0)
assault_dice = st.sidebar.slider("Assault Dice", min_value=0, max_value=6, value=2)
raid_dice = st.sidebar.slider("Raid Dice", min_value=0, max_value=6, value=0)

st.sidebar.header("Battle Configuration")
fresh_targets = st.sidebar.number_input("Fresh Target Ships", min_value=0, max_value=30, value=0)
convert_intercepts = st.sidebar.checkbox("Convert Intercepts to Damage", value=False)

st.sidebar.header("Display Options")
show_full_plot = st.sidebar.checkbox("Show Full Plot", value=False)
if not show_full_plot:
	truncate_length = st.sidebar.slider("Max Results to Show in Plot", min_value=10, max_value=100, value=20)
else:
	truncate_length = 50

summary_table_truncate_length = st.sidebar.slider("Max Results to Show in Summary Table", min_value=10, max_value=100, value=10)

debugging_info = st.sidebar.checkbox("Show Execution Timing (For Debugging)", value=False)

# Auto-detect theme using Streamlit's native theme detection
try:
	theme_type = st.context.theme.type
	theme_option = "Dark" if theme_type == "dark" else "Light"
except:
	# Fallback to dark theme if detection fails
	theme_option = "Dark"

# Cache probability calculations based on dice configuration
@st.cache_data
def cached_compute_probabilities(skirmish_dice, assault_dice, raid_dice, fresh_targets, convert_intercepts):
	return arcs_funcs.compute_probabilities(skirmish_dice, assault_dice, raid_dice, fresh_targets, convert_intercepts)

# Pre-load and cache all images at app startup
@st.cache_data
def load_dice_images():
	import base64
	def img_to_base64(image_path):
		try:
			with open(image_path, "rb") as img_file:
				return base64.b64encode(img_file.read()).decode()
		except:
			return None
	return {
		'dark': {
			'H': img_to_base64('images/hit_white.png'),
			'B': img_to_base64('images/hit_building_white.png'),
			'D': img_to_base64('images/hit_self_white.png'),
			'K': img_to_base64('images/key_white.png'),
			'I': img_to_base64('images/intercept_white.png')
		},
		'light': {
			'H': img_to_base64('images/hit_black.png'),
			'B': img_to_base64('images/hit_building_black.png'),
			'D': img_to_base64('images/hit_self_black.png'),
			'K': img_to_base64('images/key_black.png'),
			'I': img_to_base64('images/intercept_black.png')
		}
	}
# Load images once
dice_images = load_dice_images()

# Probability Calculator Section
st.subheader("Custom Probability Calculator")
st.markdown("Calculate the probability of specific outcomes:")

prob_col1, prob_col2, prob_col3 = st.columns(3)

with prob_col1:
	min_hits = st.number_input("Minimum Hits", min_value=0, value=None, placeholder="Any")
	max_damage = st.number_input("Maximum Damage to Self", min_value=0, value=None, placeholder="Any")

with prob_col2:
	min_keys = st.number_input("Minimum Keys", min_value=0, value=None, placeholder="Any")
	min_building_hits = st.number_input("Minimum Building Hits", min_value=0, value=None, placeholder="Any")

with prob_col3:
	max_building_hits = st.number_input("Maximum Building Hits", min_value=0, value=None, placeholder="Any")

if st.button("Calculate Custom Probability", type="primary"):
	if skirmish_dice + assault_dice + raid_dice == 0:
		st.error("Please select at least one die to roll first!")
	elif convert_intercepts is False:
		st.error("Please select Convert Intercepts to use this feature!")
	else:
		try:
			macrostates, probs, *_ = cached_compute_probabilities(
				skirmish_dice, assault_dice, raid_dice, fresh_targets, convert_intercepts
			)
			st.success(arcs_funcs.parse_label_for_probability(macrostates, probs, min_hits, max_damage, min_keys, min_building_hits, max_building_hits))
		except Exception as e:
			st.error(f"Error calculating probability: {str(e)}")

# Main content
if skirmish_dice + assault_dice + raid_dice == 0:
	st.warning("Please select at least one die to roll!")
else:
	try:
		# Interactive Dashboard Section
		st.markdown("---")
		st.subheader("Probability Dashboard")
		st.markdown("Explore probability distributions and relationships between different outcomes:")
		# Dashboard controls
		dash_col1, dash_col2 = st.columns(2)
		with dash_col1:
			x_axis = st.selectbox("X-axis variable:",
				options=['hits', 'damage', 'building hits', 'keys'],
				index=0,
				key="dashboard_x_axis")
		with dash_col2:
			y_axis = st.selectbox("Y-axis variable:",
				options=['hits', 'damage', 'building hits', 'keys'],
				index=1,
				key="dashboard_y_axis")
		# Generate dashboard
		try:
			# Get joint probability table
			df = arcs_funcs.get_joint_prob_table(
				skirmish_dice, assault_dice, raid_dice, fresh_targets, convert_intercepts
			)
			# Create dashboard layout
			heatmap_col, marginals_col = st.columns([5, 4])
			with heatmap_col:
				st.subheader(f"Probability Heatmap: {x_axis.title()} vs {y_axis.title()}")
				with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
					arcs_funcs.plot_heatmap(
						df, x_axis.replace(' ', '_'), y_axis.replace(' ', '_'), tmp_file.name, theme_option.lower()
					)
					st.image(tmp_file.name)
					os.unlink(tmp_file.name)
			with marginals_col:
				st.subheader("Marginal Distributions")
				variables = ['hits', 'damage', 'building_hits', 'keys']
				for var in variables:
					marginal = df.groupby(var)['prob'].sum().reset_index()
					if len(marginal) > 1:
						marg_col1, marg_col2 = st.columns([2, 1])
						with marg_col1:
							st.write(f"**{var.replace('_', ' ').title()} Distribution**")
							with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
								arcs_funcs.plot_marginal(
									df, var, tmp_file.name, theme_option.lower()
								)
								st.image(tmp_file.name)
								os.unlink(tmp_file.name)
						with marg_col2:
							st.write(f"**{var.replace('_', ' ').title()} Data**")
							# Sort marginal data by probability descending
							marginal_sorted = marginal.sort_values('prob', ascending=False)
							for _, row in marginal_sorted.iterrows():
								st.write(f"**{var.replace('_', ' ').title()}={row[var]}**: {row['prob']:.4f}")
		except Exception as e:
			st.error(f"Error generating dashboard: {str(e)}")

		st.markdown("---")

		# Calculate probabilities
		if debugging_info:
			start_time = time.time()
		with st.spinner('Calculating probabilities...'):
			macrostates, probs, parse_time, coefficient_time, loop_count = cached_compute_probabilities(
				skirmish_dice, assault_dice, raid_dice, fresh_targets, convert_intercepts
			)

			if debugging_info:
				calc_time = time.time() - start_time
				st.write(f"Calculation took {calc_time:.2f} seconds")
				st.write(f"Parse time: {parse_time:.2f}s, Coefficient time: {coefficient_time:.2f}s")
				st.write(f"Loop iterations: {loop_count:,}")
		
		# Create two columns for layout
		col1, col2 = st.columns([2, 1])
		
		with col1:
			st.subheader("Probability Distribution")

			# Generate plot with timing
			if debugging_info:
				plot_start = time.time()
			with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
				arcs_funcs.plot_most_likely_states(
					macrostates, probs, skirmish_dice, assault_dice, raid_dice,
					fresh_targets, tmp_file.name, convert_intercepts, truncate_length, show_full_plot, theme_option.lower()
				)
				st.image(tmp_file.name)
				
				# Clean up temp file
				os.unlink(tmp_file.name)
			if debugging_info:
				plot_time = time.time() - plot_start
				st.write(f"Plot generation took {plot_time:.2f} seconds")
		
		with col2:
			st.subheader("Summary")
			st.metric("Total Possible Outcomes", len(macrostates))
			
			if len(macrostates) > summary_table_truncate_length:
				st.info(f"Showing top {summary_table_truncate_length} most likely outcomes")
			
			# Show top results in a nice table
			plot_states = macrostates[-summary_table_truncate_length:] if not show_full_plot and len(macrostates) > summary_table_truncate_length else macrostates
			plot_probs = probs[-summary_table_truncate_length:] if not show_full_plot and len(probs) > summary_table_truncate_length else probs
			
			st.subheader("Most Likely Results")

			# Calculate plot height to match left column
			ylength = len(plot_states) if not show_full_plot else len(macrostates)
			plot_height = max(4.8, 0.15 * ylength)
			container_height = int(plot_height * 37.8)  # Convert matplotlib inches to pixels (roughly 37.8 px/inch)

			# Create scrollable container
			with st.container():
				st.markdown(f"""
				<div style="height: {container_height}px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 5px; padding: 10px;">
				""", unsafe_allow_html=True)

				# Display results with images instead of table
				for i, (state, prob) in enumerate(reversed(list(zip(plot_states, plot_probs)))):
					if i < summary_table_truncate_length:
						# Create columns for each result
						result_col1, result_col2 = st.columns([3, 1])

						with result_col1:
							# Use pre-cached images
							theme_key = theme_option.lower()
							current_images = dice_images[theme_key]
							html_content = "<div style='display: flex; align-items: center; gap: 2px;'>"
							for char in state:
								if char in current_images and current_images[char]:
									base64_img = current_images[char]
									html_content += f"<img src='data:image/png;base64,{base64_img}' width='15' style='margin: 0;'>"
								elif char.isalpha():
									# Fallback for missing images - show the letter
									html_content += f"<span style='font-weight: bold; margin: 0 2px; background-color: #ddd; padding: 2px; border-radius: 2px;'>{char}</span>"
								else:
									html_content += f"<span style='font-weight: bold; margin: 0 2px;'>{char}</span>"
							html_content += "</div>"
							st.markdown(html_content, unsafe_allow_html=True)

						with result_col2:
							st.markdown(f"**{prob:.4f}**")

						if i < summary_table_truncate_length - 1:  # Don't add separator after last item
							st.divider()

				st.markdown("</div>", unsafe_allow_html=True)
		
	except Exception as e:
		st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*Built with Streamlit for Arcs dice probability calculations*")
