from PySide6.QtCore import Qt, Signal, QLineF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from graphics_item import XUIGraphicsItem


class CanvasContainer(QGraphicsView):
    item_selected_signal = Signal(object)
    item_modified_signal = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(0, 0, 1200, 900, self)
        self.scene.canvas_container = self
        self.setScene(self.scene)

        self.root_container_instance = None
        self.setAcceptDrops(True)
        self.setBackgroundBrush(QBrush(QColor("#141414")))
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.scene.selectionChanged.connect(self._on_selection_changed)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        grid_size = 10
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        lines = []
        for x in range(left, int(rect.right()), grid_size):
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), grid_size):
            lines.append(QLineF(rect.left(), y, rect.right(), y))

        painter.setPen(QPen(QColor("#1f1f1f"), 1))
        painter.drawLines(lines)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        painter.save()

        ruler_bg = QColor("#222222")
        tick_color = QColor("#888888")
        text_color = QColor("#CCCCCC")
        painter.setFont(QFont("SansSerif", 7))

        top_left_scene = self.mapToScene(0, 0)
        top_y = top_left_scene.y()
        left_x = top_left_scene.x()

        painter.fillRect(QRectF(left_x, top_y, rect.width(), 20), ruler_bg)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(QLineF(left_x, top_y + 20, left_x + rect.width(), top_y + 20))

        start_x = int(left_x) - (int(left_x) % 10)
        for x in range(start_x, int(left_x + rect.width()), 10):
            if x < left_x + 20: continue
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

        painter.fillRect(QRectF(left_x, top_y, 20, rect.height()), ruler_bg)
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(QLineF(left_x + 20, top_y, left_x + 20, top_y + rect.height()))

        start_y = int(top_y) - (int(top_y) % 10)
        for y in range(start_y, int(top_y + rect.height()), 10):
            if y < top_y + 20: continue
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

        painter.fillRect(QRectF(left_x, top_y, 20, 20), QColor("#181818"))
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.drawRect(QRectF(left_x, top_y, 20, 20))

        painter.restore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        tag_name = event.mimeData().text()
        scene_pos = self.mapToScene(event.pos())

        # Determine what is under the cursor (the parent container, if any)
        parent_item = self.scene.itemAt(scene_pos, self.transform())

        if isinstance(parent_item, XUIGraphicsItem):
            # --- TAB CONTAINER DROP REDIRECTION ---
            if parent_item.tag_name == "tab_container" and tag_name not in ["panel", "layout_panel"]:
                tabs = [c for c in parent_item.child_xui_items if c.tag_name in ["panel", "layout_panel"]]
                if tabs:
                    # Redirect drop target to the currently active tab panel
                    parent_item = tabs[parent_item.active_tab_index]
                else:
                    # If no tab panel exists yet, automatically create Tab 1
                    tab_height = int(parent_item.attributes.get("tab_height", 21))
                    tab_panel = XUIGraphicsItem("panel", {
                        "name": "tab_1", "label": "Tab 1",
                        "left": "0", "top": str(tab_height),
                        "width": parent_item.attributes.get("width", "250"),
                        "height": str(max(10, int(parent_item.attributes.get("height", "180")) - tab_height))
                    })
                    parent_item.add_child_item(tab_panel)
                    parent_item = tab_panel

            # Convert absolute scene mouse position to the parent's local coordinate space
            local_pos = parent_item.mapFromScene(scene_pos)

            # Snap to parent's internal 10x10 grid without drifting
            local_x = max(0.0, round(local_pos.x() / 10.0) * 10.0)
            local_y = max(0.0, round(local_pos.y() / 10.0) * 10.0)

            # Create the item directly at the newly mapped local coordinates
            new_item = XUIGraphicsItem(tag_name, {"left": str(int(local_x)), "top": str(int(local_y))})
            new_item.setPos(local_x, local_y)

            # Nest it inside the target container/panel
            parent_item.add_child_item(new_item)
            new_item.sync_attributes_to_geometry()

        else:
            # Dropping on the main canvas (root container)
            x = max(20.0, round(scene_pos.x() / 10.0) * 10.0)
            y = max(20.0, round(scene_pos.y() / 10.0) * 10.0)

            new_item = XUIGraphicsItem(tag_name, {"left": str(int(x)), "top": str(int(y))})
            new_item.setPos(x, y)

            if self.root_container_instance is None:
                self.root_container_instance = new_item
            self.scene.addItem(new_item)

        self.scene.clearSelection()
        new_item.setSelected(True)
        self.item_modified_signal.emit(new_item)
        event.acceptProposedAction()

    def delete_item(self, item):
        if not item or not item.scene():
            return

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

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            selected = self.scene.selectedItems()
            if selected and isinstance(selected[0], XUIGraphicsItem):
                self.delete_item(selected[0])
                return
        super().keyPressEvent(event)

    def _on_selection_changed(self):
        selected = self.scene.selectedItems()
        if selected:
            self.item_selected_signal.emit(selected[0])
        else:
            self.item_selected_signal.emit(None)

    def notify_item_changed(self, item):
        self.item_modified_signal.emit(item)

    def clear_canvas(self):
        self.scene.clear()
        self.root_container_instance = None