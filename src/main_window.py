"""
This module implements the primary workspace interface for SLXUI-Studio. It
orchestrates the coordination between the interactive 2D graphics canvas,
the hierarchical DOM tree viewer, dynamic property inspectors, live multi-file
XML source editors with text search mechanics, and runtime schema evaluation.
"""
import os
import xml.etree.ElementTree as ET
from PySide6.QtCore import Qt, QPointF, QMimeData, QTimer
from PySide6.QtGui import (
    QFont, QAction, QDrag, QTextDocument, QTextCursor, QTextFormat,
    QTextCharFormat, QColor, QBrush, QPalette, QIcon
)
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
    QTextEdit, QFileDialog, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTabWidget, QApplication, QMenu, QSlider, QSizePolicy, QToolBar
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
    """A drag-and-drop enabled component tree populated with valid XUI controls.

        Provides a categorized layout panel containing standard Second Life UI nodes
        available to be dropped directly onto the design canvas.
        """
    def __init__(self, parent=None):
        """Initializes the widget palette tree structure and visual header.

                Args:
                    parent (Optional[QWidget]): Parent container widget context. Defaults to None.
                """
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setHeaderLabel("XUI Widget Palette")

    def startDrag(self, supportedActions):
        """Packages the selected leaf widget's tag name into a MIME text container for drag operations.

        Args:
            supportedActions (Qt.DropActions): The drag-and-drop action options permitted
                by the system layout.
        """
        # Retrieve the actively highlighted tree element
        item = self.currentItem()

        # Early exit safeguard: prevent dragging if empty or if selecting a category folder node
        if not item or item.childCount() > 0:
            return

        # Instantiate the core drag transport controller
        drag = QDrag(self)

        # Encapsulate the raw text metadata into a transferable MIME container
        mime_data = QMimeData()
        mime_data.setText(item.text(0))
        drag.setMimeData(mime_data)

        # Execute the operation as a non-blocking system copy event
        drag.exec(Qt.CopyAction)


