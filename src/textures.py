import os
from PIL import Image
from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QImage, QPixmap
from config import get_textures_path, get_textures_paths


class TextureManager:
    """Singleton texture loader that dynamically indexes ALL viewer textures in inheritance order."""
    _instance = None

    @classmethod
    def get(cls):
        """Returns the singleton instance, initializing it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, skin_base_path=None):
        if skin_base_path is None:
            skin_base_path = get_textures_path()
        self.base_path = skin_base_path
        self.cache = {}
        self.failed_cache = set()  # Prevents log spamming every paint frame for missing textures
        self.texture_index = {}
        self._build_index()
        TextureManager._instance = self

    def set_base_path(self, path=None):
        try:
            if path is None:
                path = get_textures_path()
            if self.base_path != path or not self.texture_index:
                self.base_path = path
                self.cache.clear()
                self.failed_cache.clear()
                self._build_index()
        except Exception as e:
            print(f"[Verbose Error] TextureManager.set_base_path failed: {e}")

    def _build_index(self):
        """Recursively scans texture directories (default first, active skin second) to build a lookup index."""
        try:
            self.texture_index.clear()
            scan_paths = get_textures_paths()

            for scan_dir in scan_paths:
                if not os.path.exists(scan_dir):
                    continue
                try:
                    for root, dirs, files in os.walk(scan_dir):
                        for file in files:
                            if file.lower().endswith(('.png', '.tga', '.j2c', '.jp2', '.jpg', '.jpeg', '.bmp', '.dds')):
                                key = os.path.splitext(file)[0].lower()
                                self.texture_index[key] = os.path.join(root, file)
                except Exception as walk_err:
                    print(f"[Verbose Error] Error scanning directory '{scan_dir}' for textures: {walk_err}")
        except Exception as e:
            print(f"[Verbose Error] TextureManager._build_index encountered a fatal error: {e}")

    def get_pixmap(self, name):
        """Alias for get_texture to maintain seamless API compatibility with graphics items."""
        return self.get_texture(name)

    def get_texture(self, name):
        if not name:
            return None

        clean_name = os.path.splitext(os.path.basename(str(name).strip()))[0].lower()
        if clean_name in self.failed_cache:
            return None

        if clean_name not in self.texture_index:
            self.failed_cache.add(clean_name)
            return None

        if clean_name in self.cache:
            return self.cache[clean_name]

        file_path = self.texture_index[clean_name]
        try:
            # 1. Attempt native Qt QPixmap load (Fastest for PNG, JPG, BMP)
            pixmap = QPixmap(file_path)

            # 2. If Qt fails (common for SL .tga and .j2c files), use PIL as fallback
            if pixmap.isNull():
                try:
                    with Image.open(file_path) as pil_img:
                        pil_img = pil_img.convert("RGBA")
                        data = pil_img.tobytes("raw", "RGBA")
                        # CRITICAL FIX: .copy() prevents PySide6 from dropping the memory buffer!
                        qimage = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888).copy()
                        pixmap = QPixmap.fromImage(qimage)
                except Exception as pil_err:
                    print(f"[Verbose Error] PIL failed to decode texture '{file_path}': {pil_err}")

            if not pixmap.isNull():
                self.cache[clean_name] = pixmap
                return pixmap
            else:
                print(f"[Verbose Error] Texture '{clean_name}' at '{file_path}' resolved to a null QPixmap.")
                self.failed_cache.add(clean_name)
        except Exception as e:
            print(f"[Verbose Error] Unexpected exception loading texture '{clean_name}': {e}")
            self.failed_cache.add(clean_name)

        return None


def draw_9_slice(painter, pixmap, rect, border_left=4, border_top=4, border_right=4, border_bottom=4):
    try:
        if not pixmap or pixmap.isNull():
            return
        pw, ph = pixmap.width(), pixmap.height()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

        # SAFEGUARD: If the texture is too small to be 9-sliced (e.g., 1x1 fill textures),
        # or if the target UI control is smaller than the borders, fall back to standard scaling.
        if pw <= (border_left + border_right) or ph <= (border_top + border_bottom) or w <= (
                border_left + border_right) or h <= (border_top + border_bottom):
            painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
            return

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

        for i in range(4):
            painter.drawPixmap(dst_corners[i], pixmap, QRectF(src_corners[i]))
            painter.drawPixmap(dst_edges[i], pixmap, QRectF(src_edges[i]))
        painter.drawPixmap(dst_center, pixmap, QRectF(src_center))
    except Exception as e:
        print(f"[Verbose Error] draw_9_slice encountered an error during painting: {e}")