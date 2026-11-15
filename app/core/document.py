"""Document model — layers, history, project save/load."""
import uuid
import io
import json
import zipfile
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

from PIL import Image, ImageDraw, ImageFont


@dataclass
class Layer:
    id: str
    name: str
    image: Any  # PIL Image RGBA
    visible: bool = True
    opacity: float = 1.0
    locked: bool = False
    x_offset: int = 0
    y_offset: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "locked": self.locked,
            "x_offset": self.x_offset,
            "y_offset": self.y_offset,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Layer":
        img = Image.open(io.BytesIO(data["image_data"]))
        return cls(
            id=data["id"],
            name=data["name"],
            image=img,
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            locked=data.get("locked", False),
            x_offset=data.get("x_offset", 0),
            y_offset=data.get("y_offset", 0),
        )


@dataclass
class HistoryEntry:
    layer_id: str
    action: str  # "paint", "clear", "move", "create", "delete", "undo", "redo"
    before_state: Optional[str] = None  # base64 or snapshot ref
    after_state: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


class Document:
    def __init__(self, width: int = 1920, height: int = 1080, bg_color: str = "#1a1a1a"):
        self.id = str(uuid.uuid4())[:8]
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.layers: List[Layer] = []
        self.active_layer_id: Optional[str] = None
        self.history: List[HistoryEntry] = []
        self.redo_stack: List[HistoryEntry] = []
        self.version = "1.0"

        # Create background layer
        bg = Image.new("RGBA", (width, height), self._hex_to_rgba(bg_color))
        self.add_layer("Background", bg, is_init=True)

    @staticmethod
    def _hex_to_rgba(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r, g, b, 255)

    def add_layer(self, name: str = "Layer", image: Optional[Image.Image] = None, is_init: bool = False) -> Layer:
        if image is None:
            image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        layer = Layer(
            id=str(uuid.uuid4())[:8],
            name=name,
            image=image,
        )
        self.layers.append(layer)
        if not is_init:
            self.active_layer_id = layer.id
            self.history.append(HistoryEntry(
                layer_id=layer.id,
                action="create",
                params={"name": name, "width": self.width, "height": self.height},
            ))
        return layer

    def add_layer_from_image(self, name: str, image: Image.Image) -> Layer:
        # Resize image to fit canvas if needed
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        if image.width > self.width or image.height > self.height:
            image.thumbnail((self.width, self.height), Image.LANCZOS)
        layer = self.add_layer(name, image)
        return layer

    def get_layer(self, layer_id: str) -> Optional[Layer]:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def remove_layer(self, layer_id: str):
        self.layers = [l for l in self.layers if l.id != layer_id]
        if self.active_layer_id == layer_id:
            self.active_layer_id = self.layers[-1].id if self.layers else None
        self.history.append(HistoryEntry(layer_id=layer_id, action="delete"))

    def move_layer(self, layer_id: str, direction: str):
        idx = next((i for i, l in enumerate(self.layers) if l.id == layer_id), -1)
        if idx < 0:
            return
        if direction == "up" and idx < len(self.layers) - 1:
            self.layers[idx], self.layers[idx + 1] = self.layers[idx + 1], self.layers[idx]
        elif direction == "down" and idx > 0:
            self.layers[idx], self.layers[idx - 1] = self.layers[idx - 1], self.layers[idx]

    def set_active_layer(self, layer_id: str):
        if self.get_layer(layer_id):
            self.active_layer_id = layer_id

    def active_layer(self) -> Optional[Layer]:
        if not self.active_layer_id:
            return None
        return self.get_layer(self.active_layer_id)

    def render(self) -> Image.Image:
        """Composite all visible layers onto background."""
        result = Image.new("RGBA", (self.width, self.height), self._hex_to_rgba(self.bg_color))
        for layer in self.layers:
            if not layer.visible:
                continue
            if layer.opacity < 1.0:
                img = layer.image.copy()
                # Apply opacity via alpha channel
                r, g, b, a = img.split()
                a = a.point(lambda x: int(x * layer.opacity))
                img = Image.merge("RGBA", (r, g, b, a))
            # Paste with offset
            paste_x = layer.x_offset
            paste_y = layer.y_offset
            # Calculate offset to center if layer differs from canvas
            if layer.x_offset == 0 and layer.y_offset == 0 and layer.image.size != (self.width, self.height):
                paste_x = (self.width - layer.image.width) // 2
                paste_y = (self.height - layer.image.height) // 2
            result.paste(img, (paste_x, paste_y), img)
        return result

    def save_to_zip(self, buf: io.BytesIO):
        """Save document to .scenepaint zip."""
        manifest = {
            "version": self.version,
            "width": self.width,
            "height": self.height,
            "bg_color": self.bg_color,
            "active_layer_id": self.active_layer_id,
            "layers": [],
        }
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for layer in self.layers:
                # Save layer image
                img_buf = io.BytesIO()
                layer.image.save(img_buf, format="PNG")
                img_buf.seek(0)
                zf.writestr(f"layers/{layer.id}.png", img_buf.read())

                # Layer metadata
                meta = layer.to_dict()
                meta["image_data"] = None  # Don't serialize image in meta
                manifest["layers"].append(meta)

            # Save manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    @classmethod
    def load_from_zip(cls, buf: io.BytesIO) -> "Document":
        with zipfile.ZipFile(buf, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))
            doc = cls(
                width=manifest["width"],
                height=manifest["height"],
                bg_color=manifest.get("bg_color", "#1a1a1a"),
            )
            doc.active_layer_id = manifest.get("active_layer_id")

            for layer_data in manifest["layers"]:
                img_data = zf.read(f"layers/{layer_data['id']}.png")
                img = Image.open(io.BytesIO(img_data))
                layer = Layer(
                    id=layer_data["id"],
                    name=layer_data["name"],
                    image=img,
                    visible=layer_data.get("visible", True),
                    opacity=layer_data.get("opacity", 1.0),
                    locked=layer_data.get("locked", False),
                    x_offset=layer_data.get("x_offset", 0),
                    y_offset=layer_data.get("y_offset", 0),
                )
                doc.layers.append(layer)

        return doc
