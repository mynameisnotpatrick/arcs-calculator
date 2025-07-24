# Interactivity won't work without an ipynb, but placed here for reference in case there are any old grumpy men using this repo

import arcs_funcs
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from ipywidgets import interact, IntSlider, Dropdown

variables = ['hits', 'damage', 'building_hits', 'keys']

def dashboard(skirmish_dice, assault_dice, raid_dice, xaxis, yaxis):
	# Compute full joint probability table
	df = arcs_funcs.get_joint_prob_table(
		skirmish_dice_count=skirmish_dice,
		assault_dice_count=assault_dice,
		raid_dice_count=raid_dice
	)

	# Prepare heatmap data
	pivot = df.pivot_table(index=yaxis, columns=xaxis, values='prob', aggfunc='sum', fill_value=0)
	x = pivot.columns
	y = pivot.index
	z = pivot.values

	# --- Figure and layout ---
	fig = plt.figure(figsize=(13, 11))
	gs = GridSpec(3, 4, figure=fig)  # 3 rows, 4 cols

	# Large heatmap (top, spans all 4 columns)
	ax_hm = fig.add_subplot(gs[0, :])
	cax = ax_hm.imshow(z, aspect='auto', origin='upper',
	                   cmap='viridis',
	                   extent=[x[0]-0.5, x[-1]+0.5, y[-1]+0.5, y[0]-0.5])
	for i in range(len(y)):
		for j in range(len(x)):
			ax_hm.text(x[j], y[i], f"{z[i, j]:.2f}", ha='center', va='center', color='w', fontsize=8)
	ax_hm.set_xticks(x)
	ax_hm.set_yticks(y)
	ax_hm.set_xlabel(xaxis.capitalize())
	ax_hm.set_ylabel(yaxis.capitalize())
	ax_hm.set_title(f"Probability Heatmap: {xaxis.capitalize()} vs {yaxis.capitalize()}")
	ax_hm.invert_yaxis()
	fig.colorbar(cax, ax=ax_hm, label='Probability', fraction=0.035, pad=0.03)

	# --- Marginals: 2nd and 3rd rows, 2 per row ---
	for idx, var in enumerate(variables):
		row = 1 + idx // 2
		col = idx % 2
		ax = fig.add_subplot(gs[row, col*2:(col+1)*2])
		marginal = df.groupby(var)['prob'].sum().reset_index()
		ax.bar(marginal[var], marginal['prob'])
		ax.set_xlabel(var.capitalize())
		ax.set_ylabel('Probability')
		ax.set_title(f'Probability Distribution: {var}')
		ax.set_xticks(marginal[var])

	fig.suptitle(
		f"Dice: Skirmish={skirmish_dice}, Assault={assault_dice}, Raid={raid_dice}",
		fontsize=15
	)
	plt.tight_layout(rect=[0, 0.04, 1, 0.96])
	plt.show()

# Interactive controls for dashboard
interact(
	dashboard,
	skirmish_dice=IntSlider(min=0, max=6, step=1, value=2, description='Skirmish'),
	assault_dice=IntSlider(min=0, max=6, step=1, value=2, description='Assault'),
	raid_dice=IntSlider(min=0, max=6, step=1, value=2, description='Raid'),
	xaxis=Dropdown(options=variables, value='hits', description='X Axis:'),
	yaxis=Dropdown(options=variables, value='damage', description='Y Axis:')
)
