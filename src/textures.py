"""
This module provides the TextureManager singleton class, which handles asset
indexing and cross-skin inheritance paths for Second Life viewer UI elements. It
features fallback PIL decoding for non-native formats (e.g., .tga, .j2c) and a
specialized 9-slice layout scaler for rendering dynamic UI panels.
"""

import os
from typing import Any, Dict, List, Optional, Set

from PIL import Image
from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QImage, QPainter, QPixmap

from config import get_textures_path, get_textures_paths


class TextureManager:
    """Singleton texture loader and cache manager for XUI graphical components.

    Indexes viewer-supported formats recursively across standard skin inheritance
    hierarchies. Leverages memory cache tables for valid assets and maintains a
    failure log set to mitigate repetitive disk hits and performance bottlenecks
    during paint loops.

    Attributes:
        base_path (str): Root file path where the skin's textures reside.
        cache (Dict[str, QPixmap]): Memory-cached active QPixmap structures.
        failed_cache (Set[str]): Cleaned texture names that failed decoding or location.
        texture_index (Dict[str, str]): Lowercase base names mapped to full file paths.
    """

    _instance: Optional["TextureManager"] = None

    @classmethod
    def get(cls) -> "TextureManager":
        """Retrieves or initializes the global singleton instance.

        Returns:
            TextureManager: The unified manager instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, skin_base_path: Optional[str] = None) -> None:
        """Initializes memory cache arrays and triggers directory file mapping.

        Args:
            skin_base_path (Optional[str]): Root textures directory. If None,
                it resolves defaults via configuration settings.
        """
        if skin_base_path is None:
            skin_base_path = get_textures_path()
        self.base_path: str = skin_base_path
        self.cache: Dict[str, QPixmap] = {}
        self.failed_cache: Set[str] = set()
        self.texture_index: Dict[str, str] = {}

        # Build initial lookups and hook instance globally
        self._build_index()
        TextureManager._instance = self

    def set_base_path(self, path: Optional[str] = None) -> None:
        """Updates the root workspace path and clears all temporary cache arrays.

        Args:
            path (Optional[str]): Target directory to swap to. If None, pulls the
                current config baseline path instead.
        """
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

    def _build_index(self) -> None:
        """Scans texture file paths hierarchically to build lookup mappings.

        Iterates over systemic paths (prioritizing active skins over defaults)
        and extracts extensions to categorize acceptable graphics elements.
        """
        try:
            self.texture_index.clear()
            scan_paths: List[str] = get_textures_paths()

            for scan_dir in scan_paths:
                if not os.path.exists(scan_dir):
                    continue
                try:
                    for root, _, files in os.walk(scan_dir):
                        for file in files:
                            if file.lower().endswith(
                                    ('.png', '.tga', '.j2c', '.jp2', '.jpg', '.jpeg', '.bmp', '.dds')
                            ):
                                key = os.path.splitext(file)[0].lower()
                                self.texture_index[key] = os.path.join(root, file)
                except Exception as walk_err:
                    print(f"[Verbose Error] Error scanning directory '{scan_dir}' for textures: {walk_err}")
        except Exception as e:
            print(f"[Verbose Error] TextureManager._build_index encountered a fatal error: {e}")

    def get_pixmap(self, name: Any) -> Optional[QPixmap]:
        """Provides an API alias to safely fetch textures as standard QPixmaps.

        Args:
            name (Any): The file target identifier or base name.

        Returns:
            Optional[QPixmap]: Loaded image object, or None if invalid.
        """
        return self.get_texture(name)

    def get_texture(self, name: Any) -> Optional[QPixmap]:
        """Loads and returns a texture, using PIL as a fallback decoder for native failures.

        Normalizes raw values to lower-cased keys. It performs initial decoding via
        QPixmap; if unreadable (common for TGA/J2C streams), it passes extraction
        to PIL before safely re-buffering pixel elements back into Qt frameworks.

        Args:
            name (Any): Asset string name or path variable.

        Returns:
            Optional[QPixmap]: The mapped visual pixel map data, or None if failed.
        """
        if not name:
            return None

        # Clean extensions and directories to match dictionary lookup targets
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
            # Step 1: Attempt native Qt loading mechanism (optimized for PNG/JPG)
            pixmap = QPixmap(file_path)

            # Step 2: If Qt fails on custom SL formats, spin up Pillow fallback conversion
            if pixmap.isNull():
                try:
                    with Image.open(file_path) as pil_img:
                        pil_img = pil_img.convert("RGBA")
                        data = pil_img.tobytes("raw", "RGBA")

                        # CRITICAL: .copy() prevents garbage collection of the underlying data buffer
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


def draw_9_slice(
        painter: QPainter,
        pixmap: QPixmap,
        rect: QRectF,
        border_left: int = 4,
        border_top: int = 4,
        border_right: int = 4,
        border_bottom: int = 4
) -> None:
    """Slices a source texture into a 3x3 grid to match variable boundaries accurately.

    Protects element scale proportions by splitting shapes into 4 absolute corners,
    4 directional scaling edges, and 1 un-anchored stretching center node.

    Args:
        painter (QPainter): The current frame engine canvas renderer pointer.
        pixmap (QPixmap): Source graphic image asset to fragment.
        rect (QRectF): Target canvas box coordinates to project into.
        border_left (int): Pixel padding boundary offset from the left.
        border_top (int): Pixel padding boundary offset from the top.
        border_right (int): Pixel padding boundary offset from the right.
        border_bottom (int): Pixel padding boundary offset from the bottom.
    """
    try:
        if not pixmap or pixmap.isNull():
            return
        pw, ph = pixmap.width(), pixmap.height()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

        # SAFEGUARD: Drop down to flat full stretch transformations if components are too small
        if pw <= (border_left + border_right) or ph <= (border_top + border_bottom) or w <= (
                border_left + border_right) or h <= (border_top + border_bottom):
            painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
            return

        # Define coordinates for the origin asset's fixed grid sections
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

        # Map fixed components onto the target canvas rectangle coordinates
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
        dst_center = QRectF(x + border_left, y + border_top, w - border_left - border_right,
                            h - border_top - border_bottom)

        # Execute drawing passes over the 9 target slices sequentially
        for i in range(4):
            painter.drawPixmap(dst_corners[i], pixmap, QRectF(src_corners[i]))
            painter.drawPixmap(dst_edges[i], pixmap, QRectF(src_edges[i]))
        painter.drawPixmap(dst_center, pixmap, QRectF(src_center))
    except Exception as e:
        print(f"[Verbose Error] draw_9_slice encountered an error during painting: {e}")