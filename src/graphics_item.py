# graphics_item.py
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QCursor, QFont
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem
from registry import LLVIEW_PARAMS, LLUICTRL_PARAMS, XUI_REGISTRY
from textures import TextureManager, draw_9_slice


class XUIGraphicsItem(QGraphicsRectItem):
    def __init__(self, tag_name, attributes=None, parent_item=None):
        super().__init__(parent_item)
        self.tag_name = tag_name
        self.attributes = attributes or {}

        # 1. Inherit parameters based on schema registry
        target_params = {}
        for cat_name, widgets in XUI_REGISTRY.items():
            if tag_name in widgets:
                target_params = widgets[tag_name].get("params", {})
                if "label" in widgets[tag_name] and not self.attributes.get("label"):
                    self.attributes["label"] = widgets[tag_name]["label"]
                if "width" in widgets[tag_name] and "width" not in self.attributes:
                    self.attributes["width"] = str(widgets[tag_name]["width"])
                if "height" in widgets[tag_name] and "height" not in self.attributes:
                    self.attributes["height"] = str(widgets[tag_name]["height"])
                break

        # If not specialized, default to LLView / LLUICtrl params
        if not target_params:
            target_params = LLUICTRL_PARAMS if tag_name != "view" else LLVIEW_PARAMS

        # Populate defaults
        for attr, meta in target_params.items():
            if attr not in self.attributes and meta.get("default", "") != "":
                self.attributes[attr] = meta["default"]

        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.child_xui_items = []
        self.resize_handle_size = 6
        self.resizing = False
        self.resize_dir = None

        self.sync_geometry_to_attributes()

    def sync_geometry_to_attributes(self):
        try:
            w = float(self.attributes.get("width", 100))
            h = float(self.attributes.get("height", 20))
            self.setRect(0, 0, w, h)
        except ValueError:
            self.setRect(0, 0, 100, 20)

    def sync_attributes_to_geometry(self):
        rect = self.rect()
        pos = self.pos()
        self.attributes["width"] = str(int(rect.width()))
        self.attributes["height"] = str(int(rect.height()))
        self.attributes["left"] = str(int(pos.x()))
        self.attributes["top"] = str(int(pos.y()))

    def add_child_item(self, child_item):
        if child_item not in self.child_xui_items:
            self.child_xui_items.append(child_item)
            child_item.setParentItem(self)

    def remove_child_item(self, child_item):
        if child_item in self.child_xui_items:
            self.child_xui_items.remove(child_item)
            child_item.setParentItem(None)

    def _get_delete_rect(self):
        """Returns the bounding rectangle for the red 'X' badge."""
        rect = self.rect()
        return QRectF(rect.width() - 10, -10, 18, 18)

    def boundingRect(self):
        """
        CRITICAL FIX: Extends the reported bounding box by 12 pixels in all directions.
        This guarantees Qt properly erases the protruding red 'X' badge and resize handles
        when dragging the item across the screen!
        """
        return self.rect().adjusted(-12, -12, 12, 12)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, False)
        rect = self.rect()
        tm = TextureManager.get()

        if self.tag_name in ["floater", "multi_floater"]:
            bg_pix = tm.get_pixmap("floater_bg")
            if bg_pix:
                draw_9_slice(painter, bg_pix, rect, 8, 20, 8, 8)
            else:
                painter.fillRect(rect, QColor("#1c1c1e"))
                painter.setPen(QPen(QColor("#555555"), 1))
                painter.drawRect(rect)
            header_rect = QRectF(rect.x(), rect.y(), rect.width(), 20)
            header_pix = tm.get_pixmap("floater_header")
            if header_pix:
                draw_9_slice(painter, header_pix, header_rect, 4, 4, 4, 4)
            else:
                painter.fillRect(header_rect, QColor("#005588"))
            painter.setPen(QPen(QColor("#FFFFFF")))
            title = self.attributes.get("title") or self.attributes.get("name", "FLOATER")
            painter.drawText(header_rect.adjusted(8, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, title)

        elif self.tag_name in ["button", "flyout_button", "split_button"]:
            btn_pix = tm.get_pixmap("button_off")
            if btn_pix:
                draw_9_slice(painter, btn_pix, rect, 6, 6, 6, 6)
            else:
                painter.fillRect(rect, QColor("#4e5d6c"))
                painter.setPen(QPen(QColor("#2b333b"), 1))
                painter.drawRect(rect)
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.drawText(rect, Qt.AlignCenter, self.attributes.get("label", "Button"))

        elif self.tag_name in ["line_editor", "search_editor", "spinner", "combo_box"]:
            edit_pix = tm.get_pixmap("line_editor") if self.tag_name != "combo_box" else tm.get_pixmap("combo_box")
            if edit_pix:
                draw_9_slice(painter, edit_pix, rect, 4, 4, 4, 4)
            else:
                painter.fillRect(rect, QColor("#111111"))
                painter.setPen(QPen(QColor("#444444"), 1))
                painter.drawRect(rect)
            painter.setPen(QPen(QColor("#CCCCCC")))
            text = self.attributes.get("initial_value", "") or self.attributes.get("value", "") or self.attributes.get("label", "")
            if not text and self.tag_name == "search_editor":
                text = "Search..."
            painter.drawText(rect.adjusted(6, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, text)

        elif self.tag_name == "check_box":
            chk_pix = tm.get_pixmap("checkbox_off")
            chk_rect = QRectF(rect.x() + 2, rect.y() + (rect.height() - 14) / 2, 14, 14)
            if chk_pix:
                painter.drawPixmap(chk_rect, chk_pix, QRectF(0, 0, chk_pix.width(), chk_pix.height()))
            else:
                painter.fillRect(chk_rect, QColor("#222222"))
                painter.setPen(QPen(QColor("#888888"), 1))
                painter.drawRect(chk_rect)
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.drawText(QRectF(rect.x() + 20, rect.y(), rect.width() - 20, rect.height()), Qt.AlignLeft | Qt.AlignVCenter, self.attributes.get("label", "Check Box"))

        elif self.tag_name in ["panel", "layout_panel", "tab_container", "accordion"]:
            panel_pix = tm.get_pixmap("panel_bg")
            if panel_pix:
                draw_9_slice(painter, panel_pix, rect, 4, 4, 4, 4)
            else:
                painter.fillRect(rect, QColor("#2d2d2d" if self.tag_name == "panel" else "#252525"))
                painter.setPen(QPen(QColor("#3d3d3d"), 1))
                painter.drawRect(rect)
            if self.attributes.get("label"):
                painter.setPen(QPen(QColor("#AAAAAA")))
                painter.drawText(rect.adjusted(6, 4, 0, 0), Qt.AlignLeft | Qt.AlignTop, self.attributes.get("label"))

        else:
            if self.tag_name == "text":
                painter.setPen(QPen(QColor("#FFFFFF")))
                painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, self.attributes.get("label", "Text Label"))
            else:
                painter.fillRect(rect, QColor("#3a3a3a"))
                painter.setPen(QPen(QColor("#555555"), 1))
                painter.drawRect(rect)
                painter.setPen(QPen(QColor("#FFFFFF")))
                painter.drawText(rect, Qt.AlignCenter, f"<{self.tag_name}>")

        if self.isSelected():
            painter.setPen(QPen(QColor("#00FF00"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
            self._draw_handles(painter)

    def _draw_handles(self, painter):
        painter.setBrush(QBrush(QColor("#00FF00")))
        painter.setPen(QPen(QColor("#000000"), 1))
        rect = self.rect()
        hs = self.resize_handle_size

        for h in [
            QRectF(0, 0, hs, hs),
            QRectF(rect.width() - hs, 0, hs, hs),
            QRectF(0, rect.height() - hs, hs, hs),
            QRectF(rect.width() - hs, rect.height() - hs, hs, hs)
        ]:
            painter.drawRect(h)

        # Red 'X' badge
        del_rect = self._get_delete_rect()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QBrush(QColor("#D32F2F")))
        painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
        painter.drawEllipse(del_rect)
        painter.setFont(QFont("SansSerif", 8, QFont.Bold))
        painter.drawText(del_rect, Qt.AlignCenter, "X")

    def hoverMoveEvent(self, event):
        if not self.isSelected():
            self.setCursor(QCursor(Qt.ArrowCursor))
            return super().hoverMoveEvent(event)
        pos = event.pos()
        rect = self.rect()
        hs = self.resize_handle_size
        if self._get_delete_rect().contains(pos):
            self.setCursor(QCursor(Qt.PointingHandCursor))
        elif QRectF(0, 0, hs, hs).contains(pos) or QRectF(rect.width() - hs, rect.height() - hs, hs, hs).contains(pos):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif QRectF(rect.width() - hs, 0, hs, hs).contains(pos) or QRectF(0, rect.height() - hs, hs, hs).contains(pos):
            self.setCursor(QCursor(Qt.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.SizeAllCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            pos = event.pos()
            rect = self.rect()
            hs = self.resize_handle_size
            if self._get_delete_rect().contains(pos):
                if self.scene() and hasattr(self.scene(), 'canvas_container'):
                    self.scene().canvas_container.delete_item(self)
                event.accept()
                return
            if QRectF(rect.width() - hs, rect.height() - hs, hs, hs).contains(pos):
                self.resizing = True
                self.resize_dir = "BR"
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing and self.resize_dir == "BR":
            new_w = max(20, event.pos().x())
            new_h = max(15, event.pos().y())
            self.setRect(0, 0, new_w, new_h)
            self.sync_attributes_to_geometry()
            self.scene().update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            self.resize_dir = None
            self.sync_attributes_to_geometry()
            if hasattr(self.scene(), 'canvas_container') and self.scene().canvas_container:
                self.scene().canvas_container.notify_item_changed(self)
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            snapped_x = round(new_pos.x() / 10.0) * 10.0
            snapped_y = round(new_pos.y() / 10.0) * 10.0
            self.attributes["left"] = str(int(snapped_x))
            self.attributes["top"] = str(int(snapped_y))
            if hasattr(self.scene(), 'canvas_container') and self.scene().canvas_container:
                self.scene().canvas_container.notify_item_changed(self)
            return QPointF(snapped_x, snapped_y)
        return super().itemChange(change, value)