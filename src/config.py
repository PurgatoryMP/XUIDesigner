"""
This module handles loading and saving user configuration settings from a local
JSON file, providing default fallback values. It also supplies a suite of path
resolution functions that dynamically locate Second Life Viewer skins, textures,
and XUI XML layout directories, supporting asset inheritance from custom skins
down to the default viewer skin.
"""

import json
import os
from typing import Any, Dict, List

CONFIG_FILE = "config.json"

# Default configuration settings applied when config.json is missing or incomplete
DEFAULT_CONFIG: Dict[str, Any] = {
    "paths": {
        "sl_viewer_path": "C:/Program Files/SecondLifeViewer",
        "skin_name": "default",
    },
    "syntax_colors": {
        "header": "#808080",
        "tag": "#569CD6",
        "attribute": "#9CDCFE",
        "string": "#CE9178",
        "comment": "#6A9955",
        "error": "#FF0000",
        "warning": "#FFA500",
        "search_bg": "#FFFF00",
        "search_fg": "#000000",
    },
    "ui_colors": {
        "window_bg": "#2b2b2b",
        "window_text": "#d4d4d4",
        "canvas_bg": "#141414",
        "tree_bg": "#1e1e1e",
        "highlight": "#1e457c",
    },
}


def load_config() -> Dict[str, Any]:
    """Loads application configuration from disk and merges with default values.

    If the config file exists, it loads the JSON data and performs a one-level deep
    merge against DEFAULT_CONFIG. This ensures that any newly added configuration
    keys or color palettes in future updates are automatically populated without
    overwriting the user's existing settings.

    Returns:
        A dictionary containing the active application configuration.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # Merge missing top-level keys and nested dictionaries from defaults
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                    elif isinstance(v, dict):
                        data[k] = {**v, **data.get(k, {})}
                return data
        except Exception:
            # Fall back silently to defaults if the file is corrupted or unreadable
            pass
    return DEFAULT_CONFIG


def save_config(config_data: Dict[str, Any]) -> None:
    """Saves the provided configuration dictionary to the local JSON config file.

    Args:
        config_data: The configuration dictionary to serialize and write to disk.
    """
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")


# Initialize global configuration on module load
CONFIG: Dict[str, Any] = load_config()


def get_skin_path() -> str:
    """Resolves the primary directory path for the currently active skin.

    Checks standard Second Life Viewer directory structures (/skins/<skin_name>)
    as well as direct subdirectory placements.

    Returns:
        The absolute filesystem path to the active skin directory, or a default
        fallback string if resolution fails.
    """
    try:
        base = CONFIG.get("paths", {}).get(
            "sl_viewer_path", "C:/Program Files/SecondLifeViewer"
        )
        skin = CONFIG.get("paths", {}).get("skin_name", "default")

        # Check standard viewer structure: <viewer>/skins/<skin_name>
        skin_dir = os.path.join(base, "skins", skin)
        if os.path.exists(skin_dir):
            return skin_dir

        # Check non-standard layout: <viewer>/<skin_name>
        direct_dir = os.path.join(base, skin)
        if os.path.exists(direct_dir):
            return direct_dir

        return skin_dir
    except Exception as e:
        print(f"[Verbose Error] get_skin_path failed to resolve: {e}")
        return "C:/Program Files/SecondLifeViewer/skins/default"


def get_skin_paths() -> List[str]:
    """Retrieves an ordered list of skin directories for asset fallback inheritance.

    In Second Life Viewer theming, custom skins inherit missing UI assets and layouts
    from the 'default' skin. This function returns the default skin path first,
    followed by the active custom skin path (if applicable), ensuring asset search
    routines can scan fallback hierarchies cleanly.

    Returns:
        A list of valid directory paths to search for skin assets.
    """
    try:
        base = CONFIG.get("paths", {}).get(
            "sl_viewer_path", "C:/Program Files/SecondLifeViewer"
        )
        skin = CONFIG.get("paths", {}).get("skin_name", "default")

        paths = []

        # Always include the default skin as the primary fallback base
        default_dir = os.path.join(base, "skins", "default")
        if not os.path.exists(default_dir):
            default_alt = os.path.join(base, "default")
            if os.path.exists(default_alt):
                default_dir = default_alt
        if os.path.exists(default_dir):
            paths.append(default_dir)

        # Append custom skin directory if a non-default skin is active
        if skin.lower() != "default":
            active_dir = get_skin_path()
            if os.path.exists(active_dir) and active_dir not in paths:
                paths.append(active_dir)

        # Fallback to the viewer root directory if no valid skin folders exist
        if not paths:
            paths.append(base)

        return paths
    except Exception as e:
        print(f"[Verbose Error] get_skin_paths failed: {e}")
        return [base]


def get_textures_path() -> str:
    """Returns the primary texture asset directory for the active skin.

    Returns:
        The path to the '/textures' subdirectory of the active skin, or the root
        skin directory if the textures subfolder does not exist.
    """
    try:
        skin_dir = get_skin_path()
        tex_dir = os.path.join(skin_dir, "textures")
        return tex_dir if os.path.exists(tex_dir) else skin_dir
    except Exception as e:
        print(f"[Verbose Error] get_textures_path failed: {e}")
        return ""


def get_textures_paths() -> List[str]:
    """Retrieves an exhaustive list of all searchable texture directories across all fallback skins.

    Traverses the skin inheritance chain and recursively scans subdirectories within
    each skin's '/textures' folder (such as icon or window subfolders) so that the
    editor can locate UI images stored in nested categorizations.

    Returns:
        A list of all discovered texture directory paths.
    """
    try:
        skin_dirs = get_skin_paths()
        tex_paths = []
        for sdir in skin_dirs:
            tex_dir = os.path.join(sdir, "textures")
            if os.path.exists(tex_dir):
                tex_paths.append(tex_dir)
                # Recursively discover icon/window subdirectories within /textures/
                try:
                    for root, dirs, _ in os.walk(tex_dir):
                        for d in dirs:
                            sub_path = os.path.join(root, d)
                            if sub_path not in tex_paths:
                                tex_paths.append(sub_path)
                except Exception as walk_err:
                    print(
                        f"[Verbose Error] Failed scanning texture subfolders in '{tex_dir}': {walk_err}"
                    )
            else:
                if sdir not in tex_paths:
                    tex_paths.append(sdir)
        return tex_paths
    except Exception as e:
        print(f"[Verbose Error] get_textures_paths failed: {e}")
        return []


def get_xui_path() -> str:
    """Resolves the primary XML layout directory for the active skin.

    Checks standard localization subdirectories ('en', 'en-us', 'default') within
    the skin's '/xui' directory.

    Returns:
        The path to the active localized XUI directory, or a fallback root path.
    """
    skin_dir = get_skin_path()
    for lang in ["en", "en-us", "default"]:
        xdir = os.path.join(skin_dir, "xui", lang)
        if os.path.exists(xdir):
            return xdir
    xbase = os.path.join(skin_dir, "xui")
    return xbase if os.path.exists(xbase) else skin_dir


def get_xui_paths() -> List[str]:
    """Retrieves an ordered list of XUI layout directories across all fallback skins.

    Iterates through the skin fallback hierarchy and checks for localized layout
    subfolders ('en', 'en-us', 'default'), ensuring the parser can find base UI
    definitions when a custom skin only overrides specific XML files.

    Returns:
        A list of valid XUI directory paths to search for layout files.
    """
    skin_dirs = get_skin_paths()
    xui_paths = []
    for sdir in skin_dirs:
        found = False
        # Prioritize standard English and default language subfolders
        for lang in ["en", "en-us", "default"]:
            xdir = os.path.join(sdir, "xui", lang)
            if os.path.exists(xdir):
                xui_paths.append(xdir)
                found = True
                break
        # Fallback to unlocalized /xui directory or the skin root if language folders are missing
        if not found:
            xbase = os.path.join(sdir, "xui")
            if os.path.exists(xbase):
                xui_paths.append(xbase)
            else:
                xui_paths.append(sdir)
    return xui_paths