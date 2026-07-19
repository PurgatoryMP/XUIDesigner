"""
This module provides the CanvasContainer, a specialized QGraphicsView that serves
as the primary visual workspace for designing user interfaces. It handles custom
grid rendering, dynamic edge rulers, drag-and-drop creation of XUI items,
and hierarchy re-parenting.
"""

from typing import Any, Optional

from PySide6.QtCore import QLineF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from graphics_item import XUIGraphicsItem


class CanvasContainer(QGraphicsView):
    """The main interactive visual workspace for rendering and editing XUI layouts.

    Supports configurable grid snapping, dynamic viewport rulers, internal item
    re-parenting via drag-and-drop, and recursive item deletion.

    Attributes:
        item_selected_signal (Signal): Emitted with the selected XUIGraphicsItem (or None).
        item_modified_signal (Signal): Emitted when an item's geometry or hierarchy changes.
        scene (QGraphicsScene): The underlying Qt scene managing 2D graphical items.
        grid_snapping_enabled (bool): Toggle for snapping dropped/moved items to the grid.
        grid_size (int): The distance in pixels between grid lines.
        root_container_instance (Optional[XUIGraphicsItem]): The primary root element of the layout.
    """

    item_selected_signal = Signal(object)
    item_modified_signal = Signal(object)

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initializes the CanvasContainer, its scene, and visual rendering properties.

        Args:
            parent: The parent Qt widget, if any.
        """
        super().__init__(parent)

        # Initialize fixed-size scene and bind a back-reference to this view
        self.scene = QGraphicsScene(0, 0, 1200, 900, self)
        self.scene.canvas_container = self
        self.setScene(self.scene)

        # Configure grid defaults
        self.grid_snapping_enabled: bool = True
        self.grid_size: int = 10
        self.root_container_instance: Optional[XUIGraphicsItem] = None

        # Enable drag-and-drop and set baseline rendering behaviors
        self.setAcceptDrops(True)
        self.setBackgroundBrush(QBrush(QColor("#141414")))
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.scene.selectionChanged.connect(self._on_selection_changed)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Renders the workspace background and dynamic snapping grid lines.

        Args:
            painter: The QPainter instance used for drawing.
            rect: The exposed rectangle of the viewport that needs redrawing.
        """
        super().drawBackground(painter, rect)
        grid_size = getattr(self, 'grid_size', 10)
        if grid_size <= 0:
            return

        # Align starting drawing coordinates to the nearest grid increment
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        # Generate vertical and horizontal grid lines spanning the visible area
        lines = []
        for x in range(left, int(rect.right()), grid_size):
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), grid_size):
            lines.append(QLineF(rect.left(), y, rect.right(), y))

        painter.setPen(QPen(QColor("#1f1f1f"), 1))
        painter.drawLines(lines)

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """Renders interactive coordinate rulers along the top and left viewport edges.

        The rulers stay dynamically mapped to viewport boundaries even while panning
        or zooming across the underlying scene.

        Args:
            painter: The QPainter instance used for drawing.
            rect: The exposed rectangle of the viewport that needs redrawing.
        """
        super().drawForeground(painter, rect)
        painter.save()

        # Visual styling for rulers and measurement labels
        ruler_bg = QColor("#222222")
        tick_color = QColor("#888888")
        text_color = QColor("#CCCCCC")
        painter.setFont(QFont("SansSerif", 7))

        # Map the top-left corner of the view to scene coordinates to anchor rulers
        top_left_scene = self.mapToScene(0, 0)
        top_y = top_left_scene.y()
        left_x = top_left_scene.x()

        # --- HORIZONTAL TOP RULER ---
        painter.fillRect(QRectF(left_x, top_y, rect.width(), 20), ruler_bg)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(QLineF(left_x, top_y + 20, left_x + rect.width(), top_y + 20))

        start_x = int(left_x) - (int(left_x) % 10)
        for x in range(start_x, int(left_x + rect.width()), 10):
            if x < left_x + 20:
                continue
            if x % 100 == 0:
                painter.setPen(QPen(tick_color, 1))
                painter.drawLine(QLineF(x, top_y + 10, x, top_y + 20))
                painter.setPen(QPen(text_color, 1))
                painter.drawText(QRectF(x + 2, top_y, 40, 12), Qt.AlignLeft | Qt.AlignTop, str(x))
            elif x % 50 == 0:
                painter.setPen(QPen(tick_color, 1))
                painter.drawLine(QLineF(x, top_y + 13, x, top_y + 20))
            else:
                painter.setPen(QPen(QColor("#555555"), 1))
                painter.drawLine(QLineF(x, top_y + 16, x, top_y + 20))

        # --- VERTICAL LEFT RULER ---
        painter.fillRect(QRectF(left_x, top_y, 20, rect.height()), ruler_bg)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(QLineF(left_x + 20, top_y, left_x + 20, top_y + rect.height()))

        start_y = int(top_y) - (int(top_y) % 10)
        for y in range(start_y, int(top_y + rect.height()), 10):
            if y < top_y + 20:
                continue
            if y % 100 == 0:
                painter.setPen(QPen(tick_color, 1))
                painter.drawLine(QLineF(left_x + 10, y, left_x + 20, y))
                painter.setPen(QPen(text_color, 1))
                painter.drawText(QRectF(left_x + 2, y + 2, 18, 12), Qt.AlignLeft | Qt.AlignTop, str(y))
            elif y % 50 == 0:
                painter.setPen(QPen(tick_color, 1))
                painter.drawLine(QLineF(left_x + 13, y, left_x + 20, y))
            else:
                painter.setPen(QPen(QColor("#555555"), 1))
                painter.drawLine(QLineF(left_x + 16, y, left_x + 20, y))

        # --- CORNER INTERSECTION BOX ---
        painter.fillRect(QRectF(left_x, top_y, 20, 20), QColor("#181818"))
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.drawRect(QRectF(left_x, top_y, 20, 20))

        painter.restore()

    def dragEnterEvent(self, event: Any) -> None:
        """Validates incoming drag events when elements enter the viewport.

        Args:
            event: The QDragEnterEvent containing mime payload data.
        """
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: Any) -> None:
        """Processes drag movement events across the canvas area.

        Args:
            event: The QDragMoveEvent containing current mouse coordinates.
        """
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        """Handles dropping UI widget tags onto the canvas or into existing container items.

        Instantiates new XUIGraphicsItems, handles tab panel automatic routing,
        calculates local coordinate snapping, and updates the layout hierarchy.

        Args:
            event: The QDropEvent containing drop coordinates and text mime payload.
        """
        tag_name = event.mimeData().text()
        scene_pos = self.mapToScene(event.pos())

        # Determine what is under the cursor (the parent container, if any)
        parent_item = self.scene.itemAt(scene_pos, self.transform())

        # Fetch dynamic grid settings once at the top
        grid_size = getattr(self, 'grid_size', 10)
        snapping_enabled = getattr(self, 'grid_snapping_enabled', True)

        if isinstance(parent_item, XUIGraphicsItem):
            # --- TAB CONTAINER DROP REDIRECTION ---
            if (
                    parent_item.tag_name == "tab_container"
                    and tag_name not in ["panel", "layout_panel"]
            ):
                tabs = [
                    c for c in parent_item.child_xui_items
                    if c.tag_name in ["panel", "layout_panel"]
                ]
                if tabs:
                    # Redirect drop target to the currently active tab panel
                    parent_item = tabs[parent_item.active_tab_index]
                else:
                    # If no tab panel exists yet, automatically create Tab 1
                    tab_height = int(parent_item.attributes.get("tab_height", 21))
                    tab_panel = XUIGraphicsItem("panel", {
                        "name": "tab_1",
                        "label": "Tab 1",
                        "left": "0",
                        "top": str(tab_height),
                        "width": parent_item.attributes.get("width", "250"),
                        "height": str(
                            max(
                                10,
                                int(parent_item.attributes.get("height", "180")) - tab_height
                            )
                        )
                    })
                    parent_item.add_child_item(tab_panel)
                    parent_item = tab_panel

            # Convert absolute scene mouse position to the parent's local coordinate space
            local_pos = parent_item.mapFromScene(scene_pos)

            # Snap using local_pos so items align properly inside containers
            if snapping_enabled and grid_size > 0:
                local_x = max(0.0, round(local_pos.x() / grid_size) * grid_size)
                local_y = max(0.0, round(local_pos.y() / grid_size) * grid_size)
            else:
                local_x = max(0.0, local_pos.x())
                local_y = max(0.0, local_pos.y())

            # Create the item directly at the newly mapped local coordinates
            new_item = XUIGraphicsItem(
                tag_name, {"left": str(int(local_x)), "top": str(int(local_y))}
            )
            new_item.setPos(local_x, local_y)

            # Nest it inside the target container/panel
            parent_item.add_child_item(new_item)
            new_item.sync_attributes_to_geometry()

        else:
            # Apply dynamic slider grid and toggle to root canvas drops
            if snapping_enabled and grid_size > 0:
                x = max(20.0, round(scene_pos.x() / grid_size) * grid_size)
                y = max(20.0, round(scene_pos.y() / grid_size) * grid_size)
            else:
                x = max(20.0, scene_pos.x())
                y = max(20.0, scene_pos.y())

            new_item = XUIGraphicsItem(tag_name, {"left": str(int(x)), "top": str(int(y))})
            new_item.setPos(x, y)

            if self.root_container_instance is None:
                self.root_container_instance = new_item
            self.scene.addItem(new_item)

        self.scene.clearSelection()
        new_item.setSelected(True)
        self.item_modified_signal.emit(new_item)
        event.acceptProposedAction()

    def delete_item(self, item: Any) -> None:
        """Recursively removes an XUIGraphicsItem and all its children from the canvas.

        Args:
            item: The target XUIGraphicsItem instance to destroy.
        """
        if not item or not item.scene():
            return

        # Create a shallow copy of the list to safely iterate during deletion
        children_copy = list(item.child_xui_items)
        for child in children_copy:
            self.delete_item(child)

        parent = item.parentItem()
        if isinstance(parent, XUIGraphicsItem):
            parent.remove_child_item(item)
        elif self.root_container_instance == item:
            self.root_container_instance = None

        self.scene.removeItem(item)
        self.scene.clearSelection()
        self.item_selected_signal.emit(None)
        self.item_modified_signal.emit(None)

    def keyPressEvent(self, event: Any) -> None:
        """Listens for keyboard shortcuts, allowing quick deletion of selected items.

        Args:
            event: The QKeyEvent containing key press payload data.
        """
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            selected = self.scene.selectedItems()
            if selected and isinstance(selected[0], XUIGraphicsItem):
                self.delete_item(selected[0])
                return
        super().keyPressEvent(event)

    def _on_selection_changed(self) -> None:
        """Internal slot triggered when the scene's selection changes. Emits item_selected_signal."""
        selected = self.scene.selectedItems()
        if selected:
            self.item_selected_signal.emit(selected[0])
        else:
            self.item_selected_signal.emit(None)

    def notify_item_changed(self, item: Any) -> None:
        """External utility method allowing external widgets to trigger modification updates.

        Args:
            item: The XUIGraphicsItem that underwent external modification.
        """
        self.item_modified_signal.emit(item)

    def clear_canvas(self) -> None:
        """Removes all items from the active scene and resets the root container tracker."""
        self.scene.clear()
        self.root_container_instance = None