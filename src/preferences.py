# preferences.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton,
    QHBoxLayout, QMessageBox, QColorDialog, QLabel, QWidget
)
from PySide6.QtGui import QColor
from config import CONFIG, save_config


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XUI Designer Preferences")
        self.resize(400, 450)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.picked_colors = {}

        # Syntax Colors
        for key, val in CONFIG["syntax_colors"].items():
            color_widget = self._make_color_picker("syntax", key, val)
            form_layout.addRow(f"Syntax - {key.capitalize()}:", color_widget)

        # UI Colors
        for key, val in CONFIG["ui_colors"].items():
            color_widget = self._make_color_picker("ui", key, val)
            form_layout.addRow(f"UI - {key.replace('_', ' ').capitalize()}:", color_widget)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save && Restart")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _make_color_picker(self, section, key, initial_hex):
        """Creates a clickable color swatch and hex label pair."""
        full_key = f"{section}_{key}"
        self.picked_colors[full_key] = initial_hex

        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)

        # The interactive color swatch button
        btn = QPushButton()
        btn.setStyleSheet(f"background-color: {initial_hex}; border: 1px solid #777; border-radius: 3px;")
        btn.setFixedSize(40, 22)
        btn.setCursor(Qt.PointingHandCursor)

        # The hex code display label
        lbl = QLabel(initial_hex)
        lbl.setFixedWidth(60)

        def pick_color():
            current_color = QColor(self.picked_colors[full_key])
            # Open the native OS Color Picker Dialog
            new_color = QColorDialog.getColor(current_color, self, f"Select Color for {key.capitalize()}")

            if new_color.isValid():
                hex_val = new_color.name()  # Returns format #RRGGBB
                self.picked_colors[full_key] = hex_val
                btn.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #777; border-radius: 3px;")
                lbl.setText(hex_val)

        btn.clicked.connect(pick_color)

        h_layout.addWidget(btn)
        h_layout.addWidget(lbl)
        h_layout.addStretch()

        return container

    def save_and_close(self):
        # Save values back to the global CONFIG dictionary
        for key in CONFIG["syntax_colors"]:
            CONFIG["syntax_colors"][key] = self.picked_colors[f"syntax_{key}"]

        for key in CONFIG["ui_colors"]:
            CONFIG["ui_colors"][key] = self.picked_colors[f"ui_{key}"]

        save_config(CONFIG)
        QMessageBox.information(self, "Saved", "Preferences saved. Please restart the application to apply UI changes.")
        self.accept()