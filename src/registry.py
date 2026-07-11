
LLVIEW_PARAMS = {
    # Designer Utilities
    "designer_export_geometry": {"type": "bool", "default": "true", "group": "Designer Tools"},

    # General & Lifecycle
    "name": {"type": "str", "default": "unnamed", "group": "LLView (General)"},
    "enabled": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "visible": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "mouse_opaque": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "use_bounding_rect": {"type": "bool", "default": "false", "group": "LLView (General)"},
    "from_xui": {"type": "bool", "default": "true", "group": "LLView (General)"},
    "focus_root": {"type": "bool", "default": "false", "group": "LLView (General)"},
    "tab_group": {"type": "int", "default": "0", "group": "LLView (General)"},
    "default_tab_group": {"type": "int", "default": "", "group": "LLView (General)"},
    "tool_tip": {"type": "str", "default": "", "group": "LLView (General)"},
    "sound_flags": {"type": "combo", "options": ["MOUSE_UP", "MOUSE_DOWN"], "default": "MOUSE_UP",
                    "group": "LLView (General)"},
    "hover_cursor": {"type": "str", "default": "UI_CURSOR_ARROW", "group": "LLView (General)"},

    # Layout & Positioning (LLRect / Relative / Follows)
    "layout": {"type": "combo", "options": ["topleft", "bottomleft"], "default": "topleft", "group": "LLView (Layout)"},
    "follows": {"type": "str", "default": "left|top", "group": "LLView (Layout)"},
    "left": {"type": "int", "default": "0", "group": "LLView (Rect Absolute)"},
    "top": {"type": "int", "default": "0", "group": "LLView (Rect Absolute)"},
    "right": {"type": "int", "default": "", "group": "LLView (Rect Absolute)"},
    "bottom": {"type": "int", "default": "", "group": "LLView (Rect Absolute)"},
    "width": {"type": "int", "default": "100", "group": "LLView (Rect Absolute)"},
    "height": {"type": "int", "default": "20", "group": "LLView (Rect Absolute)"},
    "left_pad": {"type": "int", "default": "", "group": "LLView (Rect Relative)"},
    "top_pad": {"type": "int", "default": "", "group": "LLView (Rect Relative)"},
    "left_delta": {"type": "int", "default": "", "group": "LLView (Rect Relative)"},
    "top_delta": {"type": "int", "default": "", "group": "LLView (Rect Relative)"},
    "bottom_delta": {"type": "int", "default": "", "group": "LLView (Rect Relative)"},
}

LLUICTRL_PARAMS = {
    **LLVIEW_PARAMS,
    "label": {"type": "str", "default": "", "group": "LLUICtrl"},
    "tab_stop": {"type": "bool", "default": "true", "group": "LLUICtrl"},
    "chrome": {"type": "bool", "default": "false", "group": "LLUICtrl"},
    "requests_front": {"type": "bool", "default": "false", "group": "LLUICtrl"},
    "value": {"type": "str", "default": "", "group": "LLUICtrl (Data Binding)"},
    "initial_value": {"type": "str", "default": "", "group": "LLUICtrl (Data Binding)"},
    "control_name": {"type": "str", "default": "", "group": "LLUICtrl (Data Binding)"},
    "enabled_controls": {"type": "combo", "options": ["none", "spec", "config", "prefs", "global", "all"],
                         "default": "none", "group": "LLUICtrl (Data Binding)"},
    "controls_visibility": {"type": "combo", "options": ["none", "spec", "config", "prefs", "global", "all"],
                            "default": "none", "group": "LLUICtrl (Data Binding)"},
    "font": {"type": "combo",
             "options": ["SansSerif", "SansSerifSmall", "SansSerifBig", "SansSerifHuge", "Monospace", "Cursive"],
             "default": "SansSerifSmall", "group": "LLUICtrl (Typography)"},
    "halign": {"type": "combo", "options": ["left", "center", "right"], "default": "left",
               "group": "LLUICtrl (Typography)"},
    "valign": {"type": "combo", "options": ["top", "center", "vcenter", "bottom", "baseline"], "default": "vcenter",
               "group": "LLUICtrl (Typography)"},
    "commit_callback": {"type": "str", "default": "", "group": "LLUICtrl (Callbacks)"},
    "init_callback": {"type": "str", "default": "", "group": "LLUICtrl (Callbacks)"},
    "validate_callback": {"type": "str", "default": "", "group": "LLUICtrl (Callbacks)"},
    "mouseenter_callback": {"type": "str", "default": "", "group": "LLUICtrl (Callbacks)"},
    "mouseleave_callback": {"type": "str", "default": "", "group": "LLUICtrl (Callbacks)"},
}

# BACKWARD COMPATIBILITY ALIAS: Prevents ImportError in inspector.py and graphics_item.py
UNIVERSAL_ATTRIBUTES = {**LLVIEW_PARAMS, **LLUICTRL_PARAMS}

