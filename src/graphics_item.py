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

        self.source_file = "layout.xml"
        self.is_imported_root = False
        self.active_tab_index = 0

        # Inherit parameters based on schema registry
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

        if not target_params:
            target_params = LLUICTRL_PARAMS if tag_name != "view" else LLVIEW_PARAMS

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
        self.non_visual_children = []
        self.inner_text = ""

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

        if "left_delta" not in self.attributes and "left_pad" not in self.attributes:
            self.attributes["left"] = str(int(pos.x()))
        if "top_delta" not in self.attributes and "top_pad" not in self.attributes:
            self.attributes["top"] = str(int(pos.y()))

    def resize_item(self, new_w, new_h):
        old_w = self.rect().width()
        old_h = self.rect().height()
        dw = new_w - old_w
        dh = new_h - old_h

        if dw == 0 and dh == 0:
            return

        self.setRect(0, 0, new_w, new_h)
        self.sync_attributes_to_geometry()

        # DELEGATE TO SMART CONTAINERS FIRST
        if self.tag_name == "tab_container":
            self.update_tabs()
        elif self.tag_name == "layout_stack":
            self.update_layout_stack()
        else:
            # Normal 'follows' cascade for raw items
            for child in self.child_xui_items:
                follows_str = child.attributes.get("follows", "left|top").lower()
                if follows_str == "all":
                    follows = ["left", "top", "right", "bottom"]
                else:
                    follows = follows_str.split("|")

                cx, cy = child.x(), child.y()
                cw, ch = child.rect().width(), child.rect().height()
                child_dw = child_dh = move_x = move_y = 0

                if "left" in follows and "right" in follows:
                    child_dw = dw
                elif "right" in follows and "left" not in follows:
                    move_x = dw

                if "top" in follows and "bottom" in follows:
                    child_dh = dh
                elif "bottom" in follows and "top" not in follows:
                    move_y = dh

                if move_x != 0 or move_y != 0:
                    child.setPos(cx + move_x, cy + move_y)
                    child.sync_attributes_to_geometry()

                if child_dw != 0 or child_dh != 0:
                    child.resize_item(cw + child_dw, ch + child_dh)

    # ------------------------------------------------------------------------
    # SMART CONTAINER MANAGERS
    # ------------------------------------------------------------------------
    def update_tabs(self):
        if self.tag_name != "tab_container": return

        tabs = [c for c in self.child_xui_items if c.tag_name in ["panel", "layout_panel"]]
        if self.active_tab_index >= len(tabs):
            self.active_tab_index = max(0, len(tabs) - 1)

        tab_height = int(self.attributes.get("tab_height", 21))
        container_w = self.attributes.get("width", "250")
        container_h = str(max(10, int(self.attributes.get("height", "180")) - tab_height - 2))

        for i, tab in enumerate(tabs):
            is_active = (i == self.active_tab_index)
            tab.setVisible(is_active)
            tab.setPos(2, tab_height + 2)
            tab.attributes["left"] = "2"
            tab.attributes["top"] = str(tab_height + 2)
            try:
                tab.resize_item(float(container_w) - 4, float(container_h))
            except ValueError:
                pass

    def update_layout_stack(self):
        """Forces layout panels to arrange linearly inside a layout stack, respecting XUI padding/borders."""
        if self.tag_name != "layout_stack": return

        orientation = self.attributes.get("orientation", "vertical")
        panels = [c for c in self.child_xui_items if c.tag_name in ["layout_panel", "panel"]]

        padding = int(self.attributes.get("padding", 0))
        border_size = int(self.attributes.get("border_size", 0))

        current_x = border_size
        current_y = border_size
        stack_w = max(10, self.rect().width() - (border_size * 2))
        stack_h = max(10, self.rect().height() - (border_size * 2))

        for panel in panels:
            panel.setPos(current_x, current_y)
            panel.attributes["left"] = str(int(current_x))
            panel.attributes["top"] = str(int(current_y))

            panel_w = panel.rect().width()
            panel_h = panel.rect().height()

            if orientation == "vertical":
                panel.resize_item(stack_w, panel_h)
                current_y += panel.rect().height() + padding
            else:
                panel.resize_item(panel_w, stack_h)
                current_x += panel.rect().width() + padding

    # ------------------------------------------------------------------------
    # RESTORED CHILD LOGIC
    # ------------------------------------------------------------------------
    def add_child_item(self, child_item):
        if child_item not in self.child_xui_items:
            self.child_xui_items.append(child_item)
            child_item.setParentItem(self)
        if self.tag_name == "tab_container":
            self.update_tabs()
        elif self.tag_name == "layout_stack":
            self.update_layout_stack()

    def insert_child_item(self, index, child_item):
        if child_item in self.child_xui_items:
            self.child_xui_items.remove(child_item)
        index = max(0, min(index, len(self.child_xui_items)))
        self.child_xui_items.insert(index, child_item)
        child_item.setParentItem(self)
        if self.tag_name == "tab_container":
            self.update_tabs()
        elif self.tag_name == "layout_stack":
            self.update_layout_stack()

    def remove_child_item(self, child_item):
        if child_item in self.child_xui_items:
            self.child_xui_items.remove(child_item)
            child_item.setParentItem(None)
        if self.tag_name == "tab_container":
            self.update_tabs()
        elif self.tag_name == "layout_stack":
            self.update_layout_stack()

    def _get_delete_rect(self):
        return QRectF(self.rect().width() - 10, -10, 18, 18)

    def boundingRect(self):
        return self.rect().adjusted(-12, -12, 12, 12)

    def _get_handles(self):
        r = self.rect()
        w, h, hs = r.width(), r.height(), self.resize_handle_size
        return {
            "TL": QRectF(0, 0, hs, hs),
            "T": QRectF(w / 2 - hs / 2, 0, hs, hs),
            "TR": QRectF(w - hs, 0, hs, hs),
            "R": QRectF(w - hs, h / 2 - hs / 2, hs, hs),
            "BR": QRectF(w - hs, h - hs, hs, hs),
            "B": QRectF(w / 2 - hs / 2, h - hs, hs, hs),
            "BL": QRectF(0, h - hs, hs, hs),
            "L": QRectF(0, h / 2 - hs / 2, hs, hs),
        }

    def _draw_handles(self, painter):
        painter.setBrush(QBrush(QColor("#00FF00")))
        painter.setPen(QPen(QColor("#000000"), 1))

        for handle in self._get_handles().values():
            painter.drawRect(handle)

        del_rect = self._get_delete_rect()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QBrush(QColor("#D32F2F")))
        painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
        painter.drawEllipse(del_rect)
        painter.setFont(QFont("SansSerif", 8, QFont.Bold))
        painter.drawText(del_rect, Qt.AlignCenter, "X")

    # ------------------------------------------------------------------------
    # EVENTS
    # ------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()

            if self.tag_name == "tab_container":
                tab_height = int(self.attributes.get("tab_height", 21))
                if pos.y() <= tab_height:
                    actual_panels = [c for c in self.child_xui_items if c.tag_name in ["panel", "layout_panel"]]
                    if actual_panels:
                        tab_x = 2
                        for i, tab_panel in enumerate(actual_panels):
                            tab_label = tab_panel.attributes.get("label", tab_panel.attributes.get("title",
                                                                                                   tab_panel.attributes.get(
                                                                                                       "name",
                                                                                                       "Unnamed Tab")))
                            min_w = int(self.attributes.get("tab_min_width", 60))
                            max_w = int(self.attributes.get("tab_max_width", 150))
                            calc_width = max(min_w, min(max_w, len(tab_label) * 7 + 20))

                            if tab_x <= pos.x() <= tab_x + calc_width:
                                self.active_tab_index = i
                                self.update_tabs()
                                self.scene().update()
                                super().mousePressEvent(event)
                                return
                            tab_x += calc_width

            if self.isSelected():
                if self._get_delete_rect().contains(pos):
                    if hasattr(self.scene(), 'canvas_container'):
                        self.scene().canvas_container.delete_item(self)
                    event.accept()
                    return

                handles = self._get_handles()
                for h_id, rect in handles.items():
                    if rect.contains(pos):
                        self.resizing = True
                        self.resize_dir = h_id
                        event.accept()
                        return

        super().mousePressEvent(event)

    def hoverMoveEvent(self, event):
        if not self.isSelected():
            self.setCursor(QCursor(Qt.ArrowCursor))
            return super().hoverMoveEvent(event)

        pos = event.pos()
        handles = self._get_handles()

        if self._get_delete_rect().contains(pos):
            self.setCursor(QCursor(Qt.PointingHandCursor))
        elif handles["TL"].contains(pos) or handles["BR"].contains(pos):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif handles["TR"].contains(pos) or handles["BL"].contains(pos):
            self.setCursor(QCursor(Qt.SizeBDiagCursor))
        elif handles["T"].contains(pos) or handles["B"].contains(pos):
            self.setCursor(QCursor(Qt.SizeVerCursor))
        elif handles["L"].contains(pos) or handles["R"].contains(pos):
            self.setCursor(QCursor(Qt.SizeHorCursor))
        else:
            self.setCursor(QCursor(Qt.SizeAllCursor))

        super().hoverMoveEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing and self.resize_dir:
            scene_pos = self.mapToScene(event.pos())
            parent_pos = self.parentItem().mapFromScene(scene_pos) if self.parentItem() else scene_pos

            snapped_x = round(parent_pos.x() / 10.0) * 10.0
            snapped_y = round(parent_pos.y() / 10.0) * 10.0

            cur_pos = self.pos()
            cur_rect = self.rect()

            new_x, new_y = cur_pos.x(), cur_pos.y()
            new_w, new_h = cur_rect.width(), cur_rect.height()

            if "L" in self.resize_dir:
                diff = snapped_x - cur_pos.x()
                new_w = max(10, cur_rect.width() - diff)
                if new_w > 10: new_x = snapped_x
            elif "R" in self.resize_dir:
                new_w = max(10, snapped_x - cur_pos.x())

            if "T" in self.resize_dir:
                diff = snapped_y - cur_pos.y()
                new_h = max(10, cur_rect.height() - diff)
                if new_h > 10: new_y = snapped_y
            elif "B" in self.resize_dir:
                new_h = max(10, snapped_y - cur_pos.y())

            if new_x != cur_pos.x() or new_y != cur_pos.y():
                self.setPos(new_x, new_y)
            if new_w != cur_rect.width() or new_h != cur_rect.height():
                self.resize_item(new_w, new_h)

            self.scene().update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            self.resize_dir = None
            self.sync_attributes_to_geometry()

            if self.tag_name == "tab_container":
                self.update_tabs()
            elif self.tag_name == "layout_stack":
                self.update_layout_stack()

            if hasattr(self.scene(), 'canvas_container'):
                self.scene().canvas_container.notify_item_changed(self)
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            snapped_x = round(new_pos.x() / 10.0) * 10.0
            snapped_y = round(new_pos.y() / 10.0) * 10.0

            parent = self.parentItem()
            idx = parent.child_xui_items.index(self) if isinstance(parent,
                                                                   XUIGraphicsItem) and self in parent.child_xui_items else -1
            prev_sib = parent.child_xui_items[idx - 1] if idx > 0 else None

            if "left_delta" in self.attributes and prev_sib:
                self.attributes["left_delta"] = str(int(snapped_x - prev_sib.x()))
            elif "left_pad" in self.attributes and prev_sib:
                self.attributes["left_pad"] = str(int(snapped_x - (prev_sib.x() + prev_sib.rect().width())))
            else:
                self.attributes["left"] = str(int(snapped_x))

            if "top_delta" in self.attributes and prev_sib:
                self.attributes["top_delta"] = str(int(snapped_y - prev_sib.y()))
            elif "top_pad" in self.attributes and prev_sib:
                self.attributes["top_pad"] = str(int(snapped_y - (prev_sib.y() + prev_sib.rect().height())))
            else:
                self.attributes["top"] = str(int(snapped_y))

            if hasattr(self.scene(), 'canvas_container') and self.scene().canvas_container:
                self.scene().canvas_container.notify_item_changed(self)
            return QPointF(snapped_x, snapped_y)
        return super().itemChange(change, value)

    def validate(self):
        errors, warnings = [], []
        if self.tag_name not in ["panel", "layout_panel", "text", "view_border", "icon", "window_shade", "accordion",
                                 "scroll_list"]:
            if not self.attributes.get("name"):
                warnings.append(f"Bad Practice: Missing 'name' attribute for {self.tag_name}.")

        if self.tag_name == "layout_panel":
            parent = self.parentItem()
            if not isinstance(parent, XUIGraphicsItem) or parent.tag_name != "layout_stack":
                errors.append(f"Syntax Error: <layout_panel> must be a direct child of <layout_stack>.")

        has_left, has_right = "left" in self.attributes, "right" in self.attributes
        follows = self.attributes.get("follows", "").lower()
        if has_left and has_right and "left" not in follows and "right" not in follows and "all" not in follows:
            warnings.append("Bad Practice: Opposing anchors (left & right) used without matching 'follows' flags.")

        return errors, warnings

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, False)
        rect = self.rect()
        tm = TextureManager.get()

        if self.tag_name in ["floater", "multi_floater"]:
            bg_attr = self.attributes.get("image_background", "floater_bg")
            bg_pix = tm.get_pixmap(bg_attr)
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
            img_attr = self.attributes.get("image_unselected", "PushButton_Off")
            btn_pix = tm.get_pixmap(img_attr)
            if btn_pix:
                draw_9_slice(painter, btn_pix, rect, 6, 6, 6, 6)
            else:
                painter.fillRect(rect, QColor("#4e5d6c"))
                painter.setPen(QPen(QColor("#2b333b"), 1))
                painter.drawRect(rect)
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.drawText(rect, Qt.AlignCenter,
                             self.attributes.get("label", "Button") or self.attributes.get("name", "Button"))

        elif self.tag_name in ["line_editor", "search_editor", "spinner", "combo_box"]:
            default_tex = "TextField_Off" if self.tag_name != "combo_box" else "ComboButton_Off"
            img_attr = self.attributes.get("image_unselected", default_tex)
            edit_pix = tm.get_pixmap(img_attr)

            if edit_pix:
                draw_9_slice(painter, edit_pix, rect, 4, 4, 4, 4)
            else:
                painter.fillRect(rect, QColor("#111111"))
                painter.setPen(QPen(QColor("#444444"), 1))
                painter.drawRect(rect)
            painter.setPen(QPen(QColor("#CCCCCC")))
            text = self.attributes.get("initial_value", "") or self.attributes.get("value", "") or self.attributes.get(
                "label", "")
            if not text and self.tag_name == "search_editor":
                text = "Search..."
            painter.drawText(rect.adjusted(6, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, text)

        elif self.tag_name == "check_box":
            img_attr = self.attributes.get("image_unselected", "Checkbox_Off")
            chk_pix = tm.get_pixmap(img_attr)
            chk_rect = QRectF(rect.x() + 2, rect.y() + (rect.height() - 14) / 2, 14, 14)
            if chk_pix:
                painter.drawPixmap(chk_rect, chk_pix, QRectF(0, 0, chk_pix.width(), chk_pix.height()))
            else:
                painter.fillRect(chk_rect, QColor("#222222"))
                painter.setPen(QPen(QColor("#888888"), 1))
                painter.drawRect(chk_rect)
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.drawText(QRectF(rect.x() + 20, rect.y(), rect.width() - 20, rect.height()),
                             Qt.AlignLeft | Qt.AlignVCenter, self.attributes.get("label", "Check Box"))

        elif self.tag_name == "tab_container":
            panel_pix = tm.get_pixmap("panel_bg")
            tab_height = int(self.attributes.get("tab_height", 21))

            actual_panels = [c for c in self.child_xui_items if c.tag_name in ["panel", "layout_panel"]]
            if not actual_panels:
                tabs = ["Tab 1", "Tab 2", "Tab 3"]
            else:
                tabs = []
                for child in actual_panels:
                    tabs.append(child.attributes.get("label", child.attributes.get("title", child.attributes.get("name",
                                                                                                                 "Unnamed Tab"))))

            body_rect = QRectF(rect.x(), rect.y() + tab_height, rect.width(), rect.height() - tab_height)
            if panel_pix:
                draw_9_slice(painter, panel_pix, body_rect, 4, 4, 4, 4)
            else:
                painter.fillRect(body_rect, QColor("#2d2d2d"))
                painter.setPen(QPen(QColor("#3d3d3d"), 1))
                painter.drawRect(body_rect)

            tab_x = rect.x() + 2
            tab_y = rect.y()
            for i, tab_label in enumerate(tabs):
                if i == self.active_tab_index:
                    def_tex = "TabTop_Left_Selected" if i == 0 else (
                        "TabTop_Right_Selected" if i == len(tabs) - 1 else "TabTop_Middle_Selected")
                    tex_key = self.attributes.get("tab_top_image_selected", def_tex)
                else:
                    def_tex = "TabTop_Left_Off" if i == 0 else (
                        "TabTop_Right_Off" if i == len(tabs) - 1 else "TabTop_Middle_Off")
                    tex_key = self.attributes.get("tab_top_image_unselected", def_tex)

                tab_pix = tm.get_pixmap(tex_key)
                min_w = int(self.attributes.get("tab_min_width", 60))
                max_w = int(self.attributes.get("tab_max_width", 150))
                calc_width = max(min_w, min(max_w, len(tab_label) * 7 + 20))
                t_rect = QRectF(tab_x, tab_y, calc_width, tab_height)

                if tab_pix:
                    draw_9_slice(painter, tab_pix, t_rect, 4, 4, 4, 4)
                else:
                    painter.fillRect(t_rect, QColor("#444" if i == self.active_tab_index else "#222"))
                    painter.setPen(QPen(QColor("#111"), 1))
                    painter.drawRect(t_rect)

                painter.setPen(QPen(QColor("#FFFFFF" if i == self.active_tab_index else "#AAAAAA")))
                painter.drawText(t_rect, Qt.AlignCenter, tab_label)
                tab_x += calc_width

        elif self.tag_name in ["panel", "layout_panel", "accordion", "layout_stack"]:
            bg_attr = self.attributes.get("bg_color", "panel_bg")
            panel_pix = tm.get_pixmap(bg_attr)
            if panel_pix and self.tag_name != "layout_stack":
                draw_9_slice(painter, panel_pix, rect, 4, 4, 4, 4)
            else:
                painter.fillRect(rect, QColor("#2d2d2d" if self.tag_name == "panel" else "#252525"))
                if self.tag_name != "layout_stack":
                    painter.setPen(QPen(QColor("#3d3d3d"), 1))
                    painter.drawRect(rect)

            is_tab_body = isinstance(self.parentItem(),
                                     XUIGraphicsItem) and self.parentItem().tag_name == "tab_container"
            if self.attributes.get("label") and not is_tab_body:
                painter.setPen(QPen(QColor("#AAAAAA")))
                painter.drawText(rect.adjusted(6, 4, 0, 0), Qt.AlignLeft | Qt.AlignTop, self.attributes.get("label"))

        else:
            if self.tag_name == "text":
                painter.setPen(QPen(QColor("#FFFFFF")))
                painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter,
                                 self.attributes.get("label", "Text Label") or self.inner_text)
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