class MainWindow(QMainWindow):
    """The central application coordinator window managing the XUI studio layout workspace.

        Integrates menu actions, canvas synchronization loops, performance-debounced XML
        compilation routines, structural highlight styling, multi-file nesting resolution,
        and systemic look-and-feel preference modifications.
        """

    def __init__(self):
        """Initializes application window parameters, state trackers, and debouncing timers."""
        # Initialize the base QMainWindow instance
        super().__init__()

        # Configure main application window window properties
        self.setWindowTitle("SLXUI-Studio")
        self.resize(1600, 950)
        self.setWindowIcon(QIcon("icon.ico"))

        # State tracking variables for selection and path contexts
        self.current_selected_item = None
        self.current_working_dir = ""

        # Structural hierarchy tree filtering and search index states
        self.tree_search_matches = []
        self.tree_search_idx = -1
        self._scroll_to_selection_pending = False

        # Memory cache tables for active editor fields and syntax updates
        self.code_editors = {}
        self.compiled_results = {}

        # Performance Debouncing: Timer tracking for high-frequency compilation sweeps
        self.code_refresh_timer = QTimer()
        self.code_refresh_timer.setSingleShot(True)
        self.code_refresh_timer.setInterval(150)
        self.code_refresh_timer.timeout.connect(self._do_refresh_code_view)

        # Subsystem execution calls to compile layouts and actions
        self._setup_menus()
        self._setup_ui()

    def _setup_menus(self):
        """Constructs application drop-down menu structures, shortcut bounds, and action mappings."""
        # Initialize the primary main window menu bar
        menubar = self.menuBar()

        # Initialize File dropdown menu
        file_menu = menubar.addMenu("&File")

        # Configure action to clear workspace for a blank panel configuration
        new_act = QAction("&New Layout", self)
        new_act.triggered.connect(self._new_layout)
        file_menu.addAction(new_act)

        # Configure action to locate and ingest existing XML layout files
        open_act = QAction("&Open XUI File...", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_file)
        file_menu.addAction(open_act)

        # Configure action to mass compile and write active buffers back to disk
        save_act = QAction("&Save All XML Files...", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._save_all_files)
        file_menu.addAction(save_act)

        # Separator to organize operational workflows visually
        file_menu.addSeparator()

        # Initialize Edit dropdown menu
        edit_menu = menubar.addMenu("&Edit")

        # Configure action to launch application workspace configurations
        pref_act = QAction("Preferences...", self)
        pref_act.triggered.connect(self._open_preferences)
        edit_menu.addAction(pref_act)

    def _setup_ui(self):
        """Instantiates all core workspace layouts, toolbars, view splitters, and signal connections."""
        # Main horizontal layout splitter initialization
        main_splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(main_splitter)
        self.inspector = PropertyInspector()

        # Left Panel: Widget Palette Tree
        palette_tree = WidgetPaletteTree()
        for cat_name, widgets in XUI_REGISTRY.items():
            cat_item = QTreeWidgetItem(palette_tree, [cat_name])
            for w_name, w_meta in widgets.items():
                item = QTreeWidgetItem(cat_item, [w_name])
                item.setToolTip(0, w_meta.get("desc", w_name))

        palette_tree.expandAll()
        main_splitter.addWidget(palette_tree)

        # Center Panel: Canvas Workspace & Code View Configuration
        center_splitter = QSplitter(Qt.Vertical)

        # Interactive 2D Canvas Area
        canvas_container_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_container_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)

        # Toolbar Construction
        self.top_toolbar = QToolBar("Canvas Actions")
        self.top_toolbar.setMovable(False)
        self.top_toolbar.setStyleSheet(
            "QToolBar { background: #222222; border-bottom: 1px solid #444444; padding: 4px; }"
        )

        # Toolbar Items: Layout Spacers and Labels
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.top_toolbar.addWidget(spacer)

        self.grid_size_label = QLabel("Grid: 10px  ")
        self.grid_size_label.setStyleSheet("color: #CCCCCC; font-weight: bold;")
        self.top_toolbar.addWidget(self.grid_size_label)

        # Toolbar Items: Grid Resolution Slider
        self.grid_slider = QSlider(Qt.Horizontal)
        self.grid_slider.setRange(2, 50)
        self.grid_slider.setValue(10)
        self.grid_slider.setFixedWidth(120)
        self.grid_slider.setToolTip("Adjust Grid Snap Size (2px - 50px)")
        self.grid_slider.setStyleSheet(
            "QSlider::handle:horizontal { background: #1e457c; width: 14px; margin: -4px 0; border-radius: 7px; }"
        )
        self.grid_slider.valueChanged.connect(self._on_grid_size_changed)
        self.top_toolbar.addWidget(self.grid_slider)

        spacer_small = QWidget()
        spacer_small.setFixedWidth(15)
        self.top_toolbar.addWidget(spacer_small)

        # Toolbar Items: Snapping Action Button
        self.snap_grid_btn = QPushButton("🧲 Snap: ON")
        self.snap_grid_btn.setCheckable(True)
        self.snap_grid_btn.setChecked(True)
        self.snap_grid_btn.setToolTip("Toggle Grid Snapping")
        self.snap_grid_btn.setCursor(Qt.PointingHandCursor)
        self.snap_grid_btn.setStyleSheet(
            "background-color: #1e457c; color: white; padding: 5px 12px; border-radius: 3px; font-weight: bold;"
        )
        self.snap_grid_btn.toggled.connect(self._on_toggle_grid_snapping)
        self.top_toolbar.addWidget(self.snap_grid_btn)

        # Finalize Canvas Layout
        canvas_layout.addWidget(self.top_toolbar)
        self.canvas = CanvasContainer()
        self.canvas.setBackgroundBrush(QBrush(QColor(CONFIG["ui_colors"]["canvas_bg"])))
        canvas_layout.addWidget(self.canvas)
        center_splitter.addWidget(canvas_container_widget)

        # Live XML Source Code View Area
        code_container = QWidget()
        code_layout = QVBoxLayout(code_container)
        code_layout.setContentsMargins(0, 0, 0, 0)

        # Header Control Bar & Search Utilities
        xml_header_layout = QHBoxLayout()
        xml_header_layout.addWidget(QLabel("<b>Live Second Life XML Source:</b>"))
        xml_header_layout.addStretch()

        self.xml_search_input = QLineEdit()
        self.xml_search_input.setPlaceholderText("Find in XML...")
        self.xml_search_input.setFixedWidth(150)
        self.xml_search_input.textChanged.connect(self._on_xml_search_changed)
        xml_header_layout.addWidget(self.xml_search_input)

        # XML String Selection Iterators (Up/Down Arrows)
        for text, slot in [("▲", self._xml_search_prev), ("▼", self._xml_search_next)]:
            btn = QPushButton(text)
            btn.setFixedWidth(30)
            btn.clicked.connect(slot)
            xml_header_layout.addWidget(btn)

        # Source Layout Tab Widget Integration
        code_layout.addLayout(xml_header_layout)
        self.code_tabs = QTabWidget()
        self.code_tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.code_tabs.customContextMenuRequested.connect(self._on_code_tabs_context_menu)
        code_layout.addWidget(self.code_tabs)

        # Commit Central Workspace Splitting Ratios
        code_container.setLayout(code_layout)
        center_splitter.addWidget(code_container)
        center_splitter.setSizes([650, 300])
        main_splitter.addWidget(center_splitter)

        # Right Panel: Hierarchy Tree & Property Inspectors
        right_splitter = QSplitter(Qt.Vertical)

        # System DOM Hierarchy Layout Tree
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

        # Node Traversal Directional Keys (Up/Down Arrows)
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

        # Property Schema Attribute Fields
        inspector_container = QWidget()
        inspector_layout = QVBoxLayout(inspector_container)
        inspector_layout.setContentsMargins(0, 0, 0, 0)
        inspector_layout.addWidget(QLabel("<b>Widget Attributes:</b>"))
        self.inspector = PropertyInspector()
        inspector_layout.addWidget(self.inspector)
        right_splitter.addWidget(inspector_container)

        # Commit Sub-Inspector Boundaries and Main Window Proportions
        right_splitter.setSizes([350, 600])
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([250, 950, 400])

        # Inter-Widget Signal Interconnections
        self.canvas.item_selected_signal.connect(self._on_item_selected)
        self.canvas.item_modified_signal.connect(self._on_canvas_item_modified)
        self.inspector.property_changed_signal.connect(self._queue_refresh)
        self.scene_tree.tree_refreshed.connect(self._reapply_tree_search)
        self.inspector.external_file_import_needed.connect(self._import_external_file_to_item)

    def _on_toggle_grid_snapping(self, checked):
        """Toggles layout alignment tracking snap rules on the 2D canvas workspace.

        Args:
            checked (bool): Flag indicating if grid snapping is visually active.
        """
        # Verify the interactive canvas context exists before pushing rule updates
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.grid_snapping_enabled = checked

            # Branch changes based on the interactive toggled boolean flag
            if checked:
                # Update snapping button state indicator to Active
                self.snap_grid_btn.setText("🧲 Snap: ON")
                self.snap_grid_btn.setStyleSheet(
                    "background-color: #1e457c; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;"
                )
            else:
                # Update snapping button state indicator to Inactive
                self.snap_grid_btn.setText("🧲 Snap: OFF")
                self.snap_grid_btn.setStyleSheet(
                    "background-color: #333333; color: #AAAAAA; padding: 5px 10px; border-radius: 3px;"
                )

    def _on_grid_size_changed(self, value):
        """Updates grid square pixel dimensions on the layout canvas context.

        Args:
            value (int): Pixel grid resolution boundaries (typically between 2px and 50px).
        """
        self.grid_size_label.setText(f"Grid: {value}px  ")
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.grid_size = value
            self.canvas.scene.update()

    def apply_live_preferences(self):
        """Pushes theme color changes dynamically across all active editor nodes without restart sequences."""
        # Step 1: Resolve the running application context and modify the global window palette
        app = QApplication.instance()
        if app:
            palette = QPalette()

            # Apply baseline system backgrounds and text color profiles
            palette.setColor(QPalette.Window, QColor(CONFIG["ui_colors"]["window_bg"]))
            palette.setColor(QPalette.WindowText, QColor(CONFIG["ui_colors"]["window_text"]))
            palette.setColor(QPalette.Base, QColor(CONFIG["ui_colors"]["tree_bg"]))
            palette.setColor(QPalette.AlternateBase, QColor(CONFIG["ui_colors"]["window_bg"]))
            palette.setColor(QPalette.Text, QColor(CONFIG["ui_colors"]["window_text"]))
            palette.setColor(QPalette.Button, QColor(CONFIG["ui_colors"]["window_bg"]))
            palette.setColor(QPalette.ButtonText, QColor(CONFIG["ui_colors"]["window_text"]))

            # Configure active and inactive list item focus highlights
            highlight_color = QColor(CONFIG["ui_colors"]["highlight"])
            palette.setColor(QPalette.Highlight, highlight_color)
            palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.Inactive, QPalette.Highlight, highlight_color)
            palette.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor("#FFFFFF"))

            # Inject the freshly configured color map into the window engine
            app.setPalette(palette)

        # Step 2: Mutate the visual workspace background color and force canvas repaints
        if hasattr(self, "canvas") and self.canvas:
            self.canvas.setBackgroundBrush(QBrush(QColor(CONFIG["ui_colors"]["canvas_bg"])))
            self.canvas.scene.update()

        # Step 3: Rebuild the categorized left-hand widget layout menu list elements
        if hasattr(self, "palette_tree") and self.palette_tree:
            self.palette_tree.clear()
            if hasattr(self.palette_tree, "populate_tree"):
                self.palette_tree.populate_tree()

        # Step 4: Traverse open code layout tabs to trigger regex rule transformations
        if hasattr(self, "code_tabs") and self.code_tabs:
            for i in range(self.code_tabs.count()):
                editor = self.code_tabs.widget(i)

                # Locate the highlighting engine attachment bound to the editor's text document
                for child in editor.children():
                    if isinstance(child, XMLHighlighter):
                        child.rebuild_rules()
                        break

    def _open_preferences(self):
        """Spins up the user configuration and theme adjustment dialog interface window."""
        # Instantiate the application preferences overlay panel
        dlg = PreferencesDialog(self)

        # Execute the dialog window modally, blocking parent input loops until exit
        dlg.exec()

    def _on_canvas_item_modified(self, item):
        """Triggers editor sync passes when canvas items are dragged or structurally scaled.

        Args:
            item (XUIGraphicsItem): The specific object on the canvas that was altered.
        """
        # Enqueue a code generation refresh loop pass
        self._queue_refresh()

        # Synchronize attribute lists if the modified object is actively under inspection
        if item and item == self.current_selected_item:
            self.inspector.refresh_values()

    def _get_active_editor(self):
        """Retrieves the QTextEdit control corresponding to the currently selected source tab view.

        Returns:
            Optional[QTextEdit]: The active code workspace widget, or None if no tabs exist.
        """
        # Pull the visible text widget out of the active tab view collection
        return self.code_tabs.currentWidget()

    def _on_xml_search_changed(self, text):
        """Updates string search highlights across the active XML workspace.

        Args:
            text (str): Substring criteria to isolate.
        """
        # Refresh highlighted selections across editor documents without a compilation sweep
        self._apply_extra_selections()

        # Automatically snap focus to the first matching criteria hit
        self._xml_search_next()

    def _xml_search_next(self):
        """Forwards the active text cursor focus to the next sequential match in the code viewer."""
        text = self.xml_search_input.text()
        editor = self._get_active_editor()

        # Early exit safeguard if the target text is blank or no tabs are open
        if not text or not editor:
            return

        # Attempt to locate the string forward; if it fails, wrap focus back to the top
        if not editor.find(text):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            editor.setTextCursor(cursor)
            editor.find(text)

    def _xml_search_prev(self):
        """Backtracks the active text cursor focus to the preceding match in the code viewer."""
        text = self.xml_search_input.text()
        editor = self._get_active_editor()

        # Early exit safeguard if the target text is blank or no tabs are open
        if not text or not editor:
            return

        # Attempt to locate the string backward; if it fails, wrap focus down to the end
        options = QTextDocument.FindBackward
        if not editor.find(text, options):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            editor.setTextCursor(cursor)
            editor.find(text, options)

    def _on_tree_search_changed(self, text):
        """Highlights matching hierarchy elements within the DOM structure view.

        Args:
            text (str): Search string token to match against widget tag name keys.
        """
        # Flush existing match collections and reset the active traversal cursor index
        self.tree_search_matches = []
        self.tree_search_idx = -1

        # Initialize a framework iterator to traverse the scene tree elements linearly
        it = QTreeWidgetItemIterator(self.scene_tree)
        while it.value():
            item = it.value()

            # Strip stale search background styling from the tree node
            item.setBackground(0, QBrush())
            xui_item = item.data(0, Qt.UserRole)

            # Distinguish imported sub-roots visually by altering their default text color
            fg_color = QColor("#00FF00") if xui_item and getattr(xui_item, 'is_imported_root', False) else QColor(
                CONFIG["ui_colors"]["window_text"]
            )
            item.setForeground(0, QBrush(fg_color))

            # Check if the node label contains the target search string query
            if text and text.lower() in item.text(0).lower():
                # Apply configuration-driven syntax formatting colors to the match
                item.setBackground(0, QBrush(QColor(CONFIG["syntax_colors"]["search_bg"])))
                item.setForeground(0, QBrush(QColor(CONFIG["syntax_colors"]["search_fg"])))
                self.tree_search_matches.append(item)

            it += 1

        # Automatically scroll viewport focus to the first matched candidate block
        if self.tree_search_matches:
            self._tree_search_next()

    def _reapply_tree_search(self):
        """Refreshes tree highlight layouts following background node reordering passes."""
        # Re-evaluate filtering metrics if the raw layout search query isn't empty
        if self.tree_search_input.text():
            self._on_tree_search_changed(self.tree_search_input.text())

    def _tree_search_next(self):
        """Advances selected item state focus to the next node matching tree criteria."""
        # Safeguard execution against empty hit matrices
        if not self.tree_search_matches:
            return

        # Increment the query index tracker, wrapping around to zero seamlessly via modulo arithmetic
        self.tree_search_idx = (self.tree_search_idx + 1) % len(self.tree_search_matches)

        # Pass selection instructions directly to the tree viewer container hierarchy
        self.scene_tree.setCurrentItem(self.tree_search_matches[self.tree_search_idx])

    def _tree_search_prev(self):
        """Regresses selected item state focus to the previous node matching tree criteria."""
        # Safeguard execution against empty hit matrices
        if not self.tree_search_matches:
            return

        # Decrement the query index tracker, wrapping backwards across index values via modulo arithmetic
        self.tree_search_idx = (self.tree_search_idx - 1) % len(self.tree_search_matches)

        # Pass selection instructions directly to the tree viewer container hierarchy
        self.scene_tree.setCurrentItem(self.tree_search_matches[self.tree_search_idx])

    def _on_item_selected(self, item):
        """Updates the inspector context and moves code view tab selection to track canvas items.

        Args:
            item (Optional[XUIGraphicsItem]): The newly selected canvas component target.
        """
        # Track the active structural focus globally and push attributes to properties view
        self.current_selected_item = item
        self.inspector.set_item(item)

        # Traverse tab arrays to identify and show the document owning this node
        if item:
            fname = getattr(item, 'source_file', 'layout.xml')
            for i in range(self.code_tabs.count()):
                if self.code_tabs.tabText(i) == fname:
                    self.code_tabs.setCurrentIndex(i)
                    break

        # Flag an active selection event and schedule source code recompilation loops
        self._scroll_to_selection_pending = True
        self._queue_refresh()

    def _queue_refresh(self, _ignored=None):
        """Enqueues a performance-debounced layout recompilation sequence."""
        # Spin up the single-shot compilation suppression timer block
        self.code_refresh_timer.start()

    def _do_refresh_code_view(self):
        """Generates dynamic XML structures from the design canvas and matches textual changes."""
        # Early exit safeguard: reset and clear layout structures if the canvas is empty
        if not self.canvas.root_container_instance:
            self.code_tabs.clear()
            self.code_editors.clear()
            self.compiled_results.clear()
            return

        # Compile the interactive canvas components down to raw target XML structures
        self.compiled_results = XUICompiler.generate_source(
            self.canvas.root_container_instance, self.current_selected_item
        )

        # Reconcile editor collections by cleaning out stale or deleted tab references
        for fname in list(self.code_editors.keys()):
            if fname not in self.compiled_results:
                editor = self.code_editors.pop(fname)
                idx = self.code_tabs.indexOf(editor)
                self.code_tabs.removeTab(idx)
                editor.deleteLater()

        # Iterate through active compilation streams to populate or update tabs
        for fname, (xml_str, selections) in self.compiled_results.items():
            # Instantiate a new QTextEdit field if this file context isn't tracked yet
            if fname not in self.code_editors:
                editor = QTextEdit()
                editor.setFont(QFont("Consolas", 10))
                editor.setReadOnly(True)
                editor.setStyleSheet(
                    f"background-color: {CONFIG['ui_colors']['tree_bg']}; "
                    f"color: {CONFIG['ui_colors']['window_text']};"
                )
                XMLHighlighter(editor.document())
                self.code_tabs.addTab(editor, fname)
                self.code_editors[fname] = editor

            # Update text string layout buffers while maintaining the active vertical scroll position
            editor = self.code_editors[fname]
            scroll_pos = editor.verticalScrollBar().value()
            editor.setPlainText(xml_str)
            editor.verticalScrollBar().setValue(scroll_pos)

        # Apply extra graphical block overlays, highlights, and search matches
        self._apply_extra_selections()

    def _apply_extra_selections(self):
        """Applies syntax formatting, error wavelines, and search tags to the editor text layouts."""
        # Traverse open editors to draw conditional selection formatting structures
        for fname, editor in self.code_editors.items():
            if fname not in self.compiled_results:
                continue

            selections = self.compiled_results[fname][1]
            extra_selections = []
            doc = editor.document()
            first_selected_cursor = None

            # Inline helper routine to map explicit multi-line ranges to selection instances
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

            # Layer 1: Apply highlight background regions across chosen layout components
            sel_fmt = QTextCharFormat()
            sel_fmt.setBackground(QColor(CONFIG["ui_colors"]["highlight"]))
            sel_fmt.setProperty(QTextFormat.FullWidthSelection, True)
            for start, end in selections['selected']:
                add_selection(start, end, sel_fmt)
                if first_selected_cursor is None:
                    first_selected_cursor = QTextCursor(doc.findBlockByNumber(start))

            # Layer 2: Construct wave formatting configurations to call out structural errors
            err_fmt = QTextCharFormat()
            err_fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            err_fmt.setUnderlineColor(QColor(CONFIG["syntax_colors"]["error"]))
            for start, end, msgs in selections['errors']:
                add_selection(start, end, err_fmt)

            # Layer 3: Construct wave formatting configurations to call out structural warnings
            warn_fmt = QTextCharFormat()
            warn_fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            warn_fmt.setUnderlineColor(QColor(CONFIG["syntax_colors"]["warning"]))
            for start, end, msgs in selections['warnings']:
                add_selection(start, end, warn_fmt)

            # Layer 4: Append string lookup match formatting overlays to the running tab text view
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

            # Apply structural selections to the active layout instance
            editor.setExtraSelections(extra_selections)

            # Focus Control: Force scroll parameters to center on the active component definition line
            if first_selected_cursor and self.code_tabs.currentWidget() == editor and self._scroll_to_selection_pending:
                editor.setTextCursor(first_selected_cursor)
                block = first_selected_cursor.block()
                block_top = editor.document().documentLayout().blockBoundingRect(block).top()
                editor.verticalScrollBar().setValue(int(block_top))

        # Reset selection tracking variables upon completing execution cycles
        self._scroll_to_selection_pending = False

    def _new_layout(self):
        """Wipes the active design canvas, structural models, and files to begin a blank panel configuration."""
        # Reset interactive 2D canvas workspace and structural models
        self.canvas.clear_canvas()
        self.scene_tree.clear()

        # Reset property state variables and selection tracking nodes
        self.inspector.set_item(None)
        self.current_selected_item = None

        # Clear active code editor layout components and cached results
        self.code_tabs.clear()
        self.code_editors.clear()
        self.compiled_results.clear()

        # Disengage scrolling triggers
        self._scroll_to_selection_pending = False

    def _resolve_external_file(self, filename):
        """Locates an XML file within local runtime working paths or active skin hierarchies.

        Args:
            filename (str): Target file string identity to track down.

        Returns:
            Optional[str]: Absolute path string to the discovered file target, or None if unresolved.
        """
        # Early exit safeguard if the target text string variable is empty
        if not filename:
            return None

        # Scenario 1: Directly handle absolute formatting specifications or local workspace paths
        if os.path.exists(filename):
            return os.path.abspath(filename)

        # Scenario 2: Evaluate matching parameters relative to the current file working folder context
        if hasattr(self, "current_working_dir") and self.current_working_dir:
            local_path = os.path.join(self.current_working_dir, filename)
            if os.path.exists(local_path):
                return local_path

        # Scenario 3: Traversal loop fallback over systemic configurations or custom viewer skin folders
        try:
            from config import get_xui_paths

            for xui_dir in get_xui_paths():
                if not os.path.exists(xui_dir):
                    continue

                # Check the root workspace layout container directory
                candidate = os.path.join(xui_dir, filename)
                if os.path.exists(candidate):
                    return candidate

                # Deep scan search sequence across nested subdirectories
                for root, _, files in os.walk(xui_dir):
                    if filename in files:
                        return os.path.join(root, filename)
        except Exception as e:
            print(f"[Verbose Error] _resolve_external_file search failed: {e}")

        return None

    def _import_external_file_to_item(self, item, filename):
        """Parses an external XML layout and nests it dynamically inside a target container node.

        Args:
            item (XUIGraphicsItem): Parent node receiving the child layout addition.
            filename (str): Filename context containing the target sub-elements.
        """
        # Early exit safeguard if either structural instance variable is empty
        if not item or not filename:
            return

        try:
            import xml.etree.ElementTree as ET

            # Step 1: Filter out historical structural instances on this node to prevent layout leaks
            existing_imports = [
                c
                for c in list(getattr(item, "child_xui_items", []))
                if getattr(c, "is_imported_root", False)
            ]
            for old_imp in existing_imports:
                if hasattr(self, "canvas") and self.canvas:
                    self.canvas.delete_item(old_imp)
                elif old_imp in item.child_xui_items:
                    item.child_xui_items.remove(old_imp)
                    old_imp.deleteLater()

            # Step 2: Validate target filename structures against filesystem paths
            full_path = self._resolve_external_file(filename)
            if not full_path or not os.path.exists(full_path):
                QMessageBox.warning(
                    self,
                    "Import Warning",
                    f"Could not locate external XML file:\n'{filename}'\n\nPlease check your XUI / Skins directory settings.",
                )
                print(f"[Verbose Error] Could not resolve external file to import: '{filename}'")
                return

            # Step 3: Run standard DOM extraction loops over target asset files
            child_tree = ET.parse(full_path)
            imp_root = self._parse_xml_node(
                child_tree.getroot(), parent_item=item, current_file=filename
            )

            if not imp_root:
                print(f"[Verbose Error] XML parsing returned None for '{filename}'")
                return

            # Step 4: Configure core properties and alignment rules for the sub-root element
            imp_root.is_imported_root = True
            imp_root.attributes["follows"] = "all"

            # Explicitly assign parent dependencies within Qt structural hierarchies
            if imp_root.parentItem() != item:
                imp_root.setParentItem(item)

            # Append new layouts to internal tracking coordinate matrices
            if not hasattr(item, "child_xui_items"):
                item.child_xui_items = []
            if imp_root not in item.child_xui_items:
                item.child_xui_items.append(imp_root)

            # Step 5: Iteratively attach the incoming asset trees into the operational rendering engine context
            if hasattr(self, "canvas") and self.canvas and self.canvas.scene:

                def register_to_scene(node):
                    if node.scene() != self.canvas.scene:
                        self.canvas.scene.addItem(node)
                    for child in getattr(node, "child_xui_items", []):
                        register_to_scene(child)

                register_to_scene(imp_root)

            # Step 6: Recalculate component dimensions to sync up with host bounds
            imp_root.setPos(0, 0)
            try:
                w = float(item.attributes.get("width", 100))
                h = float(item.attributes.get("height", 20))
                imp_root.resize_item(w, h)
                imp_root.sync_attributes_to_geometry()
            except ValueError:
                pass

            # Step 7: Finalize visual sorting order passes and rebuild scene views
            if hasattr(item, "update_z_orders"):
                item.update_z_orders()

            if hasattr(self, "_post_import_layout_pass"):
                self._post_import_layout_pass(item)

            if hasattr(self, "scene_tree") and self.scene_tree:
                self.scene_tree.refresh_tree()

            # Enqueue code generation workspace refresh updates
            self._queue_refresh()

            if hasattr(self, "canvas") and self.canvas and self.canvas.scene:
                self.canvas.scene.update()

            print(f"[Success] Dynamically imported '{filename}' into <{item.tag_name}>.")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to dynamically import '{filename}':\n{str(e)}",
            )
            print(f"[Verbose Error] _import_external_file_to_item exception: {e}")

    def _post_import_layout_pass(self, item):
        """Recursively updates positional alignments and Z-stack index arrays across a component tree.

        Args:
            item (XUIGraphicsItem): The target node where layout updating starts.
        """
        # Early exit safeguard if the provided node context is empty
        if not item:
            return

        # Deep traversal pass across child nodes prior to updating the host container
        for child in item.child_xui_items:
            self._post_import_layout_pass(child)

        # Route specialized layout transformations based on standard UI node keywords
        if item.tag_name == "tab_container":
            item.update_tabs()
        elif item.tag_name in ("layout_stack", "layout_panel"):
            item.update_layout_stack()

        # Enforce strict DOM index Z-ordering rules across visual child nodes
        item.update_z_orders()

    def _open_file(self):
        """Prompts for and ingests an existing Second Life XML configuration into the canvas environment."""
        # Launch system directory interface to select an existing configuration layout asset
        file_path, _ = QFileDialog.getOpenFileName(self, "Open XUI XML File", "", "XML Files (*.xml);;All Files (*)")
        if not file_path:
            return

        # Track directory paths globally to resolve relative path references later
        self.current_working_dir = os.path.dirname(file_path)
        base_filename = os.path.basename(file_path)

        try:
            # Ingest the target resource file path using the standard DOM streaming engine
            tree = ET.parse(file_path)

            # Clear existing active canvas layout workspaces completely
            self._new_layout()

            # Recursively construct visual layout component trees out of raw XML nodes
            root_item = self._parse_xml_node(tree.getroot(), parent_item=None, current_file=base_filename)

            # Run alignment logic loops over the completed structural ingestion tree
            self._post_import_layout_pass(root_item)

            # Re-populate hierarchy items inside structural tree views and trigger code updates
            self.scene_tree.refresh_tree()
            self._queue_refresh()

        except Exception as e:
            # Display explicit structural layout evaluation crash data inside modal window popups
            QMessageBox.critical(self, "Import Error", f"Failed to parse XUI file:\n{str(e)}")

    def _parse_xml_node(self, element, parent_item=None, last_sibling_item=None, current_file="layout.xml"):
        """Translates an ElementTree XML token recursively into functional canvas components.

        Parses spatial parameters (left, top, layout rules, delta configurations), assigns
        defaults, maps internal properties, and instantiates visual canvas items.

        Args:
            element (xml.etree.ElementTree.Element): The source XML node to transform.
            parent_item (Optional[XUIGraphicsItem]): Parent structural component, if any.
            last_sibling_item (Optional[XUIGraphicsItem]): Preceding parsed node for layout tracking.
            current_file (str): Context file marker tracking source ownership rules.

        Returns:
            Optional[XUIGraphicsItem]: Valid generated canvas component, or None if non-visual.
        """
        tag_name = element.tag

        # Step 1: Filter out callbacks, text definitions, and other non-visual sub-tags
        if "." in tag_name or tag_name in NON_VISUAL_TAGS:
            if parent_item and isinstance(parent_item, XUIGraphicsItem):
                parent_item.non_visual_children.append({
                    "tag": tag_name,
                    "attributes": dict(element.attrib)
                })
            return None

        # Step 2: Initialize attribute copy and track structural geometry flags
        attributes = dict(element.attrib)
        if not any(k in attributes for k in ["left", "right", "top", "bottom", "width", "height"]):
            attributes["designer_export_geometry"] = "false"

        # Step 3: Resolve bounding dimensions of the parent host container context
        parent_w = parent_item.rect().width() if isinstance(parent_item, XUIGraphicsItem) else 500
        parent_h = parent_item.rect().height() if isinstance(parent_item, XUIGraphicsItem) else 500

        left = right = top = bottom = None

        # Step 4: Calculate the horizontal baseline constraints (Left, Deltas, Padding)
        if "left" in attributes:
            left = int(attributes["left"])
        elif "left_delta" in attributes:
            left = int(last_sibling_item.x()) + int(attributes["left_delta"]) if last_sibling_item else int(
                attributes["left_delta"])
        elif "left_pad" in attributes:
            left = int(last_sibling_item.x() + last_sibling_item.rect().width()) + int(
                attributes["left_pad"]) if last_sibling_item else int(attributes["left_pad"])

        # Resolve right edge attachments relative to parent bounding box widths
        if "right" in attributes:
            r_val = int(attributes["right"])
            right = int(parent_w) + r_val if r_val <= 0 else r_val

        # Step 5: Calculate the vertical baseline constraints (Top, Deltas, Padding)
        if "top" in attributes:
            top = int(attributes["top"])
        elif "top_delta" in attributes:
            top = int(last_sibling_item.y()) + int(attributes["top_delta"]) if last_sibling_item else int(
                attributes["top_delta"])
        elif "top_pad" in attributes:
            top = int(last_sibling_item.y() + last_sibling_item.rect().height()) + int(
                attributes["top_pad"]) if last_sibling_item else int(attributes["top_pad"])

        # Resolve bottom edge attachments relative to parent bounding box heights
        if "bottom" in attributes:
            b_val = int(attributes["bottom"])
            bottom = int(parent_h) + b_val if b_val <= 0 else b_val

        # Step 6: Query systemic component registry catalogs for generic fallback sizing ratios
        default_w, default_h = 100, 20
        for cat, widgets in XUI_REGISTRY.items():
            if tag_name in widgets:
                default_w, default_h = widgets[tag_name].get("width", 100), widgets[tag_name].get("height", 20)
                break

        width = int(attributes.get("width", default_w))
        height = int(attributes.get("height", default_h))

        # Step 7: Resolve conflicting geometric constraints to compute definitive widths
        if left is not None and right is not None:
            width = right - left
        elif left is None and right is not None:
            left = right - width
        elif left is None:
            left = 0

        # Resolve conflicting geometric constraints to compute definitive heights
        if top is not None and bottom is not None:
            height = bottom - top
        elif top is None and bottom is not None:
            top = bottom - height
        elif top is None:
            top = 0

        # Step 8: Update attribute collection map values with normalized spatial values
        attributes.update({
            "left": str(int(left)),
            "top": str(int(top)),
            "width": str(int(width)),
            "height": str(int(height))
        })

        # Step 9: Instantiate canvas component wrappers and bind tracking attributes
        item = XUIGraphicsItem(tag_name, attributes)
        item.source_file = current_file

        if element.text and element.text.strip():
            item.inner_text = element.text.strip()

        # Commit layout spatial properties down to item geometry attributes
        item.setPos(QPointF(left, top))
        item.sync_geometry_to_attributes()

        # Step 10: Register component hierarchy bounds to parent hosts or root container views
        if parent_item and isinstance(parent_item, XUIGraphicsItem):
            parent_item.add_child_item(item)
        elif self.canvas.root_container_instance is None:
            self.canvas.root_container_instance = item
            self.canvas.scene.addItem(item)

        # Step 11: Deep loop recursion traversal pass across internal child components
        prev_child = None
        for child_el in element:
            created_child = self._parse_xml_node(child_el, parent_item=item, last_sibling_item=prev_child,
                                                 current_file=current_file)
            if created_child:
                prev_child = created_child

        # Step 12: Dynamically resolve and inject downstream external layout templates if linked
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

    def _on_code_tabs_context_menu(self, pos):
        """Deploys file saving operations through a right-click interface context over source tab arrays.

        Args:
            pos (QPoint): Cursor alignment positioning context coordinates.
        """
        try:
            # Step 1: Resolve the exact tab node index under the mouse cursor position
            tab_bar = self.code_tabs.tabBar()
            tab_bar_pos = tab_bar.mapFromParent(pos)
            tab_idx = tab_bar.tabAt(tab_bar_pos)

            # Fallback to the active central window panel if right-clicked outside bounds
            if tab_idx == -1:
                tab_idx = self.code_tabs.currentIndex()

            # Early exit safeguard if the tab index array resolves to empty values
            if tab_idx == -1 or self.code_tabs.count() == 0:
                return

            # Step 2: Extract file identifier string metadata from the targeted tab header
            filename = self.code_tabs.tabText(tab_idx)

            # Step 3: Populate context dropdown layout entries
            menu = QMenu(self)
            save_act = menu.addAction(f"Save '{filename}'")
            save_as_act = menu.addAction(f"Save '{filename}' As...")
            menu.addSeparator()
            save_all_act = menu.addAction("Save All")

            # Bind event callbacks dynamically with custom asset label markers
            save_act.triggered.connect(lambda: self._save_single_file(filename))
            save_as_act.triggered.connect(lambda: self._save_single_file_as(filename))
            save_all_act.triggered.connect(self._save_all_files)

            # Deploy the context menu tracking system overlay modally on screen
            menu.exec(self.code_tabs.mapToGlobal(pos))
        except Exception as e:
            QMessageBox.critical(self, "Context Menu Error", f"Failed to open tab context menu:\n{str(e)}")
            print(f"[Verbose Error] _on_code_tabs_context_menu exception: {e}")

    def _save_single_file(self, filename):
        """Compiles text layout specifications and pushes updates to a file target on disk.

        Args:
            filename (str): Name string of the targeted code panel layout.
        """
        # Early exit safeguard if the central working engine tree is empty
        if not self.canvas.root_container_instance:
            return

        try:
            # Step 1: Run compilation sweep over structural DOM elements
            results = XUICompiler.generate_source(self.canvas.root_container_instance, None)
            if filename not in results:
                QMessageBox.warning(self, "Save Warning", f"Could not find compiled source for '{filename}'.")
                return

            xml_str, _ = results[filename]

            # Step 2: Attempt path resolution loops within workspace asset paths
            target_path = self._resolve_external_file(filename)
            if not target_path and self.current_working_dir:
                target_path = os.path.join(self.current_working_dir, filename)

            # Forward instruction parameters to a new target path selector if file doesn't exist
            if not target_path or not os.path.exists(target_path):
                self._save_single_file_as(filename)
                return

            # Step 3: Stream updated text out to system storage blocks
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(xml_str)
            QMessageBox.information(self, "File Saved", f"Successfully saved '{filename}' to:\n{target_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save '{filename}':\n{str(e)}")
            print(f"[Verbose Error] _save_single_file exception: {e}")

    def _save_single_file_as(self, filename):
        """Prompts for target file location paths before serializing text layouts to disk.

        Args:
            filename (str): Context tracking baseline identifier string.
        """
        # Early exit safeguard if the central working engine tree is empty
        if not self.canvas.root_container_instance:
            return

        try:
            # Step 1: Run compilation sweep over structural DOM elements
            results = XUICompiler.generate_source(self.canvas.root_container_instance, None)
            if filename not in results:
                QMessageBox.warning(self, "Save Warning", f"Could not find compiled source for '{filename}'.")
                return

            xml_str, _ = results[filename]
            start_dir = self.current_working_dir if self.current_working_dir else ""
            default_path = os.path.join(start_dir, filename)

            # Step 2: Launch target path directory file dialog tracker interface box
            file_path, _ = QFileDialog.getSaveFileName(
                self, f"Save '{filename}' As...", default_path, "XML Files (*.xml);;All Files (*)"
            )
            if not file_path:
                return

            # Update global reference records with target storage path directory
            self.current_working_dir = os.path.dirname(file_path)

            # Step 3: Stream compiled text string payload directly down to storage
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(xml_str)
            QMessageBox.information(self, "File Saved", f"Successfully saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save As Error", f"Failed to save '{filename}':\n{str(e)}")
            print(f"[Verbose Error] _save_single_file_as exception: {e}")

    def _save_all_files(self):
        """Mass compiles canvas parameters and outputs individual files into a targeted directory."""
        # Early exit safeguard if the central working engine tree is empty
        if not self.canvas.root_container_instance:
            return

        # Launch system directory container selection tool window panel
        dir_path = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.current_working_dir)
        if not dir_path:
            return

        try:
            # Step 1: Run full layout evaluation and extraction process loops
            results = XUICompiler.generate_source(self.canvas.root_container_instance, None)

            # Step 2: Traverse compiled file output sets to write records to targeted path strings
            for fname, (xml_str, _) in results.items():
                with open(os.path.join(dir_path, fname), "w", encoding="utf-8") as f:
                    f.write(xml_str)

            QMessageBox.information(self, "Success", f"Saved {len(results)} XUI files successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save files:\n{str(e)}")