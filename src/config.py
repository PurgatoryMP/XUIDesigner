import json, os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "paths": {
        "sl_viewer_path": "C:/Program Files/SecondLifeViewer",
        "textures_path": "C:/Program Files/SecondLifeViewer/skins/default/textures",
        "xui_path": "C:/Program Files/SecondLifeViewer/skins/default/xui/en"
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