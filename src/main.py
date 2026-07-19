"""
This script initializes the PySide6 application, sets up Windows-specific
taskbar icon identifiers, applies custom UI styling and color palettes
from configuration, and launches the main application window.
"""

import ctypes
import os
import sys

from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from config import CONFIG
from main_window import MainWindow
from textures import TextureManager


def set_app_user_model_id(app_id: str) -> None:
    """Sets the Windows Application User Model ID for taskbar grouping and icons.

    On Windows, Python scripts normally group under the default Python taskbar icon.
    Setting an explicit AppUserModelID forces Windows to recognize the application
    as a unique program and display its custom icon correctly.

    Args:
        app_id: An arbitrary unique string identifier for the application.
    """
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except AttributeError:
        # Silently ignore if not running on Windows or if ctypes/shell32 is unavailable
        pass


def setup_application_palette(app: QApplication) -> None:
    """Configures and applies the custom UI color palette to the application.

    Uses the Qt 'Fusion' style as a base and applies custom background, text,
    and highlight colors defined in the global CONFIG dictionary.

    Args:
        app: The active QApplication instance to style.
    """
    app.setStyle("Fusion")
    palette = QPalette()

    # Configure standard window and tree backgrounds/text
    palette.setColor(QPalette.Window, QColor(CONFIG["ui_colors"]["window_bg"]))
    palette.setColor(QPalette.WindowText, QColor(CONFIG["ui_colors"]["window_text"]))
    palette.setColor(QPalette.Base, QColor(CONFIG["ui_colors"]["tree_bg"]))
    palette.setColor(QPalette.AlternateBase, QColor(CONFIG["ui_colors"]["window_bg"]))
    palette.setColor(QPalette.Text, QColor(CONFIG["ui_colors"]["window_text"]))
    palette.setColor(QPalette.Button, QColor(CONFIG["ui_colors"]["window_bg"]))
    palette.setColor(QPalette.ButtonText, QColor(CONFIG["ui_colors"]["window_text"]))

    # Configure active selection and highlight colors
    highlight_color = QColor(CONFIG["ui_colors"]["highlight"])
    highlighted_text = QColor("#FFFFFF")
    palette.setColor(QPalette.Highlight, highlight_color)
    palette.setColor(QPalette.HighlightedText, highlighted_text)

    # Ensure highlights remain visible even when the widget loses focus (Inactive state)
    palette.setColor(QPalette.Inactive, QPalette.Highlight, highlight_color)
    palette.setColor(QPalette.Inactive, QPalette.HighlightedText, highlighted_text)

    app.setPalette(palette)


def main() -> None:
    """Initializes and executes the XUI Designer Editor application."""
    # Set Windows taskbar ID before initializing the GUI application
    myappid = 'SLXUI-Studio'  # Arbitrary unique string
    set_app_user_model_id(myappid)

    # Initialize the Qt Application
    app = QApplication(sys.argv)

    # Resolve application icon path relative to the project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(root_dir, "icon.ico")

    # Apply global application icon if found; otherwise warn the developer
    if not os.path.exists(icon_path):
        print(f"[Warning] Icon file not found at: {icon_path}")
    else:
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # Apply UI styling and color palette
    setup_application_palette(app)

    # Initialize global asset managers
    TextureManager()

    # Create and configure the main window
    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    # Display the window and start the Qt event loop
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()