from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QAbstractItemView
)
from graphics_item import XUIGraphicsItem


class SceneTreeWidget(QTreeWidget):
    tree_refreshed = Signal()

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

        # PERFORMANCE FIX: Debounce Timer for Tree Rebuilding
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(150)
        self.refresh_timer.timeout.connect(self._do_refresh_tree)

    def set_canvas(self, canvas):
        self.canvas_container = canvas
        canvas.item_selected_signal.connect(self.select_item_from_canvas)
        canvas.item_modified_signal.connect(self.refresh_tree)

    def refresh_tree(self, _ignored=None):
        self.refresh_timer.start()

    def _do_refresh_tree(self):
        if self.syncing or not self.canvas_container:
            return
        self.syncing = True
        selected_xui = self.canvas_container.scene.selectedItems()[
            0] if self.canvas_container.scene.selectedItems() else None

        self.clear()
        if not self.canvas_container.root_container_instance:
            self.syncing = False
            self.tree_refreshed.emit()
            return

        def build_tree_node(xui_item, parent_widget):
            # --- FIX: Avoid printing 'unnamed' if the widget has a valid label or tag name ---
            name_val = xui_item.attributes.get("name", "")
            label_val = xui_item.attributes.get("label", "")

            if name_val and name_val != "unnamed":
                label = name_val
            elif label_val:
                label = label_val
            else:
                label = f"<{xui_item.tag_name}>"

            item = QTreeWidgetItem(parent_widget, [label])
            item.setData(0, Qt.UserRole, xui_item)

            if getattr(xui_item, 'is_imported_root', False) or "filename" in xui_item.attributes:
                item.setForeground(0, QBrush(QColor("#00FF00")))

            if xui_item == selected_xui:
                item.setSelected(True)

            for child in xui_item.child_xui_items:
                build_tree_node(child, item)
            return item

        root_tree_item = build_tree_node(self.canvas_container.root_container_instance, self)
        root_tree_item.setExpanded(True)
        self.expandAll()
        self.syncing = False
        self.tree_refreshed.emit()

    def _sync_dom_to_canvas_hierarchy(self):
        """Rebuilds XUIGraphicsItem parent-child array ordering and Z-values to match visual QTreeWidget order."""
        if not self.canvas_container or not self.canvas_container.root_container_instance:
            return

        def sync_item_children(tree_item):
            xui_item = tree_item.data(0, Qt.UserRole)
            if not xui_item or not isinstance(xui_item, XUIGraphicsItem):
                return

            new_children = []
            for i in range(tree_item.childCount()):
                child_tree_item = tree_item.child(i)
                child_xui = child_tree_item.data(0, Qt.UserRole)
                if child_xui and isinstance(child_xui, XUIGraphicsItem):
                    new_children.append(child_xui)
                    if child_xui.parentItem() != xui_item:
                        child_xui.setParentItem(xui_item)
                    sync_item_children(child_tree_item)

            xui_item.child_xui_items = new_children
            xui_item.update_z_orders()

        root_tree_item = self.topLevelItem(0)
        if root_tree_item:
            sync_item_children(root_tree_item)

    def dropEvent(self, event):
        dragged_item = self.currentItem()
        if not dragged_item:
            super().dropEvent(event)
            return

        dragged_xui = dragged_item.data(0, Qt.UserRole)
        target_item = self.itemAt(event.pos())
        if not target_item or not dragged_xui:
            super().dropEvent(event)
            return

        target_xui = target_item.data(0, Qt.UserRole)
        drop_pos = self.dropIndicatorPosition()

        if drop_pos == QAbstractItemView.OnItem:
            new_parent_xui = target_xui
        else:
            new_parent_xui = target_xui.parentItem() if isinstance(target_xui,
                                                                   XUIGraphicsItem) and target_xui.parentItem() else self.canvas_container.root_container_instance

        super().dropEvent(event)
        self._sync_dom_to_canvas_hierarchy()

        if isinstance(new_parent_xui, XUIGraphicsItem):
            rel_pos = dragged_xui.scenePos() - new_parent_xui.scenePos()
            dragged_xui.setPos(rel_pos)
            dragged_xui.sync_attributes_to_geometry()

        if self.canvas_container:
            self.canvas_container.item_modified_signal.emit(dragged_xui)
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
                item = it.value()
                if item.data(0, Qt.UserRole) == xui_item:
                    item.setSelected(True)
                    self.setCurrentItem(item)  # Sets active focus on the tree node
                    self.scrollToItem(item, QAbstractItemView.PositionAtCenter)  # Auto-scrolls into view
                    break
                it += 1
        self.syncing = False