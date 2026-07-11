import os
from PIL import Image
from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter

class TextureManager:
    """Singleton texture loader for PNG, TGA, and J2C files."""
    _instance = None

    # Point this to your copy of /viewer/indra/newview/skins/default/textures
    xui_skin_textures = "G:/viewer/indra/newview/skins/default/textures"

    def __init__(self):
        self.base_path = self.xui_skin_textures
        self.cache = {}
        self.texture_map = {
            "floater_bg": "windows/Window_Background.png",
            "floater_header": "windows/Dragbar.png",
            "button_off": "widgets/PushButton_Off.png",
            "button_on": "widgets/PushButton_On.png",
            "button_press": "widgets/PushButton_Press.png",
            "checkbox_off": "widgets/Checkbox_Off.png",
            "checkbox_on": "widgets/Checkbox_On.png",
            "line_editor": "widgets/TextField_Off.png",
            "combo_box": "widgets/ComboButton_Off.png",
            "panel_bg": "windows/Inspector_Background.png",
            "tab_top_left_off": "containers/TabTop_Left_Off.png",
            "tab_top_left_on": "containers/TabTop_Left_Selected.png",
            "tab_top_mid_off": "containers/TabTop_Middle_Off.png",
            "tab_top_mid_on": "containers/TabTop_Middle_Selected.png",
            "tab_top_right_off": "containers/TabTop_Right_Off.png",
            "tab_top_right_on": "containers/TabTop_Right_Selected.png",
        }

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = TextureManager()
        return cls._instance

    def set_base_path(self, path):
        self.base_path = path
        self.cache.clear()

    def get_pixmap(self, texture_key_or_path):
        rel_path = self.texture_map.get(texture_key_or_path, texture_key_or_path)
        full_path = os.path.join(self.base_path, rel_path)
        if full_path in self.cache:
            return self.cache[full_path]
        if not os.path.exists(full_path):
            return None
        try:
            pil_img = Image.open(full_path).convert("RGBA")
            data = pil_img.tobytes("raw", "RGBA")
            qim = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qim)
            self.cache[full_path] = pixmap
            return pixmap
        except Exception as e:
            print(f"[TextureManager] Failed to load {full_path}: {e}")
            return None

def draw_9_slice(painter: QPainter, pixmap: QPixmap, target_rect: QRectF,
                 border_left=6, border_top=6, border_right=6, border_bottom=6):
    """Draws an image using a Scale-9 grid to preserve corner sharpness."""
    if not pixmap or pixmap.isNull():
        return
    pw, ph = pixmap.width(), pixmap.height()
    x, y, w, h = target_rect.x(), target_rect.y(), target_rect.width(), target_rect.height()
    border_left = min(border_left, int(w / 2))
    border_right = min(border_right, int(w / 2))
    border_top = min(border_top, int(h / 2))
    border_bottom = min(border_bottom, int(h / 2))

    src_corners = [
        QRect(0, 0, border_left, border_top),
        QRect(pw - border_right, 0, border_right, border_top),
        QRect(0, ph - border_bottom, border_left, border_bottom),
        QRect(pw - border_right, ph - border_bottom, border_right, border_bottom)
    ]
    src_edges = [
        QRect(border_left, 0, pw - border_left - border_right, border_top),
        QRect(0, border_top, border_left, ph - border_top - border_bottom),
        QRect(pw - border_right, border_top, border_right, ph - border_top - border_bottom),
        QRect(border_left, ph - border_bottom, pw - border_left - border_right, border_bottom)
    ]
    src_center = QRect(border_left, border_top, pw - border_left - border_right, ph - border_top - border_bottom)

    dst_corners = [
        QRectF(x, y, border_left, border_top),
        QRectF(x + w - border_right, y, border_right, border_top),
        QRectF(x, y + h - border_bottom, border_left, border_bottom),
        QRectF(x + w - border_right, y + h - border_bottom, border_right, border_bottom)
    ]
    dst_edges = [
        QRectF(x + border_left, y, w - border_left - border_right, border_top),
        QRectF(x, y + border_top, border_left, h - border_top - border_bottom),
        QRectF(x + w - border_right, y + border_top, border_right, h - border_top - border_bottom),
        QRectF(x + border_left, y + h - border_bottom, w - border_left - border_right, border_bottom)
    ]
    dst_center = QRectF(x + border_left, y + border_top, w - border_left - border_right, h - border_top - border_bottom)

    for s, d in zip(src_corners + src_edges + [src_center], dst_corners + dst_edges + [dst_center]):
        if s.width() > 0 and s.height() > 0 and d.width() > 0 and d.height() > 0:
            painter.drawPixmap(d, pixmap, s)