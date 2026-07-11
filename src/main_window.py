# main_window.py
import xml.etree.ElementTree as ET
from PySide6.QtCore import Qt, QPointF, QMimeData
from PySide6.QtGui import QFont, QAction, QDrag
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPlainTextEdit, QFileDialog, QMessageBox, QWidget, QVBoxLayout, QLabel
)
from registry import XUI_REGISTRY
from textures import TextureManager
from graphics_item import XUIGraphicsItem
from canvas import CanvasContainer
from tree_widget import SceneTreeWidget
from inspector import PropertyInspector
from compiler import XUICompiler


class WidgetPaletteTree(QTreeWidget):
    """
    Subclass of QTreeWidget that explicitly packages the widget tag name
    as plain text MIME data so the canvas accepts drop events.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setHeaderLabel("XUI Widget Palette (Drag to Canvas)")

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item or item.childCount() > 0:  # Prevent dragging category folders
            return
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(item.text(0))
        drag.setMimeData(mime_data)
        drag.exec(Qt.CopyAction)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Second Life XUI Designer - Professional Edition")
        self.resize(1600, 950)

        self._setup_menus()
        self._setup_ui()

    def _setup_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        new_act = QAction("&New Layout", self)
        new_act.triggered.connect(self._new_layout)
        file_menu.addAction(new_act)

        open_act = QAction("&Open XUI File...", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_file)
        file_menu.addAction(open_act)

        save_act = QAction("&Save XUI File...", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._save_file)
        file_menu.addAction(save_act)

        file_menu.addSeparator()

        set_skin_act = QAction("Set Viewer Texture Folder...", self)
        set_skin_act.triggered.connect(self._set_texture_folder)
        file_menu.addAction(set_skin_act)

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(main_splitter)

        # 1. LEFT PANE: Widget Controls Palette (Unchanged)
        palette_tree = WidgetPaletteTree()
        for cat_name, widgets in XUI_REGISTRY.items():
            cat_item = QTreeWidgetItem(palette_tree, [cat_name])
            for w_name, w_meta in widgets.items():
                item = QTreeWidgetItem(cat_item, [w_name])
                item.setToolTip(0, w_meta.get("desc", w_name))
        palette_tree.expandAll()
        main_splitter.addWidget(palette_tree)

        # 2. CENTER PANE: Canvas Container (Top) + XML Source Editor (Bottom)
        center_splitter = QSplitter(Qt.Vertical)
        self.canvas = CanvasContainer()
        center_splitter.addWidget(self.canvas)

        code_container = QWidget()
        code_layout = QVBoxLayout(code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.addWidget(QLabel("<b>Live Second Life XML Source:</b>"))
        self.code_view = QPlainTextEdit()
        self.code_view.setFont(QFont("Consolas", 10))
        code_layout.addWidget(self.code_view)
        center_splitter.addWidget(code_container)

        center_splitter.setSizes([650, 300])
        main_splitter.addWidget(center_splitter)

        # 3. RIGHT PANE: XUI DOM Hierarchy / Context Menu (Top) + Property Attributes (Bottom)
        right_splitter = QSplitter(Qt.Vertical)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.addWidget(QLabel("<b>XUI DOM Hierarchy / Context Menu:</b>"))
        self.scene_tree = SceneTreeWidget()
        self.scene_tree.set_canvas(self.canvas)
        tree_layout.addWidget(self.scene_tree)
        right_splitter.addWidget(tree_container)

        inspector_container = QWidget()
        inspector_layout = QVBoxLayout(inspector_container)
        inspector_layout.setContentsMargins(0, 0, 0, 0)
        inspector_layout.addWidget(QLabel("<b>Widget Attributes & Parameters:</b>"))
        self.inspector = PropertyInspector()
        inspector_layout.addWidget(self.inspector)
        right_splitter.addWidget(inspector_container)

        right_splitter.setSizes([350, 600])
        main_splitter.addWidget(right_splitter)

        # Proportions for Left, Center, Right panes
        main_splitter.setSizes([250, 950, 400])

        # Signal Wiring
        self.canvas.item_selected_signal.connect(self.inspector.set_item)
        self.canvas.item_modified_signal.connect(self._refresh_code_view)
        self.inspector.property_changed_signal.connect(self._refresh_code_view)

    def _refresh_code_view(self, _ignored=None):
        xml_str = XUICompiler.generate_xml(self.canvas.root_container_instance)
        self.code_view.setPlainText(xml_str)

    def _new_layout(self):
        self.canvas.clear_canvas()
        self.scene_tree.clear()
        self.inspector.set_item(None)
        self.code_view.clear()

    def _set_texture_folder(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Viewer Textures Directory",
            TextureManager.get().base_path
        )
        if dir_path:
            TextureManager.get().set_base_path(dir_path)
            self.canvas.scene.update()

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open XUI XML File", "", "XML Files (*.xml);;All Files (*)")
        if not file_path:
            return

        try:
            tree = ET.parse(file_path)
            root_el = tree.getroot()
            self._new_layout()

            self._parse_xml_node(root_el, parent_item=None)
            self.scene_tree.refresh_tree()
            self._refresh_code_view()
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to parse XUI file:\n{str(e)}")

    def _parse_xml_node(self, element, parent_item=None, last_sibling_item=None):
        tag_name = element.tag

        if "." in tag_name:
            return None

        attributes = dict(element.attrib)
        width = int(attributes.get("width", 100))
        height = int(attributes.get("height", 20))

        left = 0
        top = 0

        if "left" in attributes:
            left = int(attributes["left"])
        elif "left_delta" in attributes and last_sibling_item:
            left = int(last_sibling_item.x()) + int(attributes["left_delta"])
        elif "left_pad" in attributes and last_sibling_item:
            left = int(last_sibling_item.x() + last_sibling_item.rect().width()) + int(attributes["left_pad"])
        elif "right" in attributes and parent_item:
            parent_w = parent_item.rect().width() if hasattr(parent_item, 'rect') else 500
            left = parent_w + int(attributes["right"]) - width

        if "top" in attributes:
            top = int(attributes["top"])
        elif "top_delta" in attributes and last_sibling_item:
            top = int(last_sibling_item.y()) + int(attributes["top_delta"])
        elif "top_pad" in attributes and last_sibling_item:
            top = int(last_sibling_item.y() + last_sibling_item.rect().height()) + int(attributes["top_pad"])
        elif "bottom" in attributes and parent_item:
            parent_h = parent_item.rect().height() if hasattr(parent_item, 'rect') else 500
            top = parent_h + int(attributes["bottom"]) - height

        attributes["left"] = str(left)
        attributes["top"] = str(top)
        attributes["width"] = str(width)
        attributes["height"] = str(height)

        item = XUIGraphicsItem(tag_name, attributes)
        item.setPos(QPointF(left, top))

        if parent_item and isinstance(parent_item, XUIGraphicsItem):
            parent_item.add_child_item(item)
        elif self.canvas.root_container_instance is None:
            self.canvas.root_container_instance = item
            self.canvas.scene.addItem(item)

        previous_child = None
        for child_el in element:
            created_child = self._parse_xml_node(child_el, parent_item=item, last_sibling_item=previous_child)
            if created_child:
                previous_child = created_child

        return item

    def _save_file(self):
        if not self.canvas.root_container_instance:
            QMessageBox.warning(self, "Warning", "No layout to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save XUI XML File", "layout.xml",
                                                   "XML Files (*.xml);;All Files (*)")
        if file_path:
            try:
                xml_content = XUICompiler.generate_xml(self.canvas.root_container_instance)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                QMessageBox.information(self, "Success", "XUI file saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")