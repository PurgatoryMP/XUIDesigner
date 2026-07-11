# tree_widget.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator

class SceneTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("XUI DOM Hierarchy")
        self.itemSelectionChanged.connect(self._on_tree_selection)
        self.canvas_container = None
        self.syncing = False

    def set_canvas(self, canvas):
        self.canvas_container = canvas
        canvas.item_selected_signal.connect(self.select_item_from_canvas)
        canvas.item_modified_signal.connect(self.refresh_tree)

    def refresh_tree(self, _ignored=None):
        if self.syncing or not self.canvas_container:
            return
        self.syncing = True
        self.clear()

        if self.canvas_container.root_container_instance:
            self._add_node_to_tree(self.canvas_container.root_container_instance, self.invisibleRootItem())
            self.expandAll()

        self.syncing = False

    def _add_node_to_tree(self, xui_item, parent_tree_item):
        name_str = xui_item.attributes.get("name", xui_item.tag_name)
        display_text = f"<{xui_item.tag_name}> {name_str}"
        tree_item = QTreeWidgetItem(parent_tree_item, [display_text])
        tree_item.setData(0, Qt.UserRole, xui_item)

        for child in xui_item.child_xui_items:
            self._add_node_to_tree(child, tree_item)

    def _on_tree_selection(self):
        if self.syncing or not self.canvas_container:
            return
        selected = self.selectedItems()
        if selected:
            xui_item = selected[0].data(0, Qt.UserRole)
            if xui_item and xui_item.scene():
                self.syncing = True
                self.canvas_container.scene.clearSelection()
                xui_item.setSelected(True)
                self.syncing = False
                self.canvas_container.item_selected_signal.emit(xui_item)

    def select_item_from_canvas(self, xui_item):
        if self.syncing:
            return
        self.syncing = True
        self.clearSelection()
        if xui_item:
            it = QTreeWidgetItemIterator(self)
            while it.value():
                if it.value().data(0, Qt.UserRole) == xui_item:
                    it.value().setSelected(True)
                    self.scrollToItem(it.value())
                    break
                it += 1
        self.syncing = False