XUI_REGISTRY = {
    "Containers & Windows": {
        "floater": {
            "width": 450, "height": 350, "color": "#222222", "desc": "Free-floating top-level window (LLFloater)",
            "params": {
                **LLVIEW_PARAMS,
                "title": {"type": "str", "default": "FLOATER", "group": "LLFloater"},
                "can_resize": {"type": "bool", "default": "false", "group": "LLFloater"},
                "save_rect": {"type": "bool", "default": "true", "group": "LLFloater"},
                "single_instance": {"type": "bool", "default": "true", "group": "LLFloater"},
                "legacy_header_height": {"type": "int", "default": "18", "group": "LLFloater"},
                "help_topic": {"type": "str", "default": "", "group": "LLFloater"},
            }
        },
        "multi_floater": {
            "width": 500, "height": 400, "color": "#1b2836",
            "desc": "Container managing multiple floaters via tabs (LLMultiFloater)",
            "params": {**LLVIEW_PARAMS}
        },
        "panel": {
            "width": 200, "height": 150, "color": "#2d2d2d", "desc": "Standard child container panel (LLPanel)",
            "params": {
                **LLUICTRL_PARAMS,
                "border": {"type": "bool", "default": "false", "group": "LLPanel"},
                "bg_opaque": {"type": "bool", "default": "false", "group": "LLPanel"},
                "bg_color": {"type": "str", "default": "Inspector_Background", "group": "LLPanel"},
            }
        },
        "layout_stack": {
            "width": 220, "height": 200, "color": "#3a3a3a", "desc": "Arranges layout panels linearly (LLLayoutStack)",
            "params": {
                **LLVIEW_PARAMS,
                "orientation": {"type": "combo", "options": ["horizontal", "vertical"], "default": "vertical",
                                "group": "LLLayoutStack"},
                "border": {"type": "bool", "default": "false", "group": "LLLayoutStack"},
            }
        },
        "layout_panel": {
            "width": 180, "height": 120, "color": "#333333",
            "desc": "Layout container embedded inside stacks (LLLayoutPanel)",
            "params": {
                **LLVIEW_PARAMS,
                "auto_resize": {"type": "bool", "default": "true", "group": "LLLayoutPanel"},
                "user_resize": {"type": "bool", "default": "false", "group": "LLLayoutPanel"},
            }
        },
        "tab_container": {
            "width": 250, "height": 180, "color": "#2a3540", "desc": "Tabbed panel switcher (LLTabContainer)",
            "params": {
                **LLUICTRL_PARAMS,
                "tab_position": {"type": "combo", "options": ["top", "bottom", "left"], "default": "top",
                                 "group": "LLTabContainer"},
                "tab_height": {"type": "int", "default": "21", "group": "LLTabContainer"},
                "tab_min_width": {"type": "int", "default": "60", "group": "LLTabContainer"},
                "tab_max_width": {"type": "int", "default": "150", "group": "LLTabContainer"},
            }
        },
        "accordion": {
            "width": 200, "height": 250, "color": "#282828",
            "desc": "Collapsible vertical accordion container (LLAccordionCtrl)",
            "params": {**LLVIEW_PARAMS}
        },
        "accordion_tab": {
            "width": 190, "height": 80, "color": "#323232",
            "desc": "Individual collapsible section inside accordion (LLAccordionCtrlTab)",
            "params": {
                **LLVIEW_PARAMS,
                "title": {"type": "str", "default": "Accordion Tab", "group": "LLAccordionCtrlTab"},
                "expanded": {"type": "bool", "default": "true", "group": "LLAccordionCtrlTab"},
            }
        },
    },
    "Buttons & Toggles": {
        "button": {
            "width": 90, "height": 22, "color": "#4e5d6c", "label": "Button",
            "desc": "Standard clickable button (LLButton)",
            "params": {
                **LLUICTRL_PARAMS,
                "label_selected": {"type": "str", "default": "", "group": "LLButton"},
                "image_unselected": {"type": "str", "default": "PushButton_Off", "group": "LLButton"},
                "image_selected": {"type": "str", "default": "PushButton_On", "group": "LLButton"},
                "image_pressed": {"type": "str", "default": "PushButton_Press", "group": "LLButton"},
                "is_toggle": {"type": "bool", "default": "false", "group": "LLButton"},
                "toggle": {"type": "bool", "default": "false", "group": "LLButton"},
                "pad_right": {"type": "int", "default": "4", "group": "LLButton"},
            }
        },
        "check_box": {
            "width": 120, "height": 16, "color": "#3b5249", "label": "Check Box",
            "desc": "Standard toggle checkbox (LLCheckBoxCtrl)",
            "params": {
                **LLUICTRL_PARAMS,
                "radio_style": {"type": "bool", "default": "false", "group": "LLCheckBoxCtrl"},
            }
        },
        "radio_group": {
            "width": 130, "height": 60, "color": "#4a4e69", "desc": "Mutual exclusion wrapper (LLRadioGroup)",
            "params": {**LLUICTRL_PARAMS}
        },
        "radio_item": {
            "width": 100, "height": 16, "color": "#5c677d", "label": "Radio Item",
            "desc": "Option item inside radio group (LLRadioCtrl)",
            "params": {
                **LLUICTRL_PARAMS,
                "value": {"type": "str", "default": "0", "group": "LLRadioCtrl"},
            }
        },
    },
    "Text & Editors": {
        "text": {
            "width": 100, "height": 16, "color": "transparent", "label": "Label Text",
            "desc": "Static text display (LLTextBox)",
            "params": {
                **LLUICTRL_PARAMS,
                "wrap": {"type": "bool", "default": "false", "group": "LLTextBox"},
                "text_color": {"type": "str", "default": "TextFgColor", "group": "LLTextBox"},
            }
        },
        "line_editor": {
            "width": 140, "height": 20, "color": "#1c1c1e",
            "desc": "Single-line string entry input field (LLLineEditor)",
            "params": {
                **LLUICTRL_PARAMS,
                "max_length_bytes": {"type": "int", "default": "255", "group": "LLLineEditor"},
                "password": {"type": "bool", "default": "false", "group": "LLLineEditor"},
                "border_style": {"type": "combo", "options": ["line", "texture"], "default": "line",
                                 "group": "LLLineEditor"},
            }
        },
        "text_editor": {
            "width": 200, "height": 100, "color": "#141416",
            "desc": "Multi-line text editor input canvas (LLTextEditor)",
            "params": {
                **LLUICTRL_PARAMS,
                "max_length": {"type": "int", "default": "65536", "group": "LLTextEditor"},
                "word_wrap": {"type": "bool", "default": "true", "group": "LLTextEditor"},
                "spellcheck": {"type": "bool", "default": "true", "group": "LLTextEditor"},
            }
        },
        "search_editor": {
            "width": 140, "height": 22, "color": "#202024",
            "desc": "Text entry field containing search glyphs (LLSearchEditor)",
            "params": {
                **LLUICTRL_PARAMS,
                "clear_button_visible": {"type": "bool", "default": "true", "group": "LLSearchEditor"},
            }
        },
    },
    "Selection & Numeric Controls": {
        "combo_box": {
            "width": 130, "height": 22, "color": "#2c3e50", "label": "Select Option",
            "desc": "Selectable dropdown box (LLComboBox)",
            "params": {
                **LLUICTRL_PARAMS,
                "allow_text_entry": {"type": "bool", "default": "false", "group": "LLComboBox"},
                "max_chars": {"type": "int", "default": "20", "group": "LLComboBox"},
            }
        },
        "slider": {
            "width": 150, "height": 18, "color": "#2f3e46", "label": "Slider",
            "desc": "Numeric value slider with label (LLSliderCtrl)",
            "params": {
                **LLUICTRL_PARAMS,
                "min_val": {"type": "str", "default": "0", "group": "LLSliderCtrl"},
                "max_val": {"type": "str", "default": "100", "group": "LLSliderCtrl"},
                "increment": {"type": "str", "default": "1", "group": "LLSliderCtrl"},
                "decimal_digits": {"type": "int", "default": "0", "group": "LLSliderCtrl"},
                "label_width": {"type": "int", "default": "80", "group": "LLSliderCtrl"},
            }
        },
        "spinner": {
            "width": 70, "height": 20, "color": "#64dfdf", "label": "0",
            "desc": "Numeric spinner box with up/down buttons (LLSpinCtrl)",
            "params": {
                **LLUICTRL_PARAMS,
                "min_val": {"type": "str", "default": "0", "group": "LLSpinCtrl"},
                "max_val": {"type": "str", "default": "100", "group": "LLSpinCtrl"},
                "decimal_digits": {"type": "int", "default": "0", "group": "LLSpinCtrl"},
                "label_width": {"type": "int", "default": "12", "group": "LLSpinCtrl"},
            }
        },
        "scroll_list": {
            "width": 160, "height": 120, "color": "#181818", "desc": "Selectable list box (LLScrollListCtrl)",
            "params": {
                **LLUICTRL_PARAMS,
                "multi_select": {"type": "bool", "default": "false", "group": "LLScrollListCtrl"},
                "draw_heading": {"type": "bool", "default": "false", "group": "LLScrollListCtrl"},
            }
        },
    },
    "Display & Indicators": {
        "icon": {
            "width": 32, "height": 32, "color": "#555555", "desc": "Static graphic glyph display (LLIconCtrl)",
            "params": {
                **LLUICTRL_PARAMS,
                "image_name": {"type": "str", "default": "Lock", "group": "LLIconCtrl"},
                "color": {"type": "str", "default": "1,1,1,1", "group": "LLIconCtrl"},
            }
        },
        "progress_bar": {
            "width": 150, "height": 16, "color": "#2a9d8f", "desc": "Linear progress fill gauge (LLProgressBar)",
            "params": {
                **LLVIEW_PARAMS,
                "image_bar": {"type": "str", "default": "ProgressBarSolid", "group": "LLProgressBar"},
            }
        },
        "view_border": {
            "width": 100, "height": 2, "color": "#555555", "desc": "Simple decorative separator line (LLViewBorder)",
            "params": {
                **LLVIEW_PARAMS,
                "bevel_style": {"type": "combo", "options": ["none", "in", "out", "bright"], "default": "in",
                                "group": "LLViewBorder"},
            }
        },
    }
}