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
    """Returns the primary active skin directory path, safely handling root or /skins installations."""
    try:
        base = CONFIG.get("paths", {}).get("sl_viewer_path", "C:/Program Files/SecondLifeViewer")
        skin = CONFIG.get("paths", {}).get("skin_name", "default")

        # Case 1: Standard root path (e.g., .../SecondLifeViewer -> .../SecondLifeViewer/skins/default)
        skin_dir = os.path.join(base, "skins", skin)
        if os.path.exists(skin_dir):
            return skin_dir

        # Case 2: User pointed directly at the 'skins' directory (e.g., .../skins -> .../skins/default)
        direct_dir = os.path.join(base, skin)
        if os.path.exists(direct_dir):
            return direct_dir

        return skin_dir
    except Exception as e:
        print(f"[Verbose Error] get_skin_path failed to resolve: {e}")
        return "C:/Program Files/SecondLifeViewer/skins/default"


def get_skin_paths():
    """Returns a list of skin directories in inheritance order: [default_skin_dir, active_skin_dir]."""
    try:
        base = CONFIG.get("paths", {}).get("sl_viewer_path", "C:/Program Files/SecondLifeViewer")
        skin = CONFIG.get("paths", {}).get("skin_name", "default")

        paths = []
        # 1. Resolve 'default' skin directory
        default_dir = os.path.join(base, "skins", "default")
        if not os.path.exists(default_dir):
            default_alt = os.path.join(base, "default")
            if os.path.exists(default_alt):
                default_dir = default_alt
        if os.path.exists(default_dir):
            paths.append(default_dir)

        # 2. Add active custom skin second (so its definitions override default in dictionaries/pixmaps)
        if skin.lower() != "default":
            active_dir = get_skin_path()
            if os.path.exists(active_dir) and active_dir not in paths:
                paths.append(active_dir)

        if not paths:
            paths.append(base)

        return paths
    except Exception as e:
        print(f"[Verbose Error] get_skin_paths failed: {e}")
        return [base]


def get_textures_path():
    """Returns the active texture path."""
    try:
        skin_dir = get_skin_path()
        tex_dir = os.path.join(skin_dir, "textures")
        return tex_dir if os.path.exists(tex_dir) else skin_dir
    except Exception as e:
        print(f"[Verbose Error] get_textures_path failed: {e}")
        return ""


def get_textures_paths():
    """Returns all texture directories to scan in inheritance order (default -> active), including subfolders."""
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
                    print(f"[Verbose Error] Failed scanning texture subfolders in '{tex_dir}': {walk_err}")
            else:
                if sdir not in tex_paths:
                    tex_paths.append(sdir)
        return tex_paths
    except Exception as e:
        print(f"[Verbose Error] get_textures_paths failed: {e}")
        return []


def get_xui_path():
    """Returns the active XUI directory path."""
    skin_dir = get_skin_path()
    for lang in ["en", "en-us", "default"]:
        xdir = os.path.join(skin_dir, "xui", lang)
        if os.path.exists(xdir):
            return xdir
    xbase = os.path.join(skin_dir, "xui")
    return xbase if os.path.exists(xbase) else skin_dir


def get_xui_paths():
    """Returns all XUI directories to scan in inheritance order (default -> active)."""
    skin_dirs = get_skin_paths()
    xui_paths = []
    for sdir in skin_dirs:
        found = False
        for lang in ["en", "en-us", "default"]:
            xdir = os.path.join(sdir, "xui", lang)
            if os.path.exists(xdir):
                xui_paths.append(xdir)
                found = True
                break
        if not found:
            xbase = os.path.join(sdir, "xui")
            if os.path.exists(xbase):
                xui_paths.append(xbase)
            else:
                xui_paths.append(sdir)
    return xui_paths