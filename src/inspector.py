from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFormLayout, QLabel, QGroupBox, QLineEdit, QComboBox
from registry import UNIVERSAL_ATTRIBUTES, XUI_REGISTRY


class PropertyInspector(QWidget):
    property_changed_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_xui_item = None
        self.updating = False

        self.layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.form_layout = QFormLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

    def set_item(self, xui_item):
        self.current_xui_item = xui_item
        self._rebuild_form()

    def _get_item_schema(self, tag_name):
        """Looks up the specialized parameter schema for the selected widget tag."""
        for category, widgets in XUI_REGISTRY.items():
            if tag_name in widgets:
                return widgets[tag_name].get("params", UNIVERSAL_ATTRIBUTES)
        return UNIVERSAL_ATTRIBUTES

    def _rebuild_form(self):
        self.updating = True
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.current_xui_item:
            self.form_layout.addRow(QLabel("Select an element on canvas to edit attributes."))
            self.updating = False
            return

        attrs = self.current_xui_item.attributes
        schema = self._get_item_schema(self.current_xui_item.tag_name)

        # Group attributes logically based on Second Life inheritance schemas
        groups = {}
        for k, v in attrs.items():
            meta = schema.get(k, UNIVERSAL_ATTRIBUTES.get(k, {"group": "Custom Attributes", "type": "str"}))
            grp = meta.get("group", "Custom Attributes")
            if grp not in groups:
                groups[grp] = []
            groups[grp].append((k, v, meta))

        # Build collapsible form sections for each group (e.g., LLView, LLUICtrl, LLButton)
        for grp_name, items in sorted(groups.items()):
            grp_box = QGroupBox(grp_name)
            grp_layout = QFormLayout(grp_box)

            for key, val, meta in sorted(items, key=lambda x: x[0]):
                attr_type = meta.get("type", "str")

                if attr_type == "combo" and "options" in meta:
                    editor = QComboBox()
                    editor.addItems(meta["options"])
                    if str(val) in meta["options"]:
                        editor.setCurrentText(str(val))
                    else:
                        editor.setEditText(str(val))
                    editor.currentTextChanged.connect(lambda text, k=key: self._on_attr_changed(k, text))
                else:
                    editor = QLineEdit(str(val))
                    editor.textChanged.connect(lambda text, k=key: self._on_attr_changed(k, text))

                grp_layout.addRow(QLabel(key + ":"), editor)

            self.form_layout.addRow(grp_box)

        self.updating = False

    def _on_attr_changed(self, key, val_str):
        if self.updating or not self.current_xui_item:
            return
        self.current_xui_item.attributes[key] = val_str

        # Instantly update bounding boxes on the canvas if coordinate dimensions change
        if key in ["left", "top", "width", "height"]:
            try:
                if key == "left":
                    self.current_xui_item.setX(float(val_str))
                elif key == "top":
                    self.current_xui_item.setY(float(val_str))
                elif key in ["width", "height"]:
                    self.current_xui_item.sync_geometry_to_attributes()
                self.current_xui_item.scene().update()
            except ValueError:
                pass

        self.property_changed_signal.emit()
