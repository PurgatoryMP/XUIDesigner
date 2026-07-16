import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton,
    QHBoxLayout, QMessageBox, QColorDialog, QLabel, QWidget,
    QLineEdit, QFileDialog, QGroupBox, QScrollArea, QComboBox
)
from PySide6.QtGui import QColor
from config import CONFIG, save_config, get_textures_path
from src.registry import reload_registry


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XUI Designer Preferences")
        self.resize(500, 550)

        main_layout = QVBoxLayout(self)

        # Scroll area in case preferences grow large
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.picked_colors = {}

        paths_group = QGroupBox("Second Life Viewer & Skin Settings")
        paths_layout = QFormLayout(paths_group)

        # 1. Base Viewer Installation Path
        viewer_path = CONFIG.get("paths", {}).get("sl_viewer_path", "C:/Program Files/SecondLifeViewer")
        self.viewer_path_edit = QLineEdit(viewer_path)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_viewer_path)

        path_box = QHBoxLayout()
        path_box.addWidget(self.viewer_path_edit)
        path_box.addWidget(browse_btn)
        paths_layout.addRow("Viewer Installation Path:", path_box)

        # 2. Skin Selection Dropdown (Auto-scans /skins/ directory)
        self.skin_combo = QComboBox()
        self.skin_combo.setEditable(True)  # Allows manual entry if folder isn't created yet
        self._populate_skins(viewer_path)

        current_skin = CONFIG.get("paths", {}).get("skin_name", "default")
        self.skin_combo.setCurrentText(current_skin)

        # Auto-refresh available skin folders when installation path changes
        self.viewer_path_edit.textChanged.connect(self._populate_skins)
        paths_layout.addRow("Active Skin Folder:", self.skin_combo)

        scroll_layout.addWidget(paths_group)

        # --- Section 2: Syntax Colors ---
        syntax_group = QGroupBox("Syntax Highlighting Colors")
        syntax_layout = QFormLayout(syntax_group)
        for key, val in CONFIG["syntax_colors"].items():
            color_widget = self._make_color_picker("syntax", key, val)
            syntax_layout.addRow(f"{key.capitalize()}:", color_widget)
        scroll_layout.addWidget(syntax_group)

        # --- Section 3: UI Colors ---
        ui_group = QGroupBox("Interface Colors")
        ui_layout = QFormLayout(ui_group)
        for key, val in CONFIG["ui_colors"].items():
            color_widget = self._make_color_picker("ui", key, val)
            ui_layout.addRow(f"{key.replace('_', ' ').capitalize()}:", color_widget)
        scroll_layout.addWidget(ui_group)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # --- Bottom Action Buttons ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

    def _make_path_picker(self, key, initial_path):
        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)

        edit = QLineEdit(initial_path)
        self.picked_paths[key] = initial_path

        def on_text_changed(text):
            self.picked_paths[key] = text

        edit.textChanged.connect(on_text_changed)

        btn = QPushButton("Browse...")
        btn.setCursor(Qt.PointingHandCursor)

        def browse_folder():
            dir_path = QFileDialog.getExistingDirectory(
                self,
                f"Select Directory for {key.replace('_', ' ').title()}",
                edit.text()
            )
            if dir_path:
                edit.setText(dir_path)
                self.picked_paths[key] = dir_path

        btn.clicked.connect(browse_folder)

        h_layout.addWidget(edit)
        h_layout.addWidget(btn)
        return container

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
        lbl.setFixedWidth(60)

        def pick_color():
            current_color = QColor(self.picked_colors[full_key])
            new_color = QColorDialog.getColor(current_color, self, f"Select Color for {key.capitalize()}")

            if new_color.isValid():
                hex_val = new_color.name()
                self.picked_colors[full_key] = hex_val
                btn.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #777; border-radius: 3px;")
                lbl.setText(hex_val)

        btn.clicked.connect(pick_color)

        h_layout.addWidget(btn)
        h_layout.addWidget(lbl)
        h_layout.addStretch()

        return container

    def _browse_viewer_path(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Second Life Viewer Installation Directory", self.viewer_path_edit.text()
        )
        if dir_path:
            self.viewer_path_edit.setText(dir_path)

    def _populate_skins(self, base_path=None):
        if not base_path or isinstance(base_path, bool):
            base_path = self.viewer_path_edit.text()

        current = self.skin_combo.currentText()
        self.skin_combo.clear()

        skins_dir = os.path.join(base_path, "skins")
        if os.path.exists(skins_dir):
            try:
                subdirs = [
                    d for d in os.listdir(skins_dir)
                    if os.path.isdir(os.path.join(skins_dir, d))
                ]
                self.skin_combo.addItems(sorted(subdirs))
            except Exception:
                pass

        if self.skin_combo.count() == 0:
            self.skin_combo.addItem("default")

        idx = self.skin_combo.findText(current)
        if idx >= 0:
            self.skin_combo.setCurrentIndex(idx)
        else:
            self.skin_combo.setCurrentText(current or "default")

    def save_and_close(self):
        # Save Viewer Path and Active Skin
        if "paths" not in CONFIG:
            CONFIG["paths"] = {}

        CONFIG["paths"]["sl_viewer_path"] = self.viewer_path_edit.text().strip()
        CONFIG["paths"]["skin_name"] = self.skin_combo.currentText().strip() or "default"

        # Save syntax colors & UI colors
        for key in CONFIG["syntax_colors"]:
            if f"syntax_{key}" in self.picked_colors:
                CONFIG["syntax_colors"][key] = self.picked_colors[f"syntax_{key}"]

        for key in CONFIG["ui_colors"]:
            if f"ui_{key}" in self.picked_colors:
                CONFIG["ui_colors"][key] = self.picked_colors[f"ui_{key}"]

        save_config(CONFIG)

        # 1. Update Live Texture Index for the new skin
        from textures import TextureManager
        if TextureManager._instance:
            TextureManager._instance.set_base_path(get_textures_path())

        # 2. Reload XUI Schema definitions for the new skin
        reload_registry()

        # 3. Trigger Live Application UI Sync on MainWindow
        parent_win = self.parent()
        if parent_win and hasattr(parent_win, "apply_live_preferences"):
            parent_win.apply_live_preferences()

        # Close dialog smoothly without the restart warning popup
        self.accept()