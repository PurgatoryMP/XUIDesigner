import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFormLayout, QLabel,
    QGroupBox, QLineEdit, QComboBox, QCheckBox, QPushButton, QFileDialog,
    QMessageBox, QDialog
)
from registry import LLVIEW_PARAMS, LLUICTRL_PARAMS, XUI_REGISTRY


class AddAttributeDialog(QDialog):
    """Modal dialog for adding custom attributes to an XUI control."""

    def __init__(self, existing_keys, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Attribute")
        self.resize(340, 160)
        self.existing_keys = existing_keys

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., hover_color, min_val, tooltip...")
        form.addRow("Attribute Name:", self.name_edit)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("e.g., true, 1 1 1 1, 100...")
        form.addRow("Attribute Value:", self.value_edit)

        layout.addLayout(form)

        self.err_label = QLabel("")
        self.err_label.setStyleSheet("color: #FF0000; font-size: 11px;")
        layout.addWidget(self.err_label)

        btn_box = QHBoxLayout()
        add_btn = QPushButton("Add Attribute")
        add_btn.setStyleSheet("background-color: #1e457c; color: white; font-weight: bold; padding: 4px 12px;")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.validate_and_accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(add_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            self.err_label.setText("Attribute name cannot be empty.")
            return
        # Ensure standard XML attribute naming conventions
        if not name.replace("_", "").replace("-", "").replace(".", "").isalnum():
            self.err_label.setText("Invalid characters in attribute name.")
            return
        if name in self.existing_keys:
            self.err_label.setText("Attribute already exists on this control.")
            return
        self.accept()


class PropertyInspector(QWidget):
    property_changed_signal = Signal()
    external_file_import_needed = Signal(object, str)  # Emits (xui_item, filename)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_xui_item = None
        self.updating = False
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
        try:
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
        except Exception as e:
            print(f"[Verbose Error] PropertyInspector.refresh_values exception: {e}")
            self.updating = False

    def _is_image_attribute(self, attr_name):
        """Identifies SL control texture and image attributes."""
        attr_lower = attr_name.lower()
        image_keys = {
            "image", "image_unselected", "image_selected", "image_hover_unselected",
            "image_hover_selected", "image_disabled", "image_disabled_selected",
            "image_pressed", "image_pressed_selected", "image_overlay", "background_image",
            "bg_image", "bg_opaque_image", "chrome_image", "default_icon_name", "icon",
            "image_name", "image_bar", "image_fill", "thumb_image", "track_image",
            "up_button_image", "down_button_image", "left_button_image", "right_button_image",
            "floater_header", "floater_bg", "panel_bg"
        }
        return attr_lower in image_keys or attr_lower.startswith("image") or attr_lower.endswith(
            "_image") or "icon" in attr_lower

    def _rebuild_form(self):
        try:
            while self.main_form_layout.count():
                child = self.main_form_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    while child.layout().count():
                        sub = child.layout().takeAt(0)
                        if sub.widget(): sub.widget().deleteLater()
            self.editors.clear()

            if not self.current_xui_item:
                lbl = QLabel("<i>No item selected on canvas or tree.</i>")
                lbl.setAlignment(Qt.AlignCenter)
                self.main_form_layout.addWidget(lbl)
                return

            # --- TOP ACTION BAR: "+ Add Attribute" Button ---
            top_bar = QHBoxLayout()
            add_attr_btn = QPushButton("+ Add Attribute")
            add_attr_btn.setCursor(Qt.PointingHandCursor)
            add_attr_btn.setStyleSheet(
                "background-color: #1e457c; color: white; font-weight: bold; padding: 5px; border-radius: 3px;")
            add_attr_btn.setToolTip("Add a custom XML attribute to this control")
            add_attr_btn.clicked.connect(self._on_add_attribute_clicked)
            top_bar.addStretch()
            top_bar.addWidget(add_attr_btn)
            self.main_form_layout.addLayout(top_bar)

            tag_name = self.current_xui_item.tag_name
            target_params = {}
            for cat_name, widgets in XUI_REGISTRY.items():
                if tag_name in widgets:
                    target_params = dict(widgets[tag_name].get("params", {}))
                    break

            if not target_params:
                target_params = dict(LLUICTRL_PARAMS if tag_name != "view" else LLVIEW_PARAMS)

            if "filename" not in target_params:
                target_params["filename"] = {"type": "str", "default": "", "group": "External Import"}

            for attr_key in self.current_xui_item.attributes.keys():
                if attr_key not in target_params and attr_key != "designer_export_geometry":
                    target_params[attr_key] = {"type": "str", "default": "", "group": "Custom / Extra Attributes"}

            grouped = {}
            for attr_name, meta in target_params.items():
                group_name = meta.get("group", "General Properties")
                if group_name not in grouped:
                    grouped[group_name] = []
                grouped[group_name].append((attr_name, meta))

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
                        editor.toggled.connect(
                            lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))
                        self.editors[attr_name] = (editor, attr_type)
                        form_layout.addRow(QLabel(f"{attr_name}:"), editor)
                    elif attr_type == "combo":
                        editor = QComboBox()
                        editor.setEditable(True)
                        options = meta.get("options", [])
                        editor.addItems([str(o) for o in options])
                        editor.setCurrentText(str(current_val))
                        editor.currentTextChanged.connect(
                            lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))
                        self.editors[attr_name] = (editor, attr_type)
                        form_layout.addRow(QLabel(f"{attr_name}:"), editor)
                    else:
                        editor = QLineEdit(str(current_val))

                        # --- XML File Selector Button & Debounced Import Trigger ---
                        if attr_name == "filename":
                            editor.textChanged.connect(
                                lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))
                            # Trigger XML import only when typing is finished or browse is clicked
                            editor.editingFinished.connect(
                                lambda e=editor: self._trigger_filename_import(e.text().strip()))

                            btn = QPushButton("...")
                            btn.setFixedWidth(28)
                            btn.setToolTip("Select XML File to Import")
                            btn.setCursor(Qt.PointingHandCursor)
                            btn.clicked.connect(lambda _, e=editor: self._browse_xml_file(e))

                            container = QWidget()
                            h_box = QHBoxLayout(container)
                            h_box.setContentsMargins(0, 0, 0, 0)
                            h_box.addWidget(editor)
                            h_box.addWidget(btn)
                            self.editors[attr_name] = (editor, attr_type)
                            form_layout.addRow(QLabel(f"{attr_name}:"), container)
                        # --- Image / Texture File Selector Button ---
                        elif self._is_image_attribute(attr_name):
                            editor.textChanged.connect(
                                lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))
                            btn = QPushButton("...")
                            btn.setFixedWidth(28)
                            btn.setToolTip("Select Control Texture / Image File")
                            btn.setCursor(Qt.PointingHandCursor)
                            btn.clicked.connect(lambda _, e=editor: self._browse_image_file(e))

                            container = QWidget()
                            h_box = QHBoxLayout(container)
                            h_box.setContentsMargins(0, 0, 0, 0)
                            h_box.addWidget(editor)
                            h_box.addWidget(btn)
                            self.editors[attr_name] = (editor, attr_type)
                            form_layout.addRow(QLabel(f"{attr_name}:"), container)
                        else:
                            editor.textChanged.connect(
                                lambda val, k=attr_name, t=attr_type: self._on_property_edited(k, val, t))
                            self.editors[attr_name] = (editor, attr_type)
                            form_layout.addRow(QLabel(f"{attr_name}:"), editor)

                self.main_form_layout.addWidget(group_box)
        except Exception as e:
            print(f"[Verbose Error] PropertyInspector._rebuild_form exception: {e}")

    def _on_add_attribute_clicked(self):
        """Opens modal dialog to attach a new attribute to the selected control."""
        if not self.current_xui_item:
            return
        try:
            existing_keys = set(self.current_xui_item.attributes.keys())
            dlg = AddAttributeDialog(existing_keys, self)
            if dlg.exec() == QDialog.Accepted:
                new_key = dlg.name_edit.text().strip()
                new_val = dlg.value_edit.text().strip()

                self.current_xui_item.attributes[new_key] = new_val
                self._on_property_edited(new_key, new_val, "str")

                # If user manually added 'filename', trigger the XML import
                if new_key == "filename" and new_val:
                    self._trigger_filename_import(new_val)

                # Rebuild inspector form so the new attribute appears instantly
                self._rebuild_form()
        except Exception as e:
            QMessageBox.critical(self, "Add Attribute Error", f"Failed to add custom attribute:\n{str(e)}")
            print(f"[Verbose Error] _on_add_attribute_clicked exception: {e}")

    def _trigger_filename_import(self, filename_val):
        """Safely triggers external XML import signal."""
        if self.updating or not self.current_xui_item:
            return
        try:
            if filename_val and str(filename_val).strip():
                self.external_file_import_needed.emit(self.current_xui_item, str(filename_val).strip())
        except Exception as e:
            print(f"[Verbose Error] _trigger_filename_import exception: {e}")

    def _browse_xml_file(self, editor):
        try:
            start_dir = ""
            try:
                from config import get_xui_path
                start_dir = get_xui_path()
            except Exception as path_err:
                print(f"[Verbose Error] Could not resolve XUI path: {path_err}")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select XUI XML File to Import", start_dir, "XML Files (*.xml);;All Files (*)"
            )
            if file_path:
                rel_name = os.path.basename(file_path)
                editor.setText(rel_name)
                # Immediately trigger import upon selecting via browse button
                self._trigger_filename_import(rel_name)
        except Exception as e:
            QMessageBox.critical(self, "Error Selecting XML File",
                                 f"An error occurred while browsing for XML:\n{str(e)}")
            print(f"[Verbose Error] _browse_xml_file exception: {e}")

    def _browse_image_file(self, editor):
        try:
            start_dir = ""
            try:
                from config import get_textures_path
                start_dir = get_textures_path()
            except Exception as path_err:
                print(f"[Verbose Error] Could not resolve textures path: {path_err}")

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Control Texture / Image", start_dir,
                "Image Files (*.png *.tga *.jpg *.jpeg *.bmp *.j2k);;All Files (*)"
            )
            if file_path:
                stem_name = os.path.splitext(os.path.basename(file_path))[0]
                editor.setText(stem_name)
                try:
                    from textures import TextureManager
                    tm = TextureManager.get()
                    if tm and hasattr(tm, 'set_base_path'):
                        tm.set_base_path()
                except Exception as tex_err:
                    print(f"[Verbose Error] Live texture cache sync failed: {tex_err}")
        except Exception as e:
            QMessageBox.critical(self, "Error Selecting Image File",
                                 f"An error occurred while browsing for image:\n{str(e)}")
            print(f"[Verbose Error] _browse_image_file exception: {e}")

    def _on_property_edited(self, attr_name, value, attr_type):
        try:
            if self.updating or not self.current_xui_item:
                return

            self.updating = True
            val_str = "true" if (attr_type == "bool" and value) else ("false" if attr_type == "bool" else str(value))
            self.current_xui_item.attributes[attr_name] = val_str

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
                    if parent and hasattr(parent,
                                          'child_xui_items') and self.current_xui_item in parent.child_xui_items:
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
        except Exception as e:
            print(f"[Verbose Error] PropertyInspector._on_property_edited exception: {e}")
            self.updating = False