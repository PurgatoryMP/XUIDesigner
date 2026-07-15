import os
from PIL import Image
from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter
from config import CONFIG


class TextureManager:
    """Singleton texture loader that dynamically indexes ALL viewer textures."""
    _instance = None

    def __init__(self, skin_base_path=None):
        if skin_base_path is None:
            skin_base_path = CONFIG.get("paths", {}).get(
                "textures_path",
                "C:/Program Files/SecondLifeViewer/skins/default/textures"
            )
        self.base_path = skin_base_path
        self.cache = {}
        self.texture_index = {}
        self._build_index()

    def set_base_path(self, path):
        if self.base_path != path:
            self.base_path = path
            self.cache.clear()
            self._build_index()

    def _build_index(self):
        """Recursively scans the texture directory to build a lookup index."""
        self.texture_index.clear()
        if not os.path.exists(self.base_path):
            return

        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file.lower().endswith(('.png', '.tga', '.j2c')):
                    # Store without extension for SL XML matching (e.g. 'PushButton_Off')
                    base_name = os.path.splitext(file)[0]
                    rel_path = os.path.relpath(os.path.join(root, file), self.base_path)

                    self.texture_index[base_name] = rel_path
                    self.texture_index[file] = rel_path

        # Fallbacks for generic tags used internally by the canvas
        self.texture_index["floater_bg"] = "windows/Window_Background.png"
        self.texture_index["floater_header"] = "windows/Dragbar.png"
        self.texture_index["panel_bg"] = "windows/Inspector_Background.png"

    @classmethod
    def get(cls):
        # Dynamically fetch the current configured path
        current_path = CONFIG.get("paths", {}).get(
            "textures_path",
            "C:/Program Files/SecondLifeViewer/skins/default/textures"
        )
        if cls._instance is None:
            cls._instance = TextureManager(current_path)
        elif cls._instance.base_path != current_path:
            # If the user updated the path in Preferences, update the singleton automatically
            cls._instance.set_base_path(current_path)
        return cls._instance

    def get_pixmap(self, texture_key):
        if not texture_key:
            return None

        # Try to resolve exactly as provided, or from our built index
        rel_path = self.texture_index.get(texture_key, texture_key)
        full_path = os.path.join(self.base_path, rel_path)

        if full_path in self.cache:
            return self.cache[full_path]

        # If still missing, try appending standard extensions
        if not os.path.exists(full_path):
            for ext in ['.png', '.tga']:
                if os.path.exists(full_path + ext):
                    full_path = full_path + ext
                    break

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