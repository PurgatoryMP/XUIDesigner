from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
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
                widget_def = widgets[tag_name]
                target_params = widget_def.get("params", {})

                # --- ADDED: Apply compound attributes discovered during XML registration (e.g., image_unselected) ---
                if "default_attributes" in widget_def:
                    for k, v in widget_def["default_attributes"].items():
                        if k not in self.attributes:
                            self.attributes[k] = v

                if "label" in widget_def and not self.attributes.get("label"):
                    self.attributes["label"] = widget_def["label"]
                if "width" in widget_def and "width" not in self.attributes:
                    self.attributes["width"] = str(widget_def["width"])
                if "height" in widget_def and "height" not in self.attributes:
                    self.attributes["height"] = str(widget_def["height"])
                break

        if not target_params:
            target_params = LLUICTRL_PARAMS if tag_name != "view" else LLVIEW_PARAMS

        # --- FIX: Ensure newly dragged widgets get a meaningful default name instead of 'unnamed' ---
        if "name" not in self.attributes:
            if tag_name in ["floater", "multi_floater", "panel", "layout_panel", "tab_container", "layout_stack"]:
                self.attributes["name"] = tag_name
            elif "label" in self.attributes and self.attributes["label"]:
                self.attributes["name"] = self.attributes["label"].lower().replace(" ", "_")
            else:
                self.attributes["name"] = tag_name

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

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            canvas = getattr(self.scene(), 'canvas_container', None) or self.scene()
            snapping_enabled = getattr(canvas, 'grid_snapping_enabled', True)
            grid_size = getattr(canvas, 'grid_size', 10)

            new_pos = value
            # Respect toggle and use dynamic slider grid size
            if snapping_enabled and grid_size > 0:
                snapped_x = round(new_pos.x() / grid_size) * grid_size
                snapped_y = round(new_pos.y() / grid_size) * grid_size
            else:
                snapped_x = new_pos.x()
                snapped_y = new_pos.y()

            parent = self.parentItem()
            idx = parent.child_xui_items.index(self) if isinstance(parent, XUIGraphicsItem) and self in parent.child_xui_items else -1
            prev_sib = parent.child_xui_items[idx - 1] if idx > 0 else None

            if "right" in self.attributes:
                parent_w = parent.rect().width() if isinstance(parent, XUIGraphicsItem) else 500
                try:
                    if int(self.attributes["right"]) <= 0:
                        self.attributes["right"] = str(int((snapped_x + self.rect().width()) - parent_w))
                    else:
                        self.attributes["right"] = str(int(snapped_x + self.rect().width()))
                except ValueError:
                    self.attributes["right"] = str(int(snapped_x + self.rect().width()))
            elif "left_delta" in self.attributes and prev_sib:
                self.attributes["left_delta"] = str(int(snapped_x - prev_sib.x()))
            elif "left_pad" in self.attributes and prev_sib:
                self.attributes["left_pad"] = str(int(snapped_x - (prev_sib.x() + prev_sib.rect().width())))
            else:
                self.attributes["left"] = str(int(snapped_x))

            if "bottom" in self.attributes:
                parent_h = parent.rect().height() if isinstance(parent, XUIGraphicsItem) else 500
                try:
                    if int(self.attributes["bottom"]) <= 0:
                        self.attributes["bottom"] = str(int((snapped_y + self.rect().height()) - parent_h))
                    else:
                        self.attributes["bottom"] = str(int(snapped_y + self.rect().height()))
                except ValueError:
                    self.attributes["bottom"] = str(int(snapped_y + self.rect().height()))
            elif "top_delta" in self.attributes and prev_sib:
                self.attributes["top_delta"] = str(int(snapped_y - prev_sib.y()))
            elif "top_pad" in self.attributes and prev_sib:
                self.attributes["top_pad"] = str(int(snapped_y - (prev_sib.y() + prev_sib.rect().height())))
            else:
                self.attributes["top"] = str(int(snapped_y))

            if hasattr(self.scene(), 'canvas_container') and self.scene().canvas_container:
                self.scene().canvas_container.item_modified_signal.emit(self)
            return QPointF(snapped_x, snapped_y)
        return super().itemChange(change, value)

    def _draw_tab_container(self, painter, rect):
        """Draws the tab container background and tab header buttons."""
        # Draw main container body
        painter.fillRect(rect, QColor("#222222"))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRect(rect)

        # Gather child tabs (typically <panel> or <tab_item> elements)
        tabs = [child for child in getattr(self, 'child_xui_items', []) if isinstance(child, XUIGraphicsItem)]
        if not tabs:
            return

        header_height = 24
        header_rect = QRectF(rect.x(), rect.y(), rect.width(), header_height)
        painter.fillRect(header_rect, QColor("#181818"))
        painter.drawLine(rect.left(), rect.top() + header_height, rect.right(), rect.top() + header_height)

        # Draw individual tab headers
        tab_width = min(120, max(60, rect.width() / max(1, len(tabs))))
        for i, tab_item in enumerate(tabs):
            tab_x = rect.x() + (i * tab_width)
            tab_rect = QRectF(tab_x, rect.y(), tab_width, header_height)

            # Highlight active tab
            if i == self.active_tab_index:
                painter.fillRect(tab_rect, QColor("#3a3a3a"))
                painter.setPen(QPen(QColor("#1e457c"), 2))
                painter.drawLine(tab_rect.left(), tab_rect.bottom(), tab_rect.right(), tab_rect.bottom())
                painter.setPen(QPen(QColor("#FFFFFF")))
            else:
                painter.fillRect(tab_rect, QColor("#282828"))
                painter.setPen(QPen(QColor("#888888")))

            # Draw border between tabs
            painter.drawRect(tab_rect)

            # Draw tab label
            label = tab_item.attributes.get("label") or tab_item.attributes.get("title") or tab_item.attributes.get(
                "name") or f"Tab {i + 1}"
            painter.drawText(tab_rect.adjusted(4, 0, -4, 0), Qt.AlignCenter | Qt.AlignVCenter, label)

        # Ensure only the active tab's children are shown
        self.update_tab_visibility()

    def update_tab_visibility(self):
        """Hides inactive tab panels and shows the active one."""
        tabs = [child for child in getattr(self, 'child_xui_items', []) if isinstance(child, XUIGraphicsItem)]
        for i, tab_item in enumerate(tabs):
            is_active = (i == self.active_tab_index)
            if tab_item.isVisible() != is_active:
                tab_item.setVisible(is_active)

    def update_z_orders(self):
        """Ensures Qt Canvas Z-ordering strictly mirrors the DOM hierarchy array index."""
        for idx, child in enumerate(self.child_xui_items):
            child.setZValue(float(idx + 1))
            child.update_z_orders()

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

        parent = self.parentItem()
        parent_w = parent.rect().width() if isinstance(parent, XUIGraphicsItem) else 500
        parent_h = parent.rect().height() if isinstance(parent, XUIGraphicsItem) else 500

        if "right" in self.attributes:
            try:
                if int(self.attributes["right"]) <= 0:
                    self.attributes["right"] = str(int((pos.x() + rect.width()) - parent_w))
                else:
                    self.attributes["right"] = str(int(pos.x() + rect.width()))
            except ValueError:
                self.attributes["right"] = str(int(pos.x() + rect.width()))
        elif "left_delta" not in self.attributes and "left_pad" not in self.attributes:
            self.attributes["left"] = str(int(pos.x()))

        if "bottom" in self.attributes:
            try:
                if int(self.attributes["bottom"]) <= 0:
                    self.attributes["bottom"] = str(int((pos.y() + rect.height()) - parent_h))
                else:
                    self.attributes["bottom"] = str(int(pos.y() + rect.height()))
            except ValueError:
                self.attributes["bottom"] = str(int(pos.y() + rect.height()))
        elif "top_delta" not in self.attributes and "top_pad" not in self.attributes:
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

        if self.tag_name == "tab_container":
            self.update_tabs()
        elif self.tag_name == "layout_stack":
            self.update_layout_stack()
        else:
            for child in self.child_xui_items:
                follows_str = child.attributes.get("follows", "left|top").lower()

                normalized_follows = follows_str.replace(" ", "|").replace(",", "|")
                follows = [f.strip() for f in normalized_follows.split("|") if f.strip()]

                if "all" in follows:
                    follows = ["left", "top", "right", "bottom"]

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
        if self.tag_name != "tab_container":
            return

        tabs = [c for c in self.child_xui_items if c.tag_name in ["panel", "layout_panel"]]
        if self.active_tab_index >= len(tabs):
            self.active_tab_index = max(0, len(tabs) - 1)

        tab_pos_side = self.attributes.get("tab_position", "top").lower()
        tab_height = int(self.attributes.get("tab_height", 21))
        tab_width_attr = int(self.attributes.get("tab_width", 80))

        container_w = float(self.attributes.get("width", 250))
        container_h = float(self.attributes.get("height", 180))

        # Calculate child panel bounding box based on header side
        if tab_pos_side == "top":
            panel_x, panel_y = 2.0, float(tab_height + 2)
            panel_w = max(10.0, container_w - 4.0)
            panel_h = max(10.0, container_h - tab_height - 4.0)
        elif tab_pos_side == "bottom":
            panel_x, panel_y = 2.0, 2.0
            panel_w = max(10.0, container_w - 4.0)
            panel_h = max(10.0, container_h - tab_height - 4.0)
        elif tab_pos_side == "left":
            panel_x, panel_y = float(tab_width_attr + 2), 2.0
            panel_w = max(10.0, container_w - tab_width_attr - 4.0)
            panel_h = max(10.0, container_h - 4.0)
        elif tab_pos_side == "right":
            panel_x, panel_y = 2.0, 2.0
            panel_w = max(10.0, container_w - tab_width_attr - 4.0)
            panel_h = max(10.0, container_h - 4.0)
        else:
            panel_x, panel_y = 2.0, float(tab_height + 2)
            panel_w = max(10.0, container_w - 4.0)
            panel_h = max(10.0, container_h - tab_height - 4.0)

        for i, tab in enumerate(tabs):
            is_active = (i == self.active_tab_index)
            tab.setVisible(is_active)
            tab.setPos(panel_x, panel_y)
            tab.attributes["left"] = str(int(panel_x))
            tab.attributes["top"] = str(int(panel_y))
            try:
                tab.resize_item(panel_w, panel_h)
            except ValueError:
                pass
        self.update_z_orders()

    def update_layout_stack(self):
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
        self.update_z_orders()

    def add_child_item(self, child_item):
        if child_item not in self.child_xui_items:
            self.child_xui_items.append(child_item)
            child_item.setParentItem(self)
        if self.tag_name == "tab_container":
            self.update_tabs()
        elif self.tag_name == "layout_stack":
            self.update_layout_stack()
        self.update_z_orders()

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
        self.update_z_orders()

    def remove_child_item(self, child_item):
        if child_item in self.child_xui_items:
            self.child_xui_items.remove(child_item)
            child_item.setParentItem(None)
        if self.tag_name == "tab_container":
            self.update_tabs()
        elif self.tag_name == "layout_stack":
            self.update_layout_stack()
        self.update_z_orders()

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()

            if self.tag_name == "tab_container":
                # Check '+' button click to spawn new tab
                if hasattr(self, '_plus_btn_rect') and self._plus_btn_rect and self._plus_btn_rect.contains(pos):
                    actual_panels = [c for c in self.child_xui_items if c.tag_name in ["panel", "layout_panel"]]
                    new_idx = len(actual_panels) + 1

                    new_panel = XUIGraphicsItem("panel", {"label": f"New Tab {new_idx}", "name": f"tab_{new_idx}"})
                    new_panel.source_file = self.source_file
                    self.add_child_item(new_panel)

                    self.active_tab_index = new_idx - 1
                    self.update_tabs()

                    if hasattr(self.scene(), 'canvas_container'):
                        self.scene().canvas_container.item_modified_signal.emit(self)

                    self.scene().update()
                    event.accept()
                    return

                # Check tab header clicks to switch tabs
                if hasattr(self, '_tab_header_rects') and self._tab_header_rects:
                    for idx, tab_rect in self._tab_header_rects:
                        if tab_rect.contains(pos):
                            self.active_tab_index = idx
                            self.update_tabs()
                            self.scene().update()

                            if hasattr(self.scene(), 'canvas_container'):
                                self.scene().canvas_container.item_modified_signal.emit(self)

                            super().mousePressEvent(event)
                            return

                # --- Handle Delete Button & Resize Handles (Consolidated) ---
            if self.isSelected():
                if self._get_delete_rect().contains(pos):
                    if hasattr(self.scene(), 'canvas_container'):
                        self.scene().canvas_container.delete_item(self)
                    event.accept()
                    return

                handles = self._get_handles()
                for h_id, r in handles.items():
                    if r.contains(pos):
                        self.resizing = True
                        self.resize_dir = h_id
                        event.accept()
                        return

                handles = self._get_handles()
                for h_id, r in handles.items():
                    if r.contains(pos):
                        self.resizing = True
                        self.resize_dir = h_id
                        event.accept()
                        return

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

                            is_active = (i == self.active_tab_index)
                            extra_w = 20 if is_active else 0
                            calc_width = max(min_w, min(max_w, len(tab_label) * 7 + 20)) + extra_w

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
            canvas = getattr(self.scene(), 'canvas_container', None) or self.scene()
            snapping_enabled = getattr(canvas, 'grid_snapping_enabled', True)
            grid_size = getattr(canvas, 'grid_size', 10)

            if snapping_enabled and grid_size > 0:
                snapped_x = round(parent_pos.x() / grid_size) * grid_size
                snapped_y = round(parent_pos.y() / grid_size) * grid_size
            else:
                snapped_x = parent_pos.x()
                snapped_y = parent_pos.y()

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
                self.scene().canvas_container.item_modified_signal.emit(self)
        super().mouseReleaseEvent(event)

    def validate(self):
        errors, warnings = [], []
        if self.tag_name not in ["panel", "layout_panel", "text", "view_border", "icon", "window_shade", "accordion",
                                 "scroll_list"]:
            if not self.attributes.get("name") or self.attributes.get("name") == "unnamed":
                warnings.append(f"Bad Practice: Missing or 'unnamed' name attribute for {self.tag_name}.")

        if self.tag_name == "layout_panel":
            parent = self.parentItem()
            if not isinstance(parent, XUIGraphicsItem) or parent.tag_name != "layout_stack":
                errors.append(f"Syntax Error: <layout_panel> must be a direct child of <layout_stack>.")

        has_left, has_right = "left" in self.attributes, "right" in self.attributes
        follows = self.attributes.get("follows", "").lower()

        normalized_follows = follows.replace(" ", "|").replace(",", "|")
        follows_list = [f.strip() for f in normalized_follows.split("|") if f.strip()]

        if has_left and has_right and "left" not in follows_list and "right" not in follows_list and "all" not in follows_list:
            warnings.append("Bad Practice: Opposing anchors (left & right) used without matching 'follows' flags.")

        return errors, warnings

    def paint(self, painter, option, widget=None):
        try:
            painter.setClipRect(option.exposedRect)
            rect = self.rect()

            tm = TextureManager.get()
            get_pixmap = tm.get_pixmap if tm else lambda k: None

            is_checkbox_or_radio = self.tag_name in ("check_box", "radio_item")

            # 1. Resolve Background / 9-Slice Textures
            # Notice checkboxes and radio items must NOT use image_unselected as their background 9-slice!
            bg_texture_key = None
            bg_keys = ["background_image", "bg_image", "bg_opaque_image", "chrome_image"]
            if not is_checkbox_or_radio:
                bg_keys = ["image_unselected", "background_image", "bg_image", "bg_opaque_image", "image", "chrome_image"]

            for attr_key in bg_keys:
                val = self.attributes.get(attr_key)
                if val and str(val).strip():
                    bg_texture_key = str(val).strip()
                    break

            # Container and control fallback texture keys (inherits from custom skin if present)
            if not bg_texture_key:
                if self.tag_name == "floater": bg_texture_key = "floater_bg"
                elif self.tag_name == "panel": bg_texture_key = "panel_bg"
                elif self.tag_name == "button" and not is_checkbox_or_radio: bg_texture_key = "PushButton_Off"
                elif self.tag_name == "combo_box": bg_texture_key = "combobox_off"
                elif self.tag_name == "line_editor": bg_texture_key = "lineeditor_bg"

            bg_pixmap = get_pixmap(bg_texture_key) if bg_texture_key else None

            # --- Special Case: Floater Window ---
            if self.tag_name == "floater":
                if bg_pixmap and not bg_pixmap.isNull():
                    draw_9_slice(painter, bg_pixmap, rect)
                else:
                    painter.fillRect(rect, QColor("#222222"))
                    painter.setPen(QPen(QColor("#555555"), 1))
                    painter.drawRect(rect)

                header_rect = QRectF(rect.x(), rect.y(), rect.width(), 24)
                header_pixmap = get_pixmap("floater_header")
                if header_pixmap and not header_pixmap.isNull():
                    draw_9_slice(painter, header_pixmap, header_rect, 4, 4, 4, 4)
                else:
                    painter.fillRect(header_rect, QColor("#333333"))

                painter.setPen(QPen(QColor("#FFFFFF")))
                title = self.attributes.get("title") or self.attributes.get("name") or "Floater"
                painter.drawText(header_rect.adjusted(8, 0, -8, 0), Qt.AlignLeft | Qt.AlignVCenter, title)
                self._draw_selection_box(painter, rect)
                return

            # --- Special Case: Progress Bar ---
            elif self.tag_name == "progress_bar":
                track_rect = QRectF(rect.x(), rect.y(), rect.width(), rect.height())
                painter.fillRect(track_rect, QColor("#111111"))
                painter.setPen(QPen(QColor("#444444"), 1))
                painter.drawRect(track_rect)

                try:
                    val_str = (self.attributes.get("value") or self.attributes.get("initial_val") or
                               self.attributes.get("val") or "0.5")
                    progress_val = max(0.0, min(1.0, float(val_str)))
                except ValueError:
                    progress_val = 0.5

                fill_w = max(0.0, (rect.width() - 4) * progress_val)
                if fill_w > 0:
                    fill_rect = QRectF(rect.x() + 2, rect.y() + 2, fill_w, rect.height() - 4)
                    painter.fillRect(fill_rect, QColor("#1e457c"))
                self._draw_selection_box(painter, rect)
                return

            # --- Special Case: Pure Text Label ---
            elif self.tag_name == "text":
                painter.setPen(QPen(QColor("#FFFFFF")))
                txt_label = (self.attributes.get("label") or self.attributes.get("name") or
                             getattr(self, 'inner_text', '') or "Text Label")
                if txt_label == "unnamed": txt_label = "Text Label"

                halign_str = self.attributes.get("halign", "left").lower()
                valign_str = self.attributes.get("valign", "center").lower()
                align_flags = Qt.TextSingleLine
                align_flags |= Qt.AlignHCenter if halign_str == "center" else (Qt.AlignRight if halign_str == "right" else Qt.AlignLeft)
                align_flags |= Qt.AlignTop if valign_str == "top" else (Qt.AlignBottom if valign_str == "bottom" else Qt.AlignVCenter)

                painter.drawText(rect.adjusted(2, 2, -2, -2), align_flags, txt_label)
                self._draw_selection_box(painter, rect)
                return

            # --- Special Case: Tab Container ---
            elif self.tag_name == "tab_container":
                self._draw_tab_container_internal(painter, rect)
                return

            # --- Standard Controls & Imported Viewer Widgets ---
            # 1. Draw Background (9-sliced texture or fallback solid box)
            if bg_pixmap and not bg_pixmap.isNull():
                if self.tag_name in ("icon", "image", "avatar_icon", "view_border"):
                    painter.drawPixmap(rect, bg_pixmap, QRectF(bg_pixmap.rect()))
                else:
                    draw_9_slice(painter, bg_pixmap, rect)
            else:
                painter.fillRect(rect, QColor("#3a3a3a"))
                painter.setPen(QPen(QColor("#555555"), 1))
                painter.drawRect(rect)

            # 2. Resolve Control Icons / Overlays (Checkboxes & Radio Items use image_unselected / image_selected here!)
            icon_texture_key = None
            if is_checkbox_or_radio:
                is_checked = str(self.attributes.get("value", "")).lower() in ["true", "1", "yes"] or \
                             str(self.attributes.get("initial_value", "")).lower() in ["true", "1", "yes"]
                if is_checked:
                    icon_texture_key = self.attributes.get("image_selected") or ("Checkbox_On" if self.tag_name == "check_box" else "RadioButton_On")
                else:
                    icon_texture_key = self.attributes.get("image_unselected") or ("Checkbox_Off" if self.tag_name == "check_box" else "RadioButton_Off")
            else:
                icon_texture_key = (self.attributes.get("default_icon_name") or
                                    self.attributes.get("icon") or
                                    self.attributes.get("image_name") or
                                    self.attributes.get("image_overlay") or
                                    (self.attributes.get("image") if self.tag_name in ("icon", "image") else None))

            if icon_texture_key:
                icon_pixmap = get_pixmap(icon_texture_key)
                if icon_pixmap and not icon_pixmap.isNull():
                    iw, ih = float(icon_pixmap.width()), float(icon_pixmap.height())
                    if is_checkbox_or_radio:
                        box_size = min(max(12.0, ih), rect.height() - 4.0)
                        target_rect = QRectF(rect.left() + 4.0, rect.center().y() - (box_size / 2.0), box_size, box_size)
                    else:
                        avail_w, avail_h = max(1.0, rect.width() - 4.0), max(1.0, rect.height() - 4.0)
                        if (iw > avail_w or ih > avail_h or self.tag_name in ("icon", "image")) and iw > 0 and ih > 0:
                            scale = min(avail_w / iw, avail_h / ih)
                            target_w, target_h = iw * scale, ih * scale
                            target_rect = QRectF(rect.center().x() - target_w / 2.0, rect.center().y() - target_h / 2.0, target_w, target_h)
                        else:
                            target_rect = QRectF(rect.center().x() - iw / 2.0, rect.center().y() - ih / 2.0, iw, ih)
                    painter.drawPixmap(target_rect, icon_pixmap, QRectF(icon_pixmap.rect()))
                elif is_checkbox_or_radio:
                    # Clean vector fallback drawing if skin texture is missing
                    box_size = 14.0
                    target_rect = QRectF(rect.left() + 4.0, rect.center().y() - (box_size / 2.0), box_size, box_size)
                    painter.save()
                    painter.setPen(QPen(QColor("#AAAAAA"), 1.5))
                    painter.setBrush(QBrush(QColor("#222222")))
                    if self.tag_name == "radio_item":
                        painter.drawEllipse(target_rect)
                        if "on" in str(icon_texture_key).lower() or "selected" in str(icon_texture_key).lower():
                            painter.setBrush(QBrush(QColor("#FFFFFF")))
                            painter.drawEllipse(target_rect.adjusted(3, 3, -3, -3))
                    else:
                        painter.drawRect(target_rect)
                        if "on" in str(icon_texture_key).lower() or "selected" in str(icon_texture_key).lower():
                            painter.setPen(QPen(QColor("#FFFFFF"), 2))
                            painter.drawLine(target_rect.left() + 3, target_rect.center().y(), target_rect.center().x(), target_rect.bottom() - 3)
                            painter.drawLine(target_rect.center().x(), target_rect.bottom() - 3, target_rect.right() - 3, target_rect.top() + 3)
                    painter.restore()

            # 3. Draw Control Label Text
            label_text = self.attributes.get("label") or self.attributes.get("label_selected")
            if not label_text and self.tag_name in ("button", "check_box", "radio_item", "menu_item", "flyout_button"):
                name_val = self.attributes.get("name", "")
                if name_val and name_val != "unnamed": label_text = name_val

            if label_text:
                painter.setPen(QPen(QColor("#FFFFFF")))
                if is_checkbox_or_radio:
                    painter.drawText(rect.adjusted(22, 0, -4, 0), Qt.AlignLeft | Qt.AlignVCenter, label_text)
                else:
                    painter.drawText(rect.adjusted(6, 0, -6, 0), Qt.AlignCenter | Qt.AlignVCenter, label_text)

            self._draw_selection_box(painter, rect)
        except Exception as e:
            print(f"[Verbose Error] XUIGraphicsItem.paint failed on <{self.tag_name}>: {e}")

    def _draw_tab_container_internal(self, painter, rect):
        """Helper method extracted to keep tab rendering clean and exception-safe."""
        try:
            painter.fillRect(rect, QColor("#1e1e1e"))
            painter.setPen(QPen(QColor("#555555"), 1))
            painter.drawRect(rect)

            tab_pos_side = self.attributes.get("tab_position", "top").lower()
            tab_height = int(self.attributes.get("tab_height", 21))
            tab_width_attr = int(self.attributes.get("tab_width", 80))
            min_w, max_w = int(self.attributes.get("tab_min_width", 60)), int(self.attributes.get("tab_max_width", 150))

            actual_panels = [c for c in getattr(self, 'child_xui_items', []) if c.tag_name in ["panel", "layout_panel"]]
            self._tab_header_rects = []
            self._plus_btn_rect = None

            if tab_pos_side == "top":
                header_rect = QRectF(rect.x(), rect.y(), rect.width(), tab_height)
                divider_line = QLineF(rect.left(), rect.top() + tab_height, rect.right(), rect.top() + tab_height)
            elif tab_pos_side == "bottom":
                header_rect = QRectF(rect.x(), rect.bottom() - tab_height, rect.width(), tab_height)
                divider_line = QLineF(rect.left(), rect.bottom() - tab_height, rect.right(), rect.bottom() - tab_height)
            elif tab_pos_side == "left":
                header_rect = QRectF(rect.x(), rect.y(), tab_width_attr, rect.height())
                divider_line = QLineF(rect.left() + tab_width_attr, rect.top(), rect.left() + tab_width_attr, rect.bottom())
            elif tab_pos_side == "right":
                header_rect = QRectF(rect.right() - tab_width_attr, rect.y(), tab_width_attr, rect.height())
                divider_line = QLineF(rect.right() - tab_width_attr, rect.top(), rect.right() - tab_width_attr, rect.bottom())
            else:
                header_rect = QRectF(rect.x(), rect.y(), rect.width(), tab_height)
                divider_line = QLineF(rect.left(), rect.top() + tab_height, rect.right(), rect.top() + tab_height)

            painter.fillRect(header_rect, QColor("#141414"))
            painter.drawLine(divider_line)

            offset = 2
            for i, tab_panel in enumerate(actual_panels):
                tab_label = tab_panel.attributes.get("label", tab_panel.attributes.get("title", tab_panel.attributes.get("name", "Unnamed Tab")))
                is_active = (i == getattr(self, 'active_tab_index', 0))

                if tab_pos_side in ["top", "bottom"]:
                    calc_size = max(min_w, min(max_w, len(tab_label) * 7 + 20)) + (20 if is_active else 0)
                    tab_rect = QRectF(rect.x() + offset, header_rect.y(), calc_size, tab_height)
                else:
                    calc_size = max(20, tab_height + (6 if is_active else 0))
                    tab_rect = QRectF(header_rect.x(), rect.y() + offset, tab_width_attr, calc_size)

                self._tab_header_rects.append((i, tab_rect))

                if is_active:
                    painter.fillRect(tab_rect, QColor("#2b2b2b"))
                    painter.setPen(QPen(QColor("#1e457c"), 2))
                    if tab_pos_side == "top": painter.drawLine(tab_rect.left(), tab_rect.bottom(), tab_rect.right(), tab_rect.bottom())
                    elif tab_pos_side == "bottom": painter.drawLine(tab_rect.left(), tab_rect.top(), tab_rect.right(), tab_rect.top())
                    elif tab_pos_side == "left": painter.drawLine(tab_rect.right(), tab_rect.top(), tab_rect.right(), tab_rect.bottom())
                    elif tab_pos_side == "right": painter.drawLine(tab_rect.left(), tab_rect.top(), tab_rect.left(), tab_rect.bottom())
                    painter.setPen(QPen(QColor("#FFFFFF")))
                else:
                    painter.fillRect(tab_rect, QColor("#222222"))
                    painter.setPen(QPen(QColor("#888888")))

                painter.drawRect(tab_rect)
                painter.drawText(tab_rect.adjusted(4, 0, -4, 0), Qt.AlignCenter | Qt.AlignVCenter, tab_label)
                offset += calc_size

            if tab_pos_side in ["top", "bottom"]:
                self._plus_btn_rect = QRectF(rect.x() + offset + 4, header_rect.y() + 2, 20, tab_height - 4)
            else:
                self._plus_btn_rect = QRectF(header_rect.x() + 2, rect.y() + offset + 4, tab_width_attr - 4, 20)

            painter.fillRect(self._plus_btn_rect, QColor("#333333"))
            painter.setPen(QPen(QColor("#AAAAAA")))
            painter.drawRect(self._plus_btn_rect)
            painter.drawText(self._plus_btn_rect, Qt.AlignCenter, "+")
            self._draw_selection_box(painter, rect)
        except Exception as e:
            print(f"[Verbose Error] _draw_tab_container_internal failed: {e}")

    def _draw_selection_box(self, painter, rect):
        """Helper to draw the green dashed selection bounding box and 8-way resize handles."""
        if self.isSelected():
            painter.save()
            painter.setPen(QPen(QColor("#00FF00"), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
            painter.restore()

            painter.save()
            self._draw_handles(painter)
            painter.restore()
