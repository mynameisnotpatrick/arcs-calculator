# Copyright (C) 2025 Cody Messick
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

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

