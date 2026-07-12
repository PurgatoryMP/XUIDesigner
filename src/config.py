import json, os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
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
                    if k not in data: data[k] = v
                    else: data[k] = {**v, **data[k]}
                return data
        except Exception: pass
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

CONFIG = load_config()