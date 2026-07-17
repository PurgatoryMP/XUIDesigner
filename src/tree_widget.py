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

        # Debounce Timer for Tree Rebuilding
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(150)
        self.refresh_timer.timeout.connect(self._do_refresh_tree)

    def set_canvas(self, canvas):
        try:
            self.canvas_container = canvas
            canvas.item_selected_signal.connect(self.select_item_from_canvas)
            canvas.item_modified_signal.connect(self.refresh_tree)
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget.set_canvas failed: {e}")

    def refresh_tree(self, _ignored=None):
        self.refresh_timer.start()

    def _do_refresh_tree(self):
        try:
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
                try:
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

                    for child in getattr(xui_item, 'child_xui_items', []):
                        build_tree_node(child, item)
                    return item
                except Exception as node_err:
                    print(
                        f"[Verbose Error] Error building tree node for <{getattr(xui_item, 'tag_name', 'unknown')}>: {node_err}")
                    return None

            root_tree_item = build_tree_node(self.canvas_container.root_container_instance, self)
            if root_tree_item:
                root_tree_item.setExpanded(True)
            self.expandAll()
            self.syncing = False
            self.tree_refreshed.emit()
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget._do_refresh_tree fatal exception: {e}")
            self.syncing = False

    def _sync_dom_to_canvas_hierarchy(self):
        """Rebuilds XUIGraphicsItem parent-child array ordering and Z-values to match visual QTreeWidget order."""
        try:
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

                # Trigger container layout updates when children are rearranged via tree dragging
                if xui_item.tag_name == "tab_container" and hasattr(xui_item, "update_tabs"):
                    xui_item.update_tabs()
                elif xui_item.tag_name in ("layout_stack", "layout_panel") and hasattr(xui_item, "update_layout_stack"):
                    xui_item.update_layout_stack()

            root_tree_item = self.topLevelItem(0)
            if root_tree_item:
                sync_item_children(root_tree_item)
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget._sync_dom_to_canvas_hierarchy exception: {e}")

    def dropEvent(self, event):
        try:
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
                new_parent_xui = target_xui.parentItem() if (isinstance(target_xui, XUIGraphicsItem) and target_xui.parentItem()) else self.canvas_container.root_container_instance

            super().dropEvent(event)
            self._sync_dom_to_canvas_hierarchy()

            if isinstance(new_parent_xui, XUIGraphicsItem) and isinstance(dragged_xui, XUIGraphicsItem):
                try:
                    rel_pos = dragged_xui.scenePos() - new_parent_xui.scenePos()
                    dragged_xui.setPos(rel_pos)
                    dragged_xui.sync_attributes_to_geometry()
                except Exception as geo_err:
                    print(f"[Verbose Error] Failed calculating dropped item relative geometry: {geo_err}")

            if self.canvas_container:
                self.canvas_container.item_modified_signal.emit(dragged_xui)
                self.canvas_container.scene.update()

            event.setDropAction(Qt.IgnoreAction)
            event.accept()
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget.dropEvent exception: {e}")
            event.ignore()

    def _on_tree_selection(self):
        try:
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
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget._on_tree_selection exception: {e}")
            self.syncing = False

    def select_item_from_canvas(self, xui_item):
        try:
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
                        self.setCurrentItem(item)
                        self.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                        break
                    it += 1
            self.syncing = False
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget.select_item_from_canvas exception: {e}")
            self.syncing = False
