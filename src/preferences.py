"""User preferences dialog for the XUI Designer.

This module provides the PreferencesDialog class, a modal UI window that allows
users to configure Second Life Viewer installation paths, select active skins,
and customize syntax highlighting and interface color palettes. Changes are saved
to disk and applied live to the running application.
"""

import os
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config import CONFIG, get_textures_path, save_config
from registry import reload_registry
from textures import TextureManager


class PreferencesDialog(QDialog):
    """Modal dialog for editing application preferences and color themes.

    Provides a scrollable interface divided into Viewer/Skin paths, Syntax colors,
    and UI theme colors. Tracks live color modifications and synchronizes saved
    changes across global configuration dictionaries, asset managers, and the
    primary editor workspace.

    Attributes:
        picked_colors (dict[str, str]): Maps combined category/key strings to hex color codes.
        viewer_path_edit (QLineEdit): Text field containing the active SL Viewer installation path.
        skin_combo (QComboBox): Dropdown list of discovered or custom viewer skin names.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initializes the PreferencesDialog and constructs its scrollable form sections.

        Args:
            parent: The parent QWidget window, if any.
        """
        super().__init__(parent)
        self.setWindowTitle("XUI Designer Preferences")
        self.resize(520, 580)

        main_layout = QVBoxLayout(self)

        # Configure scrollable workspace to ensure usability on smaller screens
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Dictionary tracking modified hex values before commit
        self.picked_colors: dict[str, str] = {}

        # --- Section 1: Viewer & Skin Settings ---
        paths_group = QGroupBox("Second Life Viewer & Skin Settings")
        paths_layout = QFormLayout(paths_group)

        viewer_path = CONFIG.get("paths", {}).get(
            "sl_viewer_path", "C:/Program Files/SecondLifeViewer"
        )
        self.viewer_path_edit = QLineEdit(viewer_path)

        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_viewer_path)

        path_box = QHBoxLayout()
        path_box.addWidget(self.viewer_path_edit)
        path_box.addWidget(browse_btn)
        paths_layout.addRow("Viewer Installation Path:", path_box)

        # Unified skin selection dropdown; left editable to allow custom folder naming
        self.skin_combo = QComboBox()
        self.skin_combo.setEditable(True)
        self.populate_skins(viewer_path)

        current_skin = CONFIG.get("paths", {}).get("skin_name", "default")
        idx = self.skin_combo.findText(current_skin)
        if idx >= 0:
            self.skin_combo.setCurrentIndex(idx)
        else:
            self.skin_combo.setCurrentText(current_skin)

        # Automatically rescan skins if the user edits the viewer installation path
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

    def populate_skins(self, viewer_path: Optional[Any] = None) -> None:
        """Scans viewer installation or direct skin directories for available themes.

        Checks both standard Second Life directory structures (/skins/<skin_name>)
        and alternate layouts where the viewer path itself acts as the skin root.
        Ensures 'default' is always prioritized at the top of the dropdown list.

        Args:
            viewer_path: The filesystem path string to scan. If omitted or not a string,
                falls back to reading the contents of self.viewer_path_edit.
        """
        try:
            if not isinstance(viewer_path, str) or not viewer_path:
                viewer_path = self.viewer_path_edit.text().strip()

            current_selection = self.skin_combo.currentText()
            self.skin_combo.blockSignals(True)
            self.skin_combo.clear()
            skins_found = []

            # Check inside standard /skins/ subdirectory
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

            # Discover all valid subdirectories representing distinct skins
            if target_dir and os.path.exists(target_dir):
                for item in sorted(os.listdir(target_dir)):
                    full_p = os.path.join(target_dir, item)
                    if os.path.isdir(full_p) and not item.startswith('.'):
                        skins_found.append(item)

            # Ensure 'default' always exists and sits at index 0
            if "default" not in skins_found:
                skins_found.insert(0, "default")
            elif skins_found[0] != "default":
                skins_found.remove("default")
                skins_found.insert(0, "default")

            self.skin_combo.addItems(skins_found)

            # Restore previous selection state if valid
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

    def _make_color_picker(self, category: str, key: str, initial_hex: str) -> QWidget:
        """Constructs an interactive color picker button and hex display label.

        Args:
            category: The theme category name ('syntax' or 'ui').
            key: The specific configuration color key (e.g., 'header', 'window_bg').
            initial_hex: The starting hexadecimal color string (e.g., '#808080').

        Returns:
            A QWidget container holding the styled color button and text label.
        """
        full_key = f"{category}_{key}"
        self.picked_colors[full_key] = initial_hex

        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Button visually styled with the current hex color as its background
        btn = QPushButton()
        btn.setStyleSheet(
            f"background-color: {initial_hex}; border: 1px solid #777; border-radius: 3px;"
        )
        btn.setFixedSize(40, 22)
        btn.setCursor(Qt.PointingHandCursor)

        lbl = QLabel(initial_hex)
        lbl.setFixedWidth(65)

        def pick_color() -> None:
            """Opens a QColorDialog and updates visual styles upon color selection."""
            try:
                current_color = QColor(self.picked_colors[full_key])
                new_color = QColorDialog.getColor(
                    current_color, self, f"Select Color for {key.capitalize()}"
                )
                if new_color.isValid():
                    hex_val = new_color.name()
                    self.picked_colors[full_key] = hex_val
                    btn.setStyleSheet(
                        f"background-color: {hex_val}; border: 1px solid #777; border-radius: 3px;"
                    )
                    lbl.setText(hex_val)
            except Exception as e:
                print(f"[Verbose Error] Color picker exception: {e}")

        btn.clicked.connect(pick_color)
        h_layout.addWidget(btn)
        h_layout.addWidget(lbl)
        h_layout.addStretch()
        return container

    def _browse_viewer_path(self) -> None:
        """Launches a directory selection dialog to locate the SL Viewer folder."""
        try:
            dir_path = QFileDialog.getExistingDirectory(
                self,
                "Select Second Life Viewer Installation Directory",
                self.viewer_path_edit.text(),
            )
            if dir_path:
                self.viewer_path_edit.setText(dir_path)
        except Exception as e:
            print(f"[Verbose Error] _browse_viewer_path failed: {e}")

    def save_and_close(self) -> None:
        """Commits updated preferences to disk and applies changes live to the editor.

        Updates the global CONFIG dictionary, serializes to config.json, triggers
        schema and texture cache reloads, and pushes style updates to the MainWindow
        and active canvas scene without requiring an application restart.
        """
        try:
            if "paths" not in CONFIG:
                CONFIG["paths"] = {}

            # Save core directory and skin preferences
            CONFIG["paths"]["sl_viewer_path"] = self.viewer_path_edit.text().strip()
            CONFIG["paths"]["skin_name"] = self.skin_combo.currentText().strip() or "default"

            # Commit modified syntax highlighting colors
            for key in CONFIG.get("syntax_colors", {}):
                if f"syntax_{key}" in self.picked_colors:
                    CONFIG["syntax_colors"][key] = self.picked_colors[f"syntax_{key}"]

            # Commit modified interface colors
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

            # Push live UI updates to MainWindow and force canvas redraws
            parent_win = self.parent()
            if parent_win and hasattr(parent_win, "apply_live_preferences"):
                parent_win.apply_live_preferences()
            elif parent_win and hasattr(parent_win, "canvas") and parent_win.canvas:
                parent_win.canvas.scene.update()

            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Preferences Error", f"Failed to save preferences:\n{str(e)}"
            )
            print(f"[Verbose Error] save_and_close exception: {e}")