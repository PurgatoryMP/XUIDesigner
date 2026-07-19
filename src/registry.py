"""
This module defines standard Second Life Viewer UI control schemas (LLView and
LLUICtrl parameter sets) and maintains a global XUI_REGISTRY of available widgets.
It also provides a dynamic XML parser that scans Second Life Viewer installation
directories to discover and register custom or compound XML widgets at runtime.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict

from config import CONFIG, get_xui_path, get_xui_paths

# Base parameters common to all Second Life LLView elements
LLVIEW_PARAMS: Dict[str, Dict[str, Any]] = {
    "designer_export_geometry": {
        "type": "bool",
        "default": "true",
        "group": "Designer Tools",
    },
    "name": {"type": "str", "default": "unnamed", "group": "LLView (General)"},
    "enabled": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "visible": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "mouse_opaque": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "use_bounding_rect": {
        "type": "bool",
        "default": "false",
        "group": "LLView (General)",
    },
    "from_xui": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "focus_root": {"type": "bool", "default": "false", "group": "LLView (General)"},
    "tab_group": {"type": "int", "default": "0", "group": "LLView (General)"},
    "default_tab_group": {"type": "int", "default": "", "group": "LLView (General)"},
    "tool_tip": {"type": "str", "default": "", "group": "LLView (General)"},
    "sound_flags": {
        "type": "combo",
        "options": ["MOUSE_UP", "MOUSE_DOWN"],
        "default": "MOUSE_UP",
        "group": "LLView (General)",
    },
    "layout": {
        "type": "combo",
        "options": ["topleft", "topright", "bottomleft", "bottomright"],
        "default": "topleft",
        "group": "LLView (Layout)",
    },
    "follows": {"type": "str", "default": "left|top", "group": "LLView (Layout)"},
    "hover_cursor": {
        "type": "str",
        "default": "UI_CURSOR_ARROW",
        "group": "LLView (Cursor)",
    },
    "chrome": {"type": "bool", "default": "false", "group": "LLView (Advanced)"},
    "requests_front": {
        "type": "bool",
        "default": "false",
        "group": "LLView (Advanced)",
    },
    "controls_visibility": {
        "type": "str",
        "default": "none",
        "group": "LLView (Advanced)",
    },
    "enabled_controls": {
        "type": "str",
        "default": "none",
        "group": "LLView (Advanced)",
    },
}

# Extended parameters common to all interactive LLUICtrl widgets
LLUICTRL_PARAMS: Dict[str, Dict[str, Any]] = {
    **LLVIEW_PARAMS,
    "tab_stop": {"type": "bool", "default": "true", "group": "LLUICtrl"},
    "font": {
        "type": "combo",
        "options": ["SansSerif", "SansSerifSmall", "SansSerifLarge", "Monospace"],
        "default": "SansSerifSmall",
        "group": "LLUICtrl",
    },
    "halign": {
        "type": "combo",
        "options": ["left", "center", "right"],
        "default": "left",
        "group": "LLUICtrl",
    },
    "valign": {
        "type": "combo",
        "options": ["top", "vcenter", "bottom"],
        "default": "vcenter",
        "group": "LLUICtrl",
    },
    "initial_value": {"type": "str", "default": "", "group": "LLUICtrl"},
    "control_name": {"type": "str", "default": "", "group": "LLUICtrl"},
}

# Universal attributes applied as a baseline when registering unknown imported widgets
UNIVERSAL_ATTRIBUTES: Dict[str, Dict[str, Any]] = {**LLUICTRL_PARAMS}

# Master widget schema registry categorized for UI presentation in the editor
XUI_REGISTRY: Dict[str, Dict[str, Any]] = {
    "Containers & Windows": {
        "floater": {
            "width": 400,
            "height": 300,
            "label": "New Floater",
            "desc": "Standard floating window",
            "params": {
                **LLVIEW_PARAMS,
                "title": {"type": "str", "default": "Floater Title", "group": "Window"},
                "can_resize": {"type": "bool", "default": "true", "group": "Window"},
                "can_minimize": {"type": "bool", "default": "true", "group": "Window"},
                "can_close": {"type": "bool", "default": "true", "group": "Window"},
            },
        },
        "panel": {
            "width": 200,
            "height": 150,
            "label": "Panel",
            "desc": "Basic container panel",
            "params": {
                **LLVIEW_PARAMS,
                "border": {"type": "bool", "default": "false", "group": "Panel"},
                "bg_visible": {"type": "bool", "default": "false", "group": "Panel"},
                "bg_opaque_color": {
                    "type": "color",
                    "default": "0 0 0 0.5",
                    "group": "Panel",
                },
            },
        },
        "tab_container": {
            "width": 300,
            "height": 200,
            "label": "Tab Container",
            "desc": "Tabbed panel container",
            "params": {
                **LLVIEW_PARAMS,
                "tab_position": {
                    "type": "combo",
                    "options": ["top", "bottom", "left", "right"],
                    "default": "top",
                    "group": "Tabs",
                },
                "tab_height": {"type": "int", "default": "21", "group": "Tabs"},
                "tab_width": {"type": "int", "default": "80", "group": "Tabs"},
                "tab_min_width": {"type": "int", "default": "60", "group": "Tabs"},
                "tab_max_width": {"type": "int", "default": "150", "group": "Tabs"},
            },
        },
        "scroll_container": {
            "width": 250,
            "height": 200,
            "label": "Scroll Container",
            "desc": "Scrollable view area",
            "params": {
                **LLVIEW_PARAMS,
                "opaque": {"type": "bool", "default": "true", "group": "Scroll"},
                "reserve_scroll_corner": {
                    "type": "bool",
                    "default": "true",
                    "group": "Scroll",
                },
            },
        },
        "layout_stack": {
            "width": 300,
            "height": 100,
            "label": "Layout Stack",
            "desc": "Stack layout container",
            "params": {
                **LLVIEW_PARAMS,
                "orientation": {
                    "type": "combo",
                    "options": ["horizontal", "vertical"],
                    "default": "horizontal",
                    "group": "Layout",
                },
            },
        },
        "layout_panel": {
            "width": 100,
            "height": 100,
            "label": "Layout Panel",
            "desc": "Child panel for Layout Stack",
            "params": {
                **LLVIEW_PARAMS,
                "auto_resize": {"type": "bool", "default": "true", "group": "Layout"},
                "user_resize": {"type": "bool", "default": "false", "group": "Layout"},
            },
        },
    },
    "Basic Controls": {
        "button": {
            "width": 100,
            "height": 23,
            "label": "Button",
            "desc": "Standard clickable button",
            "params": {
                **LLUICTRL_PARAMS,
                "label": {"type": "str", "default": "Button", "group": "Button"},
                "image_unselected": {
                    "type": "str",
                    "default": "PushButton_Off",
                    "group": "Button Images",
                },
                "image_selected": {
                    "type": "str",
                    "default": "PushButton_Selected",
                    "group": "Button Images",
                },
                "image_hover_unselected": {
                    "type": "str",
                    "default": "PushButton_Over",
                    "group": "Button Images",
                },
            },
        },
        "check_box": {
            "width": 120,
            "height": 20,
            "label": "Check Box",
            "desc": "Toggle check box with label",
            "params": {
                **LLUICTRL_PARAMS,
                "label": {"type": "str", "default": "Check Box", "group": "CheckBox"},
                "image_unselected": {
                    "type": "str",
                    "default": "Checkbox_Off",
                    "group": "CheckBox Images",
                },
                "image_selected": {
                    "type": "str",
                    "default": "Checkbox_On",
                    "group": "CheckBox Images",
                },
            },
        },
        "radio_group": {
            "width": 150,
            "height": 80,
            "label": "Radio Group",
            "desc": "Container for radio buttons",
            "params": {
                **LLUICTRL_PARAMS,
                "draw_border": {
                    "type": "bool",
                    "default": "false",
                    "group": "Radio Group",
                },
            },
        },
        "radio_item": {
            "width": 100,
            "height": 20,
            "label": "Radio Item",
            "desc": "Single option in a radio group",
            "params": {
                **LLUICTRL_PARAMS,
                "label": {"type": "str", "default": "Radio Item", "group": "Radio Item"},
                "value": {"type": "str", "default": "", "group": "Radio Item"},
                "image_unselected": {
                    "type": "str",
                    "default": "RadioButton_Off",
                    "group": "Radio Images",
                },
                "image_selected": {
                    "type": "str",
                    "default": "RadioButton_On",
                    "group": "Radio Images",
                },
                "image_disabled": {
                    "type": "str",
                    "default": "RadioButton_Disabled",
                    "group": "Radio Images",
                },
                "image_disabled_selected": {
                    "type": "str",
                    "default": "RadioButton_On_Disabled",
                    "group": "Radio Images",
                },
            },
        },
        "combo_box": {
            "width": 130,
            "height": 20,
            "label": "Combo Box",
            "desc": "Drop-down selection menu",
            "params": {
                **LLUICTRL_PARAMS,
                "allow_text_entry": {
                    "type": "bool",
                    "default": "false",
                    "group": "Combo Box",
                },
                "max_chars": {"type": "int", "default": "20", "group": "Combo Box"},
            },
        },
        "combo_item": {
            "width": 120,
            "height": 20,
            "label": "Combo Item",
            "desc": "Item inside a Combo Box",
            "params": {
                **LLUICTRL_PARAMS,
                "label": {"type": "str", "default": "Item", "group": "Combo Item"},
                "value": {"type": "str", "default": "", "group": "Combo Item"},
            },
        },
        "line_editor": {
            "width": 150,
            "height": 20,
            "label": "Line Editor",
            "desc": "Single-line text input field",
            "params": {
                **LLUICTRL_PARAMS,
                "max_length_bytes": {
                    "type": "int",
                    "default": "254",
                    "group": "Text Input",
                },
                "select_on_focus": {
                    "type": "bool",
                    "default": "false",
                    "group": "Text Input",
                },
                "password": {"type": "bool", "default": "false", "group": "Text Input"},
            },
        },
        "text_editor": {
            "width": 200,
            "height": 100,
            "label": "Text Editor",
            "desc": "Multi-line rich text input",
            "params": {
                **LLUICTRL_PARAMS,
                "word_wrap": {"type": "bool", "default": "true", "group": "Text Editor"},
                "max_length_bytes": {
                    "type": "int",
                    "default": "65535",
                    "group": "Text Editor",
                },
                "show_line_numbers": {
                    "type": "bool",
                    "default": "false",
                    "group": "Text Editor",
                },
            },
        },
        "spinner": {
            "width": 80,
            "height": 20,
            "label": "Spinner",
            "desc": "Numeric input with up/down arrows",
            "params": {
                **LLUICTRL_PARAMS,
                "min_val": {"type": "float", "default": "0.0", "group": "Spinner"},
                "max_val": {"type": "float", "default": "100.0", "group": "Spinner"},
                "initial_val": {"type": "float", "default": "0.0", "group": "Spinner"},
                "increment": {"type": "float", "default": "1.0", "group": "Spinner"},
                "decimal_digits": {"type": "int", "default": "0", "group": "Spinner"},
            },
        },
        "slider": {
            "width": 150,
            "height": 20,
            "label": "Slider",
            "desc": "Horizontal sliding value selector",
            "params": {
                **LLUICTRL_PARAMS,
                "min_val": {"type": "float", "default": "0.0", "group": "Slider"},
                "max_val": {"type": "float", "default": "100.0", "group": "Slider"},
                "initial_val": {"type": "float", "default": "50.0", "group": "Slider"},
                "show_text": {"type": "bool", "default": "true", "group": "Slider"},
            },
        },
    },
    "Text & Display": {
        "text": {
            "width": 100,
            "height": 16,
            "label": "Text Label",
            "desc": "Static text display label",
            "params": {
                **LLUICTRL_PARAMS,
                "text_color": {
                    "type": "color",
                    "default": "1 1 1 1",
                    "group": "Text Display",
                },
                "wrap": {"type": "bool", "default": "false", "group": "Text Display"},
            },
        },
        "icon": {
            "width": 32,
            "height": 32,
            "label": "Icon",
            "desc": "Static graphic icon display",
            "params": {
                **LLVIEW_PARAMS,
                "image_name": {
                    "type": "str",
                    "default": "add_icon",
                    "group": "Icon Display",
                },
                "color": {
                    "type": "color",
                    "default": "1 1 1 1",
                    "group": "Icon Display",
                },
                "scale_image": {
                    "type": "bool",
                    "default": "true",
                    "group": "Icon Display",
                },
            },
        },
        "progress_bar": {
            "width": 150,
            "height": 15,
            "label": "Progress Bar",
            "desc": "Visual progress indicator",
            "params": {
                **LLVIEW_PARAMS,
                "image_bar": {
                    "type": "str",
                    "default": "ProgressBarSolid",
                    "group": "Progress",
                },
                "image_fill": {
                    "type": "str",
                    "default": "ProgressBarSolid",
                    "group": "Progress",
                },
            },
        },
    },
    "Imported Viewer Widgets": {},
}


# --- DYNAMIC WIDGET LOADER ---
def _register_xml_content(content: str, source_name: str = "Unknown") -> None:
    """Parses raw XML string content to discover and register unknown Second Life widgets.

    Extracts tag names, default dimensions, direct attributes, and compound sub-element
    attributes (such as `<radio_item.check_button>`), registering them directly into
    the global XUI_REGISTRY under 'Imported Viewer Widgets'.

    Args:
        content: The raw XML string content read from a layout or widget definition file.
        source_name: The originating filename used for debugging and registry descriptions.
    """
    try:
        # Strip XML declaration tags that could interfere with multi-root wrapping
        content = re.sub(r"<\?xml.*?\?>", "", content)
        root = ET.fromstring(f"<root>{content}</root>")

        # Build a fast lookup list of tags already defined in standard categories
        handled_tags = []
        for cat in XUI_REGISTRY.values():
            handled_tags.extend(cat.keys())

        for child in root:
            tag = child.tag
            if tag in handled_tags:
                continue

            width = int(child.attrib.get("width", 100))
            height = int(child.attrib.get("height", 20))

            params = UNIVERSAL_ATTRIBUTES.copy()
            default_attrs = {}

            # 1. Extract direct attributes declared on the root widget element
            for k, v in child.attrib.items():
                default_attrs[k] = v
                if k not in params:
                    params[k] = {
                        "type": "str",
                        "default": v,
                        "group": f"Imported ({tag})",
                    }

            # 2. Extract attributes from compound sub-elements (e.g., <radio_item.check_button>)
            for sub_el in child.iter():
                if sub_el is child:
                    continue

                # Resolve fallback label strings from sub-element text definitions
                if "label" in sub_el.attrib and "label" not in default_attrs:
                    default_attrs["label"] = sub_el.attrib["label"]
                elif (
                        sub_el.tag.endswith(".label_text")
                        and "name" in sub_el.attrib
                        and "label" not in default_attrs
                ):
                    default_attrs["label"] = sub_el.attrib["name"]
                elif (
                        sub_el.tag.endswith(".label_text")
                        and "initial_value" in sub_el.attrib
                        and "label" not in default_attrs
                ):
                    default_attrs["label"] = sub_el.attrib["initial_value"]

                for sub_k, sub_v in sub_el.attrib.items():
                    # Ignore physical layout attributes on sub-elements to prevent canvas distortion
                    if sub_k in (
                            "name",
                            "left",
                            "top",
                            "right",
                            "bottom",
                            "width",
                            "height",
                            "follows",
                    ):
                        continue

                    default_attrs[sub_k] = sub_v
                    if sub_k not in params:
                        # Derive clean property group titles from compound dot-notation tags
                        group_name = (
                            sub_el.tag.split(".")[-1].replace("_", " ").title()
                            if "." in sub_el.tag
                            else "Sub-Control"
                        )
                        params[sub_k] = {
                            "type": "str",
                            "default": sub_v,
                            "group": f"Imported ({group_name})",
                        }

            # Determine human-readable display label for the widget pallette
            default_label = default_attrs.get("label", tag)
            if (
                    default_label == tag
                    and "name" in default_attrs
                    and default_attrs["name"] != "unnamed"
            ):
                default_label = default_attrs["name"]

            # Register the discovered widget into the global schema dictionary
            XUI_REGISTRY["Imported Viewer Widgets"][tag] = {
                "width": width,
                "height": height,
                "label": default_label,
                "desc": f"Viewer Widget ({tag}) [{source_name}]",
                "params": params,
                "default_attributes": default_attrs,
            }
    except Exception:
        # Silently ignore XML syntax errors or malformed widget definitions during scanning
        pass


def reload_registry() -> None:
    """Clears and re-indexes all XUI widget schemas in skin inheritance order.

    Scans the Second Life Viewer directory hierarchy (default skin -> active custom skin),
    reading all `.xml` files within base XUI folders and `/widgets` subdirectories.
    If no external definitions are found, falls back to a local context file.
    """
    XUI_REGISTRY["Imported Viewer Widgets"].clear()

    xui_dirs = get_xui_paths()
    scan_dirs = []

    # Gather base language folders and their respective /widgets subdirectories
    for xdir in xui_dirs:
        if os.path.exists(xdir):
            scan_dirs.append(xdir)
            widgets_sub = os.path.join(xdir, "widgets")
            if os.path.exists(widgets_sub):
                scan_dirs.append(widgets_sub)

    # Scan and parse all discovered XML layout and widget files
    for folder in scan_dirs:
        if not os.path.exists(folder):
            continue
        for fname in os.listdir(folder):
            if fname.endswith(".xml"):
                full_p = os.path.join(folder, fname)
                try:
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                        _register_xml_content(f.read(), source_name=fname)
                except Exception:
                    pass

    # Fall back to a local bundled definition file if external scanning yielded nothing
    if not XUI_REGISTRY["Imported Viewer Widgets"]:
        combined_path = "combined_widgets_context.xml"
        if os.path.exists(combined_path):
            try:
                with open(combined_path, "r", encoding="utf-8", errors="ignore") as f:
                    _register_xml_content(
                        f.read(), source_name="combined_widgets_context.xml"
                    )
            except Exception:
                pass


# Execute once on initial startup to populate the registry before GUI creation
reload_registry()