"""Paint engine — brush, eraser, bucket fill, text, outline, move tools."""
import io
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from enum import Enum
from app.core.document import Document


class BrushTool(Enum):
    BRUSH = "brush"
    ERASER = "eraser"
    BUCKET = "bucket"
    TEXT = "text"
    OUTLINE = "outline"
    MOVE = "move"


class PaintEngine:
    """Handles all painting tool operations."""

    def __init__(self, doc: Document):
        self.doc = doc
        self.history = []
        self.redo_stack = []
        self.max_history = 50

    def _save_state(self, layer_id: str, action: str):
        """Save layer state for undo."""
        layer = self.doc.get_layer(layer_id)
        if layer:
            img_buf = io.BytesIO()
            layer.image.save(img_buf, format="PNG")
            img_buf.seek(0)
            self.history.append({
                "layer_id": layer_id,
                "action": action,
                "image_data": img_buf.getvalue(),
            })
            if len(self.history) > self.max_history:
                self.history.pop(0)
            self.redo_stack.clear()

    def undo(self):
        if not self.history:
            return
        entry = self.history.pop()
        layer = self.doc.get_layer(entry["layer_id"])
        if layer:
            # Save current state for redo
            img_buf = io.BytesIO()
            layer.image.save(img_buf, format="PNG")
            img_buf.seek(0)
            self.redo_stack.append({
                "layer_id": entry["layer_id"],
                "image_data": img_buf.getvalue(),
            })
            # Restore previous state
            layer.image = Image.open(io.BytesIO(entry["image_data"]))

    def redo(self):
        if not self.redo_stack:
            return
        entry = self.redo_stack.pop()
        layer = self.doc.get_layer(entry["layer_id"])
        if layer:
            img_buf = io.BytesIO()
            layer.image.save(img_buf, format="PNG")
            img_buf.seek(0)
            self.history.append({
                "layer_id": entry["layer_id"],
                "image_data": img_buf.getvalue(),
            })
            layer.image = Image.open(io.BytesIO(entry["image_data"]))

    def execute_tool(
        self,
        tool: str,
        x1: int,
        y1: int,
        x2: int = None,
        y2: int = None,
        radius: int = 8,
        opacity: float = 1.0,
        color: str = "#ffffff",
        text: str = None,
        font_size: int = 24,
        fill_color: str = None,
    ):
        """Execute a tool action on the active layer."""
        layer = self.doc.active_layer()
        if not layer:
            raise ValueError("No active layer")
        if layer.locked:
            raise ValueError("Layer is locked")

        self._save_state(layer.id, tool)

        if tool == "brush":
            self._brush(layer, x1, y1, x2 or x1, y2 or y1, radius, color, opacity)
        elif tool == "eraser":
            self._eraser(layer, x1, y1, x2 or x1, y2 or y1, radius)
        elif tool == "bucket":
            self._bucket_fill(layer, x1, y1, fill_color or color)
        elif tool == "text":
            self._text(layer, x1, y1, text or "", font_size, color)
        elif tool == "outline":
            self._outline(layer, x1, y1, x2 or x1, y2 or y1, radius, color, opacity)
        elif tool == "move":
            self._move(layer, x1, y1, x2 or x1, y2 or y1)

    def _brush(self, layer, x1, y1, x2, y2, radius, color, opacity):
        """Draw with brush tool."""
        draw = ImageDraw.Draw(layer.image)
        rgba = self._hex_to_rgba(color, int(255 * opacity))
        draw.line([(x1, y1), (x2, y2)], fill=rgba, width=radius)

    def _eraser(self, layer, x1, y1, x2, y2, radius):
        """Erase with eraser tool."""
        draw = ImageDraw.Draw(layer.image)
        draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0, 0), width=radius)

    def _bucket_fill(self, layer, x, y, color):
        """Flood fill at point."""
        arr = np.array(layer.image, dtype=np.uint8)
        h, w = arr.shape[:2]

        # Get target color
        target = tuple(arr[y, x, :3])
        rgba = self._hex_to_rgba(color, 255)

        # BFS flood fill
        if target == (rgba[0], rgba[1], rgba[2]):
            return

        queue = [(x, y)]
        visited = set()
        visited.add((x, y))

        while queue:
            cx, cy = queue.pop(0)
            if 0 <= cx < w and 0 <= cy < h:
                current = tuple(arr[cy, cx, :3])
                if abs(current[0] - target[0]) < 30 and \
                   abs(current[1] - target[1]) < 30 and \
                   abs(current[2] - target[2]) < 30:
                    arr[cy, cx, :3] = rgba[:3]
                    arr[cy, cx, 3] = rgba[3]
                    for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                        if (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append((nx, ny))

        layer.image = Image.fromarray(arr)

    def _text(self, layer, x, y, text, font_size, color):
        """Draw text."""
        draw = ImageDraw.Draw(layer.image)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        rgba = self._hex_to_rgba(color, 255)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x, y), text, fill=rgba, font=font)

    def _outline(self, layer, x1, y1, x2, y2, radius, color, opacity):
        """Draw outline/selection box."""
        draw = ImageDraw.Draw(layer.image)
        rgba = self._hex_to_rgba(color, int(255 * opacity))
        draw.rectangle([x1, y1, x2, y2], outline=rgba, width=2)
        draw.rectangle([x1, y1, x2, y2], fill=tuple(int(c * 0.1) for c in rgba[:3]) + (int(64 * opacity),))

    def _move(self, layer, x1, y1, x2, y2):
        """Move layer content."""
        dx = x2 - x1
        dy = y2 - y1
        layer.x_offset += dx
        layer.y_offset += dy

    @staticmethod
    def _hex_to_rgba(hex_color, alpha=255):
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r, g, b, alpha)
