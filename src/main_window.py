import os
import xml.etree.ElementTree as ET
from PySide6.QtCore import Qt, QPointF, QMimeData, QTimer
from PySide6.QtGui import (
    QFont, QAction, QDrag, QTextDocument, QTextCursor, QTextFormat,
    QTextCharFormat, QColor, QBrush
)
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QTextEdit, QFileDialog, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTabWidget
)
from registry import XUI_REGISTRY
from textures import TextureManager
from graphics_item import XUIGraphicsItem
from canvas import CanvasContainer
from tree_widget import SceneTreeWidget
from inspector import PropertyInspector
from compiler import XUICompiler
from syntax_highlighter import XMLHighlighter
from preferences import PreferencesDialog
from config import CONFIG

# Define known SL non-visual configuration elements so they don't break visual sibling layout math
NON_VISUAL_TAGS = {
    "callback", "string", "key", "val", "value", "column", "item",
    "commit_callback", "mouse_down_callback", "mouse_up_callback",
    "on_enable", "on_disable", "on_click", "help", "doc", "menu_item"
}


class WidgetPaletteTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setHeaderLabel("XUI Widget Palette")

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item or item.childCount() > 0: return
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

        self.current_selected_item = None
        self.current_working_dir = ""
        self.tree_search_matches = []
        self.tree_search_idx = -1
        self._scroll_to_selection_pending = False

        self.code_editors = {}
        self.compiled_results = {}  # Caches XML structural validation so search doesn't wipe it

        # PERFORMANCE FIX: Debounce Timer for XML Compilation
        self.code_refresh_timer = QTimer()
        self.code_refresh_timer.setSingleShot(True)
        self.code_refresh_timer.setInterval(150)
        self.code_refresh_timer.timeout.connect(self._do_refresh_code_view)

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

        save_act = QAction("&Save All XML Files...", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._save_all_files)
        file_menu.addAction(save_act)

        file_menu.addSeparator()

        set_skin_act = QAction("Set Viewer Texture Folder...", self)
        set_skin_act.triggered.connect(self._set_texture_folder)
        file_menu.addAction(set_skin_act)

        edit_menu = menubar.addMenu("&Edit")
        pref_act = QAction("Preferences...", self)
        pref_act.triggered.connect(self._open_preferences)
        edit_menu.addAction(pref_act)

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(main_splitter)

        palette_tree = WidgetPaletteTree()
        for cat_name, widgets in XUI_REGISTRY.items():
            cat_item = QTreeWidgetItem(palette_tree, [cat_name])
            for w_name, w_meta in widgets.items():
                item = QTreeWidgetItem(cat_item, [w_name])
                item.setToolTip(0, w_meta.get("desc", w_name))
        palette_tree.expandAll()
        main_splitter.addWidget(palette_tree)

        center_splitter = QSplitter(Qt.Vertical)
        self.canvas = CanvasContainer()
        self.canvas.setBackgroundBrush(QBrush(QColor(CONFIG["ui_colors"]["canvas_bg"])))
        center_splitter.addWidget(self.canvas)

        code_container = QWidget()
        code_layout = QVBoxLayout(code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)

        xml_header_layout = QHBoxLayout()
        xml_header_layout.addWidget(QLabel("<b>Live Second Life XML Source:</b>"))
        xml_header_layout.addStretch()

        self.xml_search_input = QLineEdit()
        self.xml_search_input.setPlaceholderText("Find in active tab...")
        self.xml_search_input.setFixedWidth(150)
        self.xml_search_input.textChanged.connect(self._on_xml_search_changed)
        xml_header_layout.addWidget(self.xml_search_input)

        for text, slot in [("▲", self._xml_search_prev), ("▼", self._xml_search_next)]:
            btn = QPushButton(text)
            btn.setFixedWidth(30)
            btn.clicked.connect(slot)
            xml_header_layout.addWidget(btn)

        code_layout.addLayout(xml_header_layout)

        self.code_tabs = QTabWidget()
        code_layout.addWidget(self.code_tabs)

        center_splitter.addWidget(code_container)
        center_splitter.setSizes([650, 300])
        main_splitter.addWidget(center_splitter)

        right_splitter = QSplitter(Qt.Vertical)
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        tree_header_layout = QHBoxLayout()
        tree_header_layout.addWidget(QLabel("<b>XUI DOM Hierarchy:</b>"))
        tree_header_layout.addStretch()

        self.tree_search_input = QLineEdit()
        self.tree_search_input.setPlaceholderText("Find node...")
        self.tree_search_input.setFixedWidth(120)
        self.tree_search_input.textChanged.connect(self._on_tree_search_changed)
        tree_header_layout.addWidget(self.tree_search_input)

        for text, slot in [("▲", self._tree_search_prev), ("▼", self._tree_search_next)]:
            btn = QPushButton(text)
            btn.setFixedWidth(30)
            btn.clicked.connect(slot)
            tree_header_layout.addWidget(btn)

        tree_layout.addLayout(tree_header_layout)

        self.scene_tree = SceneTreeWidget()
        self.scene_tree.set_canvas(self.canvas)
        tree_layout.addWidget(self.scene_tree)
        right_splitter.addWidget(tree_container)

        inspector_container = QWidget()
        inspector_layout = QVBoxLayout(inspector_container)
        inspector_layout.setContentsMargins(0, 0, 0, 0)
        inspector_layout.addWidget(QLabel("<b>Widget Attributes:</b>"))
        self.inspector = PropertyInspector()
        inspector_layout.addWidget(self.inspector)
        right_splitter.addWidget(inspector_container)

        right_splitter.setSizes([350, 600])
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([250, 950, 400])

        # --- SIGNAL ROUTING ---
        self.canvas.item_selected_signal.connect(self._on_item_selected)
        self.canvas.item_modified_signal.connect(self._on_canvas_item_modified)
        self.inspector.property_changed_signal.connect(self._queue_refresh)
        self.scene_tree.tree_refreshed.connect(self._reapply_tree_search)

    def _open_preferences(self):
        dlg = PreferencesDialog(self)
        dlg.exec()

    def _on_canvas_item_modified(self, item):
        self._queue_refresh()
        if item and item == self.current_selected_item:
            self.inspector.refresh_values()

    # --- XML SEARCH LOGIC ---
    def _get_active_editor(self):
        return self.code_tabs.currentWidget()

    def _on_xml_search_changed(self, text):
        self._apply_extra_selections()
        self._xml_search_next()

    def _xml_search_next(self):
        text = self.xml_search_input.text()
        editor = self._get_active_editor()
        if not text or not editor: return
        if not editor.find(text):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            editor.setTextCursor(cursor)
            editor.find(text)

    def _xml_search_prev(self):
        text = self.xml_search_input.text()
        editor = self._get_active_editor()
        if not text or not editor: return
        options = QTextDocument.FindBackward
        if not editor.find(text, options):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            editor.setTextCursor(cursor)
            editor.find(text, options)

    # --- TREE SEARCH LOGIC ---
    def _on_tree_search_changed(self, text):
        self.tree_search_matches = []
        self.tree_search_idx = -1
        it = QTreeWidgetItemIterator(self.scene_tree)
        while it.value():
            item = it.value()
            item.setBackground(0, QBrush())
            xui_item = item.data(0, Qt.UserRole)

            fg_color = QColor("#00FF00") if xui_item and getattr(xui_item, 'is_imported_root', False) else QColor(
                CONFIG["ui_colors"]["window_text"])
            item.setForeground(0, QBrush(fg_color))

            if text and text.lower() in item.text(0).lower():
                item.setBackground(0, QBrush(QColor(CONFIG["syntax_colors"]["search_bg"])))
                item.setForeground(0, QBrush(QColor(CONFIG["syntax_colors"]["search_fg"])))
                self.tree_search_matches.append(item)
            it += 1
        if self.tree_search_matches: self._tree_search_next()

    def _reapply_tree_search(self):
        if self.tree_search_input.text(): self._on_tree_search_changed(self.tree_search_input.text())

    def _tree_search_next(self):
        if not self.tree_search_matches: return
        self.tree_search_idx = (self.tree_search_idx + 1) % len(self.tree_search_matches)
        self.scene_tree.setCurrentItem(self.tree_search_matches[self.tree_search_idx])

    def _tree_search_prev(self):
        if not self.tree_search_matches: return
        self.tree_search_idx = (self.tree_search_idx - 1) % len(self.tree_search_matches)
        self.scene_tree.setCurrentItem(self.tree_search_matches[self.tree_search_idx])

    # --- CORE REFRESH & TAB LOGIC ---
    def _on_item_selected(self, item):
        self.current_selected_item = item
        self.inspector.set_item(item)
        if item:
            fname = getattr(item, 'source_file', 'layout.xml')
            for i in range(self.code_tabs.count()):
                if self.code_tabs.tabText(i) == fname:
                    self.code_tabs.setCurrentIndex(i)
                    break
        # Flag that a purposeful selection happened, requesting an editor scroll adjustment
        self._scroll_to_selection_pending = True
        self._queue_refresh()

    def _queue_refresh(self, _ignored=None):
        self.code_refresh_timer.start()

    def _do_refresh_code_view(self):
        if not self.canvas.root_container_instance:
            self.code_tabs.clear()
            self.code_editors.clear()
            self.compiled_results.clear()
            return

        self.compiled_results = XUICompiler.generate_source(self.canvas.root_container_instance,
                                                            self.current_selected_item)

        # Remove stale tabs
        for fname in list(self.code_editors.keys()):
            if fname not in self.compiled_results:
                editor = self.code_editors.pop(fname)
                idx = self.code_tabs.indexOf(editor)
                self.code_tabs.removeTab(idx)
                editor.deleteLater()

        # Update text editors
        for fname, (xml_str, selections) in self.compiled_results.items():
            if fname not in self.code_editors:
                editor = QTextEdit()
                editor.setFont(QFont("Consolas", 10))
                editor.setReadOnly(True)
                editor.setStyleSheet(
                    f"background-color: {CONFIG['ui_colors']['tree_bg']}; color: {CONFIG['ui_colors']['window_text']};")
                XMLHighlighter(editor.document())
                self.code_tabs.addTab(editor, fname)
                self.code_editors[fname] = editor

            editor = self.code_editors[fname]
            scroll_pos = editor.verticalScrollBar().value()
            editor.setPlainText(xml_str)
            editor.verticalScrollBar().setValue(scroll_pos)

        self._apply_extra_selections()

    def _apply_extra_selections(self):
        """Applies syntax highlights and active search matches to the editors instantly without recompiling."""
        for fname, editor in self.code_editors.items():
            if fname not in self.compiled_results: continue

            selections = self.compiled_results[fname][1]
            extra_selections = []
            doc = editor.document()
            first_selected_cursor = None

            def add_selection(start_line, end_line, fmt):
                start_block = doc.findBlockByNumber(start_line)
                end_block = doc.findBlockByNumber(end_line)
                cursor = QTextCursor(start_block)
                if end_line > start_line:
                    cursor.setPosition(end_block.position() + end_block.length() - 1, QTextCursor.KeepAnchor)
                else:
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cursor
                sel.format = fmt
                extra_selections.append(sel)
                return cursor

            sel_fmt = QTextCharFormat()
            sel_fmt.setBackground(QColor(CONFIG["ui_colors"]["highlight"]))
            sel_fmt.setProperty(QTextFormat.FullWidthSelection, True)
            for start, end in selections['selected']:
                add_selection(start, end, sel_fmt)
                if first_selected_cursor is None:
                    # Generate a tracking cursor situated at the start of the targeted layout element block
                    first_selected_cursor = QTextCursor(doc.findBlockByNumber(start))

            err_fmt = QTextCharFormat()
            err_fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            err_fmt.setUnderlineColor(QColor(CONFIG["syntax_colors"]["error"]))
            for start, end, msgs in selections['errors']: add_selection(start, end, err_fmt)

            warn_fmt = QTextCharFormat()
            warn_fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            warn_fmt.setUnderlineColor(QColor(CONFIG["syntax_colors"]["warning"]))
            for start, end, msgs in selections['warnings']: add_selection(start, end, warn_fmt)

            search_text = self.xml_search_input.text()
            if search_text and self.code_tabs.currentWidget() == editor:
                search_fmt = QTextCharFormat()
                search_fmt.setBackground(QColor(CONFIG["syntax_colors"]["search_bg"]))
                search_fmt.setForeground(QColor(CONFIG["syntax_colors"]["search_fg"]))
                cursor = QTextCursor(doc)
                while not cursor.isNull() and not cursor.atEnd():
                    cursor = doc.find(search_text, cursor)
                    if not cursor.isNull():
                        sel = QTextEdit.ExtraSelection()
                        sel.cursor, sel.format = cursor, search_fmt
                        extra_selections.append(sel)

            editor.setExtraSelections(extra_selections)

            # SCROLL FOCUS ROUTINE: Force the top of the selected code block to the top of the window viewport
            if first_selected_cursor and self.code_tabs.currentWidget() == editor and self._scroll_to_selection_pending:
                editor.setTextCursor(first_selected_cursor)

                # Fetch abstract layout coordinate data for the block line and push directly to scroll values
                block = first_selected_cursor.block()
                block_top = editor.document().documentLayout().blockBoundingRect(block).top()
                editor.verticalScrollBar().setValue(int(block_top))

        # Clear the flag after processing the layout views
        self._scroll_to_selection_pending = False

    # --- IMPORT & EXPORT MULTI-FILE LOGIC ---
    def _new_layout(self):
        self.canvas.clear_canvas()
        self.scene_tree.clear()
        self.inspector.set_item(None)
        self.current_selected_item = None
        self.code_tabs.clear()
        self.code_editors.clear()
        self.compiled_results.clear()
        self._scroll_to_selection_pending = False

    def _set_texture_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Viewer Textures", TextureManager.get().base_path)
        if dir_path:
            TextureManager.get().set_base_path(dir_path)
            self.canvas.scene.update()

    def _resolve_external_file(self, filename):
        """Resolves XML filenames by checking local folders and configured SL XUI installation paths."""
        if not filename:
            return None

        # 1. Check current working directory or relative path
        if hasattr(self, 'current_working_dir') and self.current_working_dir:
            local_path = os.path.join(self.current_working_dir, filename)
            if os.path.exists(local_path):
                return local_path

        if os.path.exists(filename):
            return filename

        # 2. Check Second Life XUI path defined in Preferences
        xui_dir = CONFIG.get("paths", {}).get("xui_path", "")
        if xui_dir and os.path.exists(xui_dir):
            # Direct match in xui/en/
            sl_path = os.path.join(xui_dir, filename)
            if os.path.exists(sl_path):
                return sl_path

            # Common Second Life subdirectories to search
            sub_dirs = ["widgets", "windows", "icons", "taskpanel", "navbar"]
            for sub in sub_dirs:
                sub_path = os.path.join(xui_dir, sub, filename)
                if os.path.exists(sub_path):
                    return sub_path

            # Recursive search fallback across the entire xui_dir if not found above
            for root, dirs, files in os.walk(xui_dir):
                if filename in files:
                    return os.path.join(root, filename)

        return None

    def _post_import_layout_pass(self, item):
        """Recursively recalculates layout containers and Z-ordering after full DOM ingestion."""
        if not item:
            return

        for child in item.child_xui_items:
            self._post_import_layout_pass(child)

        if item.tag_name == "tab_container":
            item.update_tabs()
        elif item.tag_name in ("layout_stack", "layout_panel"):
            item.update_layout_stack()

        # Enforce strict DOM list Z-indexing on the completed tree hierarchy
        item.update_z_orders()

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open XUI XML File", "", "XML Files (*.xml);;All Files (*)")
        if not file_path: return

        self.current_working_dir = os.path.dirname(file_path)
        base_filename = os.path.basename(file_path)
        try:
            tree = ET.parse(file_path)
            self._new_layout()
            root_item = self._parse_xml_node(tree.getroot(), parent_item=None, current_file=base_filename)

            self._post_import_layout_pass(root_item)

            self.scene_tree.refresh_tree()
            self._queue_refresh()
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to parse XUI file:\n{str(e)}")

    def _parse_xml_node(self, element, parent_item=None, last_sibling_item=None, current_file="layout.xml"):
        tag_name = element.tag

        if "." in tag_name or tag_name in NON_VISUAL_TAGS:
            if parent_item and isinstance(parent_item, XUIGraphicsItem):
                parent_item.non_visual_children.append({
                    "tag": tag_name,
                    "attributes": dict(element.attrib)
                })
            return None

        attributes = dict(element.attrib)
        if not any(k in attributes for k in ["left", "right", "top", "bottom", "width", "height"]):
            attributes["designer_export_geometry"] = "false"

        parent_w = parent_item.rect().width() if isinstance(parent_item, XUIGraphicsItem) else 500
        parent_h = parent_item.rect().height() if isinstance(parent_item, XUIGraphicsItem) else 500

        left = right = top = bottom = None

        if "left" in attributes:
            left = int(attributes["left"])
        elif "left_delta" in attributes:
            left = int(last_sibling_item.x()) + int(attributes["left_delta"]) if last_sibling_item else int(
                attributes["left_delta"])
        elif "left_pad" in attributes:
            left = int(last_sibling_item.x() + last_sibling_item.rect().width()) + int(
                attributes["left_pad"]) if last_sibling_item else int(attributes["left_pad"])

        if "right" in attributes:
            r_val = int(attributes["right"])
            right = int(parent_w) + r_val if r_val <= 0 else r_val

        if "top" in attributes:
            top = int(attributes["top"])
        elif "top_delta" in attributes:
            top = int(last_sibling_item.y()) + int(attributes["top_delta"]) if last_sibling_item else int(
                attributes["top_delta"])
        elif "top_pad" in attributes:
            top = int(last_sibling_item.y() + last_sibling_item.rect().height()) + int(
                attributes["top_pad"]) if last_sibling_item else int(attributes["top_pad"])

        if "bottom" in attributes:
            b_val = int(attributes["bottom"])
            bottom = int(parent_h) + b_val if b_val <= 0 else b_val

        default_w, default_h = 100, 20
        for cat, widgets in XUI_REGISTRY.items():
            if tag_name in widgets:
                default_w, default_h = widgets[tag_name].get("width", 100), widgets[tag_name].get("height", 20)
                break

        width = int(attributes.get("width", default_w))
        height = int(attributes.get("height", default_h))

        if left is not None and right is not None:
            width = right - left
        elif left is None and right is not None:
            left = right - width
        elif left is None:
            left = 0

        if top is not None and bottom is not None:
            height = bottom - top
        elif top is None and bottom is not None:
            top = bottom - height
        elif top is None:
            top = 0

        attributes.update({
            "left": str(int(left)),
            "top": str(int(top)),
            "width": str(int(width)),
            "height": str(int(height))
        })

        item = XUIGraphicsItem(tag_name, attributes)
        item.source_file = current_file

        if element.text and element.text.strip():
            item.inner_text = element.text.strip()

        item.setPos(QPointF(left, top))
        item.sync_geometry_to_attributes()

        if parent_item and isinstance(parent_item, XUIGraphicsItem):
            parent_item.add_child_item(item)
        elif self.canvas.root_container_instance is None:
            self.canvas.root_container_instance = item
            self.canvas.scene.addItem(item)

        prev_child = None
        for child_el in element:
            created_child = self._parse_xml_node(child_el, parent_item=item, last_sibling_item=prev_child,
                                                 current_file=current_file)
            if created_child:
                prev_child = created_child

        if "filename" in attributes:
            ref_file = attributes["filename"]
            full_path = self._resolve_external_file(ref_file)
            if full_path:
                child_tree = ET.parse(full_path)
                imp_root = self._parse_xml_node(child_tree.getroot(), parent_item=item, current_file=ref_file)
                if imp_root:
                    imp_root.is_imported_root = True
                    imp_root.attributes["follows"] = "all"
                    imp_root.setPos(0, 0)
                    imp_root.resize_item(width, height)

        return item

    def _save_all_files(self):
        if not self.canvas.root_container_instance: return
        dir_path = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.current_working_dir)
        if not dir_path: return

        try:
            results = XUICompiler.generate_source(self.canvas.root_container_instance, None)
            for fname, (xml_str, _) in results.items():
                with open(os.path.join(dir_path, fname), "w", encoding="utf-8") as f:
                    f.write(xml_str)
            QMessageBox.information(self, "Success", f"Saved {len(results)} XUI files successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save files:\n{str(e)}")