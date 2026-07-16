import json, os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "paths": {
        "sl_viewer_path": "C:/Program Files/SecondLifeViewer",
        "skin_name": "default"
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
        "search_fg": "#000000"
    },
    "ui_colors": {
        "window_bg": "#2b2b2b",
        "window_text": "#d4d4d4",
        "canvas_bg": "#141414",
        "tree_bg": "#1e1e1e",
        "highlight": "#1e457c"
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                    elif isinstance(v, dict):
                        data[k] = {**v, **data.get(k, {})}
                return data
        except Exception:
            pass
    return DEFAULT_CONFIG

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

# Global configuration instance
CONFIG = load_config()


def get_skin_path():
    base = CONFIG.get("paths", {}).get("sl_viewer_path", "C:/Program Files/SecondLifeViewer")
    skin = CONFIG.get("paths", {}).get("skin_name", "default")

    # Resolves standard installation paths (e.g. C:/Program Files/SecondLifeViewer/skins/default)
    # or custom dev builds (e.g. .../indra/newview/skins/default)
    skin_dir = os.path.join(base, "skins", skin)
    if not os.path.exists(skin_dir) and os.path.exists(os.path.join(base, skin)):
        # Fallback if you point directly to a skins parent folder
        skin_dir = os.path.join(base, skin)
    return skin_dir


def get_textures_path():
    return os.path.join(get_skin_path(), "textures")


def get_xui_path():
    skin_p = get_skin_path()
    en_path = os.path.join(skin_p, "xui", "en")
    if os.path.exists(en_path):
        return en_path
    return os.path.join(skin_p, "xui")