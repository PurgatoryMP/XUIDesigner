"""DOM Hierarchy Tree View widget for the XUI Designer.

This module provides the SceneTreeWidget, which visually displays and allows
manipulation of the XUI DOM hierarchy. It handles two-way selection and structural
synchronization between the tree view and the graphical canvas.
"""

from typing import Any, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
)

from graphics_item import XUIGraphicsItem


class SceneTreeWidget(QTreeWidget):
    """A customized QTreeWidget for displaying and editing the XUI DOM hierarchy.

    Supports internal drag-and-drop for reparenting and reordering elements,
    debounced tree rebuilding to maintain performance during rapid updates, and
    bidirectional selection syncing with the editor canvas.

    Attributes:
        tree_refreshed (Signal): Emitted whenever the tree structure is fully rebuilt.
        canvas_container (Any): Reference to the main editor canvas container widget.
        syncing (bool): Flag used to prevent recursive feedback loops during signal updates.
        refresh_timer (QTimer): Debounce timer used to coalesce rapid refresh requests.
    """

    tree_refreshed = Signal()

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initializes the SceneTreeWidget and configures drag-and-drop behavior.

        Args:
            parent: The parent Qt widget, if any.
        """
        super().__init__(parent)
        self.setHeaderLabel("XUI DOM Hierarchy")
        self.itemSelectionChanged.connect(self._on_tree_selection)

        self.canvas_container: Optional[Any] = None
        self.syncing: bool = False

        # Enable internal drag and drop for DOM reparenting and reordering
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

        # Debounce Timer for Tree Rebuilding: prevents UI freezing during rapid DOM changes
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(150)
        self.refresh_timer.timeout.connect(self._do_refresh_tree)

    def set_canvas(self, canvas: Any) -> None:
        """Binds the tree widget to the main editor canvas and connects synchronization signals.

        Args:
            canvas: The main canvas container instance managing the QGraphicsScene.
        """
        try:
            self.canvas_container = canvas
            canvas.item_selected_signal.connect(self.select_item_from_canvas)
            canvas.item_modified_signal.connect(self.refresh_tree)
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget.set_canvas failed: {e}")

    def refresh_tree(self, _ignored: Optional[Any] = None) -> None:
        """Triggers a debounced refresh of the DOM tree.

        Args:
            _ignored: Optional parameter to accommodate signal emission payloads.
        """
        self.refresh_timer.start()

    def _do_refresh_tree(self) -> None:
        """Rebuilds the entire visual tree hierarchy from the canvas root container.

        This method clears existing items and recursively generates new tree nodes
        matching the current XUIGraphicsItem hierarchy on the canvas. Maintains
        currently selected items and highlights imported files.
        """
        try:
            if self.syncing or not self.canvas_container:
                return

            self.syncing = True

            # Preserve selection state across rebuilds if an item is currently selected
            selected_xui = (
                self.canvas_container.scene.selectedItems()[0]
                if self.canvas_container.scene.selectedItems()
                else None
            )

            self.clear()
            if not self.canvas_container.root_container_instance:
                self.syncing = False
                self.tree_refreshed.emit()
                return

            def build_tree_node(
                    xui_item: Any, parent_widget: Any
            ) -> Optional[QTreeWidgetItem]:
                """Recursively creates a QTreeWidgetItem for an XUIGraphicsItem and its children.

                Args:
                    xui_item: The data model/graphics item to create a node for.
                    parent_widget: The parent QTreeWidget or QTreeWidgetItem to attach to.

                Returns:
                    The created QTreeWidgetItem, or None if creation fails.
                """
                try:
                    name_val = xui_item.attributes.get("name", "")
                    label_val = xui_item.attributes.get("label", "")

                    # Determine display label priority: name -> label -> XML tag name
                    if name_val and name_val != "unnamed":
                        label = name_val
                    elif label_val:
                        label = label_val
                    else:
                        label = f"<{xui_item.tag_name}>"

                    item = QTreeWidgetItem(parent_widget, [label])
                    item.setData(0, Qt.UserRole, xui_item)

                    # Highlight imported root elements or items referencing external files in green
                    if (
                            getattr(xui_item, 'is_imported_root', False)
                            or "filename" in xui_item.attributes
                    ):
                        item.setForeground(0, QBrush(QColor("#00FF00")))

                    # Restore previous selection state
                    if xui_item == selected_xui:
                        item.setSelected(True)

                    # Recursively process child elements
                    for child in getattr(xui_item, 'child_xui_items', []):
                        build_tree_node(child, item)
                    return item
                except Exception as node_err:
                    print(
                        f"[Verbose Error] Error building tree node for "
                        f"<{getattr(xui_item, 'tag_name', 'unknown')}>: {node_err}"
                    )
                    return None

            # Build from the canvas root and expand all items by default
            root_tree_item = build_tree_node(
                self.canvas_container.root_container_instance, self
            )
            if root_tree_item:
                root_tree_item.setExpanded(True)
            self.expandAll()

            self.syncing = False
            self.tree_refreshed.emit()
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget._do_refresh_tree fatal exception: {e}")
            self.syncing = False

    def _sync_dom_to_canvas_hierarchy(self) -> None:
        """Rebuilds XUIGraphicsItem parent-child array ordering and Z-values.

        Updates the underlying graphics item relationships to match the visual
        ordering currently present in the QTreeWidget after a drag-and-drop operation.
        Also triggers layout recalculations for container widgets.
        """
        try:
            if not self.canvas_container or not self.canvas_container.root_container_instance:
                return

            def sync_item_children(tree_item: QTreeWidgetItem) -> None:
                """Recursively updates child arrays and parent pointers for a tree node.

                Args:
                    tree_item: The QTreeWidgetItem whose children need synchronization.
                """
                xui_item = tree_item.data(0, Qt.UserRole)
                if not xui_item or not isinstance(xui_item, XUIGraphicsItem):
                    return

                new_children = []
                for i in range(tree_item.childCount()):
                    child_tree_item = tree_item.child(i)
                    child_xui = child_tree_item.data(0, Qt.UserRole)
                    if child_xui and isinstance(child_xui, XUIGraphicsItem):
                        new_children.append(child_xui)
                        # Reparent canvas item if the tree structure was modified
                        if child_xui.parentItem() != xui_item:
                            child_xui.setParentItem(xui_item)
                        sync_item_children(child_tree_item)

                xui_item.child_xui_items = new_children
                xui_item.update_z_orders()

                # Trigger container layout updates when children are rearranged via tree dragging
                if xui_item.tag_name == "tab_container" and hasattr(xui_item, "update_tabs"):
                    xui_item.update_tabs()
                elif xui_item.tag_name in ("layout_stack", "layout_panel") and hasattr(
                        xui_item, "update_layout_stack"
                ):
                    xui_item.update_layout_stack()

            root_tree_item = self.topLevelItem(0)
            if root_tree_item:
                sync_item_children(root_tree_item)
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget._sync_dom_to_canvas_hierarchy exception: {e}")

    def dropEvent(self, event: Any) -> None:
        """Handles drag-and-drop drop events within the tree widget.

        Executes the visual tree reparenting, synchronizes the changes back to
        the underlying XUIGraphicsItem canvas hierarchy, and recalculates relative
        scene positions to prevent elements from jumping.

        Args:
            event: The QDropEvent containing drag payload and coordinates.
        """
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

            # Determine whether the drop target is becoming a parent or a sibling
            if drop_pos == QAbstractItemView.OnItem:
                new_parent_xui = target_xui
            else:
                new_parent_xui = (
                    target_xui.parentItem()
                    if (isinstance(target_xui, XUIGraphicsItem) and target_xui.parentItem())
                    else self.canvas_container.root_container_instance
                )

            # Perform the standard Qt tree item move
            super().dropEvent(event)

            # Push new hierarchy changes to the graphics scene
            self._sync_dom_to_canvas_hierarchy()

            # Recalculate relative scene positions for the reparented graphics item
            if isinstance(new_parent_xui, XUIGraphicsItem) and isinstance(
                    dragged_xui, XUIGraphicsItem
            ):
                try:
                    rel_pos = dragged_xui.scenePos() - new_parent_xui.scenePos()
                    dragged_xui.setPos(rel_pos)
                    dragged_xui.sync_attributes_to_geometry()
                except Exception as geo_err:
                    print(
                        f"[Verbose Error] Failed calculating dropped item relative geometry: {geo_err}"
                    )

            # Notify the canvas that an item was modified by the tree drop
            if self.canvas_container:
                self.canvas_container.item_modified_signal.emit(dragged_xui)
                self.canvas_container.scene.update()

            event.setDropAction(Qt.IgnoreAction)
            event.accept()
        except Exception as e:
            print(f"[Verbose Error] SceneTreeWidget.dropEvent exception: {e}")
            event.ignore()

    def _on_tree_selection(self) -> None:
        """Handles selection changes in the tree widget and syncs them to the canvas.

        Clears existing canvas selections and selects the corresponding XUIGraphicsItem
        in the graphics scene without triggering recursive selection loops.
        """
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

    def select_item_from_canvas(self, xui_item: Any) -> None:
        """Selects and scrolls to a tree item when the corresponding canvas item is selected.

        Args:
            xui_item: The XUIGraphicsItem that was selected on the canvas.
        """
        try:
            if self.syncing:
                return

            self.syncing = True
            self.clearSelection()

            if xui_item:
                # Iterate through all tree nodes to find the matching user role data
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