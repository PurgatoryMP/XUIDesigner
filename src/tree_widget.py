from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QAbstractItemView
)
from graphics_item import XUIGraphicsItem


class SceneTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("XUI DOM Hierarchy")
        self.itemSelectionChanged.connect(self._on_tree_selection)
        self.canvas_container = None
        self.syncing = False

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

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

    def dragEnterEvent(self, event):
        super().dragEnterEvent(event)
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        event.acceptProposedAction()

    def dropEvent(self, event):
        selected = self.selectedItems()
        if not selected:
            return

        dragged_tree_item = selected[0]
        dragged_xui = dragged_tree_item.data(0, Qt.UserRole)

        target_tree_item = self.itemAt(event.pos())
        if not target_tree_item or target_tree_item == dragged_tree_item:
            event.ignore()
            return

        target_xui = target_tree_item.data(0, Qt.UserRole)
        if not dragged_xui or not target_xui:
            event.ignore()
            return

        if self.canvas_container and self.canvas_container.root_container_instance == dragged_xui:
            event.ignore()
            return

        curr = target_xui
        while curr:
            if curr == dragged_xui:
                event.ignore()
                return
            curr = curr.parentItem() if isinstance(curr.parentItem(), XUIGraphicsItem) else None

        old_parent = dragged_xui.parentItem()
        if isinstance(old_parent, XUIGraphicsItem):
            old_parent.remove_child_item(dragged_xui)

        pos_mode = self.dropIndicatorPosition()

        if pos_mode == QAbstractItemView.OnItem:

            # --- TAB CONTAINER DROP REDIRECTION ---
            if target_xui.tag_name == "tab_container" and dragged_xui.tag_name not in ["panel", "layout_panel"]:
                tabs = [c for c in target_xui.child_xui_items if c.tag_name in ["panel", "layout_panel"]]
                if tabs:
                    target_xui = tabs[target_xui.active_tab_index]

            target_xui.add_child_item(dragged_xui)
            new_parent = target_xui

        elif pos_mode in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
            new_parent = target_xui.parentItem()
            if not isinstance(new_parent, XUIGraphicsItem):
                new_parent = target_xui
                new_parent.add_child_item(dragged_xui)
            else:
                idx = new_parent.child_xui_items.index(target_xui) if target_xui in new_parent.child_xui_items else len(
                    new_parent.child_xui_items)
                if pos_mode == QAbstractItemView.BelowItem:
                    idx += 1
                if hasattr(new_parent, 'insert_child_item'):
                    new_parent.insert_child_item(idx, dragged_xui)
                else:
                    new_parent.add_child_item(dragged_xui)
        else:
            event.ignore()
            return

        if isinstance(new_parent, XUIGraphicsItem):
            rel_pos = dragged_xui.scenePos() - new_parent.scenePos()
            dragged_xui.setPos(rel_pos)
            dragged_xui.sync_attributes_to_geometry()

        if self.canvas_container:
            self.canvas_container.notify_item_changed(dragged_xui)
            self.canvas_container.scene.update()

        event.setDropAction(Qt.IgnoreAction)
        event.accept()

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