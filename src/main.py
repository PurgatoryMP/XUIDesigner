import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from main_window import MainWindow
from config import CONFIG

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(CONFIG["ui_colors"]["window_bg"]))
    palette.setColor(QPalette.WindowText, QColor(CONFIG["ui_colors"]["window_text"]))
    palette.setColor(QPalette.Base, QColor(CONFIG["ui_colors"]["tree_bg"]))
    palette.setColor(QPalette.AlternateBase, QColor(CONFIG["ui_colors"]["window_bg"]))
    palette.setColor(QPalette.Text, QColor(CONFIG["ui_colors"]["window_text"]))
    palette.setColor(QPalette.Button, QColor(CONFIG["ui_colors"]["window_bg"]))
    palette.setColor(QPalette.ButtonText, QColor(CONFIG["ui_colors"]["window_text"]))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())