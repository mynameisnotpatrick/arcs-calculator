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
import tempfile
import os

st.set_page_config(
	page_title="Arcs Dice Calculator",
	page_icon="🎲",
	layout="wide"
)

st.title("Arcs Dice Calculator")
st.markdown("Calculate probabilities for Arcs dice rolls with interactive charts!")

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

# Auto-detect theme using Streamlit's native theme detection
try:
	theme_type = st.context.theme.type
	theme_option = "Dark" if theme_type == "dark" else "Light"
except:
	# Fallback to dark theme if detection fails
	theme_option = "Dark"

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

# Main content
if skirmish_dice + assault_dice + raid_dice == 0:
	st.warning("Please select at least one die to roll!")
else:
	try:
		# Calculate probabilities with detailed timing
		import time
		start_time = time.time()

		# Import what we need for profiling
		import itertools
		from collections import Counter

		loop_count = 0
		parse_time = 0
		coefficient_time = 0

		with st.spinner('Calculating probabilities...'):
			# Manual implementation with timing
			macrostates_set = set()
			macrostates_dict = {}
			total_states = 0

			for skirmish_combination in itertools.combinations_with_replacement(arcs_funcs.skirmish_dice, r=skirmish_dice):
				coeff_start = time.time()
				skirmish_coefficient = arcs_funcs.adjusted_multinomial_coefficient(skirmish_combination, 'skirmish')
				coefficient_time += time.time() - coeff_start

				for assault_combination in itertools.combinations_with_replacement(arcs_funcs.unique_assault_dice, r=assault_dice):
					coeff_start = time.time()
					assault_coefficient = arcs_funcs.adjusted_multinomial_coefficient(assault_combination, 'assault')
					coefficient_time += time.time() - coeff_start

					for raid_combination in itertools.combinations_with_replacement(arcs_funcs.unique_raid_dice, r=raid_dice):
						parse_start = time.time()
						combination = arcs_funcs.parse_dice({'skirmish': skirmish_combination, 'assault': assault_combination, 'raid': raid_combination}, fresh_targets, convert_intercepts=convert_intercepts)
						parse_time += time.time() - parse_start

						coeff_start = time.time()
						num_microstates = skirmish_coefficient * assault_coefficient * arcs_funcs.adjusted_multinomial_coefficient(raid_combination, 'raid')
						coefficient_time += time.time() - coeff_start

						if combination not in macrostates_set:
							macrostates_dict[combination] = 0
							macrostates_set.add(combination)
						macrostates_dict[combination] += num_microstates
						total_states += num_microstates
						loop_count += 1

			# Convert to the expected format
			sorted_macrostates = sorted(list(macrostates_dict.keys()), key = lambda k: macrostates_dict[k], reverse=False)
			sorted_probs = sorted([count / total_states for count in macrostates_dict.values()])
			macrostates, probs = sorted_macrostates, sorted_probs

		calc_time = time.time() - start_time
		st.write(f"Calculation took {calc_time:.2f} seconds")
		st.write(f"Parse time: {parse_time:.2f}s, Coefficient time: {coefficient_time:.2f}s")
		st.write(f"Loop iterations: {loop_count:,}")
		
		# Create two columns for layout
		col1, col2 = st.columns([2, 1])
		
		with col1:
			st.subheader("Probability Distribution")
			
			# Generate plot with timing
			plot_start = time.time()
			with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
				arcs_funcs.plot_most_likely_states(
					macrostates, probs, skirmish_dice, assault_dice, raid_dice,
					fresh_targets, tmp_file.name, convert_intercepts, truncate_length, show_full_plot
				)
				st.image(tmp_file.name)
				
				# Clean up temp file
				os.unlink(tmp_file.name)
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
		
		# Probability Calculator Section
		st.markdown("---")
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
			try:
				st.success(arcs_funcs.parse_label_for_probability(macrostates, probs, min_hits, max_damage, min_keys, min_building_hits, max_building_hits))
				
			except Exception as e:
				st.error(f"Error calculating probability: {str(e)}")
		
	except Exception as e:
		st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*Built with Streamlit for Arcs dice probability calculations*")
