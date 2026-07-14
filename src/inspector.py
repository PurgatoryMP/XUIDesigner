from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFormLayout, QLabel,
    QGroupBox, QLineEdit, QComboBox, QCheckBox
)
from registry import LLVIEW_PARAMS, LLUICTRL_PARAMS, XUI_REGISTRY


class PropertyInspector(QWidget):
    property_changed_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_xui_item = None
        self.updating = False

        # Caches active UI input fields to allow real-time canvas sync updates
        self.editors = {}

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.scroll_content = QWidget()
        self.main_form_layout = QVBoxLayout(self.scroll_content)
        self.main_form_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

    def set_item(self, xui_item):
        self.current_xui_item = xui_item
        self._rebuild_form()

    def refresh_values(self):
        """Silently updates field data in real-time without rebuilding the UI (prevents focus loss)."""
        if self.updating or not self.current_xui_item:
            return

        self.updating = True
        for key, (editor, attr_type) in self.editors.items():
            val = self.current_xui_item.attributes.get(key, "")
            if attr_type == "bool":
                editor.setChecked(str(val).lower() in ["true", "1", "yes"])
            elif attr_type == "combo":
                idx = editor.findText(str(val), Qt.MatchFixedString)
                if idx >= 0:
                    editor.setCurrentIndex(idx)
                else:
                    editor.setCurrentText(str(val))
            else:
                if editor.text() != str(val):
                    editor.setText(str(val))
        self.updating = False

    def _rebuild_form(self):
        # Clear existing layout widgets
        while self.main_form_layout.count():
            child = self.main_form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.editors.clear()

        if not self.current_xui_item:
            lbl = QLabel("<i>No item selected on canvas or tree.</i>")
            lbl.setAlignment(Qt.AlignCenter)
            self.main_form_layout.addWidget(lbl)
            return

        tag_name = self.current_xui_item.tag_name
        target_params = {}
        for cat_name, widgets in XUI_REGISTRY.items():
            if tag_name in widgets:
                target_params = dict(widgets[tag_name].get("params", {}))
                break

        if not target_params:
            target_params = dict(LLUICTRL_PARAMS if tag_name != "view" else LLVIEW_PARAMS)

        # --- GUARANTEE FILENAME AND IMPORTED ATTRIBUTES ALWAYS APPEAR ---
        if "filename" not in target_params:
            target_params["filename"] = {"type": "str", "default": "", "group": "External Import"}

        # Dynamic attribute capture: Ensure custom/unrecognized XML properties on this widget are never hidden
        for attr_key in self.current_xui_item.attributes.keys():
            if attr_key not in target_params and attr_key != "designer_export_geometry":
                target_params[attr_key] = {"type": "str", "default": "", "group": "Custom / Extra Attributes"}

        # Group parameters by category
        grouped = {}
        for attr_name, meta in target_params.items():
            group_name = meta.get("group", "General Properties")
            if group_name not in grouped:
                grouped[group_name] = []
            grouped[group_name].append((attr_name, meta))

        # Build group boxes and inputs
        for group_name, params in sorted(grouped.items()):
            group_box = QGroupBox(group_name)
            form_layout = QFormLayout(group_box)
            form_layout.setContentsMargins(8, 12, 8, 8)

            for attr_name, meta in sorted(params, key=lambda x: x[0]):
                attr_type = meta.get("type", "str")
                current_val = self.current_xui_item.attributes.get(attr_name, meta.get("default", ""))

                if attr_type == "bool":
                    editor = QCheckBox()
                    editor.setChecked(str(current_val).lower() in ["true", "1", "yes"])
                    editor.toggled.connect(lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))
                elif attr_type == "combo":
                    editor = QComboBox()
                    editor.setEditable(True)
                    options = meta.get("options", [])
                    editor.addItems([str(o) for o in options])
                    editor.setCurrentText(str(current_val))
                    editor.currentTextChanged.connect(
                        lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))
                else:
                    editor = QLineEdit(str(current_val))
                    editor.textChanged.connect(
                        lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))

                self.editors[attr_name] = (editor, attr_type)
                form_layout.addRow(QLabel(f"{attr_name}:"), editor)

            self.main_form_layout.addWidget(group_box)

    def _on_property_edited(self, attr_name, value, attr_type):
        if self.updating or not self.current_xui_item:
            return

        self.updating = True
        if attr_type == "bool":
            val_str = "true" if value else "false"
        else:
            val_str = str(value)

        self.current_xui_item.attributes[attr_name] = val_str

        # Apply geometry updates immediately when editing dimensions or coordinates
        try:
            if attr_name in ["width", "height"]:
                w = float(self.current_xui_item.attributes.get("width", 100))
                h = float(self.current_xui_item.attributes.get("height", 20))
                self.current_xui_item.resize_item(w, h)
            elif attr_name in ["left", "top"]:
                x = float(self.current_xui_item.attributes.get("left", 0))
                y = float(self.current_xui_item.attributes.get("top", 0))
                self.current_xui_item.setPos(x, y)
                self.current_xui_item.sync_attributes_to_geometry()
            elif attr_name in ["left_delta", "left_pad", "top_delta", "top_pad"]:
                parent = self.current_xui_item.parentItem()
                if parent and hasattr(parent, 'child_xui_items') and self.current_xui_item in parent.child_xui_items:
                    idx = parent.child_xui_items.index(self.current_xui_item)
                    prev_sib = parent.child_xui_items[idx - 1] if idx > 0 else None
                    if prev_sib:
                        if attr_name == "left_delta":
                            self.current_xui_item.setX(prev_sib.x() + float(val_str))
                        elif attr_name == "left_pad":
                            self.current_xui_item.setX(prev_sib.x() + prev_sib.rect().width() + float(val_str))
                        elif attr_name == "top_delta":
                            self.current_xui_item.setY(prev_sib.y() + float(val_str))
                        elif attr_name == "top_pad":
                            self.current_xui_item.setY(prev_sib.y() + prev_sib.rect().height() + float(val_str))
                        self.current_xui_item.sync_attributes_to_geometry()
        except ValueError:
            pass

        self.updating = False
        self.property_changed_signal.emit()

        if self.current_xui_item.scene() and hasattr(self.current_xui_item.scene(), 'canvas_container'):
            self.current_xui_item.scene().canvas_container.item_modified_signal.emit(self.current_xui_item)