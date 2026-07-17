import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton,
    QHBoxLayout, QMessageBox, QColorDialog, QLabel, QWidget,
    QLineEdit, QFileDialog, QGroupBox, QScrollArea, QComboBox
)
from PySide6.QtGui import QColor
from config import CONFIG, save_config, get_textures_path
from registry import reload_registry
from textures import TextureManager


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XUI Designer Preferences")
        self.resize(520, 580)

        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.picked_colors = {}

        # --- Section 1: Viewer & Skin Settings ---
        paths_group = QGroupBox("Second Life Viewer & Skin Settings")
        paths_layout = QFormLayout(paths_group)

        viewer_path = CONFIG.get("paths", {}).get("sl_viewer_path", "C:/Program Files/SecondLifeViewer")
        self.viewer_path_edit = QLineEdit(viewer_path)

        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_viewer_path)

        path_box = QHBoxLayout()
        path_box.addWidget(self.viewer_path_edit)
        path_box.addWidget(browse_btn)
        paths_layout.addRow("Viewer Installation Path:", path_box)

        # Single, unified Skin Selection Dropdown
        self.skin_combo = QComboBox()
        self.skin_combo.setEditable(True)  # Allow manual entry for new custom skins
        self.populate_skins(viewer_path)

        current_skin = CONFIG.get("paths", {}).get("skin_name", "default")
        idx = self.skin_combo.findText(current_skin)
        if idx >= 0:
            self.skin_combo.setCurrentIndex(idx)
        else:
            self.skin_combo.setCurrentText(current_skin)

        self.viewer_path_edit.textChanged.connect(self.populate_skins)
        paths_layout.addRow("Active Skin Folder:", self.skin_combo)
        scroll_layout.addWidget(paths_group)

        # --- Section 2: Syntax Colors ---
        syntax_group = QGroupBox("Syntax Highlighting Colors")
        syntax_layout = QFormLayout(syntax_group)
        for key, val in CONFIG.get("syntax_colors", {}).items():
            color_widget = self._make_color_picker("syntax", key, val)
            syntax_layout.addRow(f"{key.capitalize()}:", color_widget)
        scroll_layout.addWidget(syntax_group)

        # --- Section 3: UI Colors ---
        ui_group = QGroupBox("Interface Colors")
        ui_layout = QFormLayout(ui_group)
        for key, val in CONFIG.get("ui_colors", {}).items():
            color_widget = self._make_color_picker("ui", key, val)
            ui_layout.addRow(f"{key.replace('_', ' ').capitalize()}:", color_widget)
        scroll_layout.addWidget(ui_group)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # --- Bottom Action Buttons ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Preferences")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

    def populate_skins(self, viewer_path=None):
        """Scans viewer installation or direct skins directories for available skins."""
        try:
            if not isinstance(viewer_path, str) or not viewer_path:
                viewer_path = self.viewer_path_edit.text().strip()

            current_selection = self.skin_combo.currentText()
            self.skin_combo.blockSignals(True)
            self.skin_combo.clear()
            skins_found = []

            # Check inside /skins/ subdirectory
            skins_subdir = os.path.join(viewer_path, "skins")
            if os.path.exists(skins_subdir) and os.path.isdir(skins_subdir):
                target_dir = skins_subdir
            # Check if viewer_path itself is the /skins/ folder
            elif os.path.exists(viewer_path) and os.path.isdir(viewer_path):
                if os.path.exists(os.path.join(viewer_path, "default")):
                    target_dir = viewer_path
                else:
                    target_dir = None
            else:
                target_dir = None

            if target_dir and os.path.exists(target_dir):
                for item in sorted(os.listdir(target_dir)):
                    full_p = os.path.join(target_dir, item)
                    if os.path.isdir(full_p) and not item.startswith('.'):
                        skins_found.append(item)

            if "default" not in skins_found:
                skins_found.insert(0, "default")
            elif skins_found[0] != "default":
                skins_found.remove("default")
                skins_found.insert(0, "default")

            self.skin_combo.addItems(skins_found)

            idx = self.skin_combo.findText(current_selection)
            if idx >= 0:
                self.skin_combo.setCurrentIndex(idx)
            elif current_selection:
                self.skin_combo.setCurrentText(current_selection)
            else:
                self.skin_combo.setCurrentIndex(0)

            self.skin_combo.blockSignals(False)
        except Exception as e:
            print(f"[Verbose Error] Failed populating skin dropdown: {e}")
            self.skin_combo.blockSignals(False)
            if self.skin_combo.count() == 0:
                self.skin_combo.addItem("default")

    def _make_color_picker(self, category, key, initial_hex):
        full_key = f"{category}_{key}"
        self.picked_colors[full_key] = initial_hex

        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)

        btn = QPushButton()
        btn.setStyleSheet(f"background-color: {initial_hex}; border: 1px solid #777; border-radius: 3px;")
        btn.setFixedSize(40, 22)
        btn.setCursor(Qt.PointingHandCursor)

        lbl = QLabel(initial_hex)
        lbl.setFixedWidth(65)

        def pick_color():
            try:
                current_color = QColor(self.picked_colors[full_key])
                new_color = QColorDialog.getColor(current_color, self, f"Select Color for {key.capitalize()}")
                if new_color.isValid():
                    hex_val = new_color.name()
                    self.picked_colors[full_key] = hex_val
                    btn.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #777; border-radius: 3px;")
                    lbl.setText(hex_val)
            except Exception as e:
                print(f"[Verbose Error] Color picker exception: {e}")

        btn.clicked.connect(pick_color)
        h_layout.addWidget(btn)
        h_layout.addWidget(lbl)
        h_layout.addStretch()
        return container

    def _browse_viewer_path(self):
        try:
            dir_path = QFileDialog.getExistingDirectory(
                self, "Select Second Life Viewer Installation Directory", self.viewer_path_edit.text()
            )
            if dir_path:
                self.viewer_path_edit.setText(dir_path)
        except Exception as e:
            print(f"[Verbose Error] _browse_viewer_path failed: {e}")

    def save_and_close(self):
        try:
            if "paths" not in CONFIG:
                CONFIG["paths"] = {}

            CONFIG["paths"]["sl_viewer_path"] = self.viewer_path_edit.text().strip()
            CONFIG["paths"]["skin_name"] = self.skin_combo.currentText().strip() or "default"

            for key in CONFIG.get("syntax_colors", {}):
                if f"syntax_{key}" in self.picked_colors:
                    CONFIG["syntax_colors"][key] = self.picked_colors[f"syntax_{key}"]

            for key in CONFIG.get("ui_colors", {}):
                if f"ui_{key}" in self.picked_colors:
                    CONFIG["ui_colors"][key] = self.picked_colors[f"ui_{key}"]

            save_config(CONFIG)
            reload_registry()

            # Refresh TextureManager cache against new inheritance paths
            try:
                if TextureManager._instance:
                    TextureManager._instance.set_base_path()
            except Exception as tex_err:
                print(f"[Verbose Error] Failed refreshing TextureManager paths: {tex_err}")

            # Push live UI updates to MainWindow
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, "apply_live_preferences"):
                parent_win.apply_live_preferences()
            elif parent_win and hasattr(parent_win, "canvas") and parent_win.canvas:
                parent_win.canvas.scene.update()

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Preferences Error", f"Failed to save preferences:\n{str(e)}")
            print(f"[Verbose Error] save_and_close exception: {e}")