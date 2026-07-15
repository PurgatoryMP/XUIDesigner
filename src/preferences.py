from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton,
    QHBoxLayout, QMessageBox, QColorDialog, QLabel, QWidget,
    QLineEdit, QFileDialog, QGroupBox, QScrollArea
)
from PySide6.QtGui import QColor
from config import CONFIG, save_config


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
        self.picked_paths = {}

        # --- Section 1: Second Life Paths ---
        paths_group = QGroupBox("Second Life Viewer Paths")
        paths_layout = QFormLayout(paths_group)
        for key, val in CONFIG.get("paths", {}).items():
            path_widget = self._make_path_picker(key, val)
            label_text = key.replace('_', ' ').title() + ":"
            paths_layout.addRow(label_text, path_widget)
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
        save_btn = QPushButton("Save && Restart")
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

    def save_and_close(self):
        # Save paths
        if "paths" not in CONFIG:
            CONFIG["paths"] = {}
        for key, val in self.picked_paths.items():
            CONFIG["paths"][key] = val

        # Save syntax colors
        for key in CONFIG["syntax_colors"]:
            CONFIG["syntax_colors"][key] = self.picked_colors[f"syntax_{key}"]

        # Save UI colors
        for key in CONFIG["ui_colors"]:
            CONFIG["ui_colors"][key] = self.picked_colors[f"ui_{key}"]

        save_config(CONFIG)

        QMessageBox.information(
            self,
            "Preferences Saved",
            "Preferences have been saved. Please restart the application if path or color changes do not take immediate effect."
        )
        self.accept()