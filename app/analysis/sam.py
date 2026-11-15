"""Segmentation — SAM-like mask generation."""
import io
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path
from typing import List, Optional, Tuple


class Segmenter:
    """Image segmentation using local onnx model or fallback."""

    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model = None
        self._load_model()

    def _load_model(self):
        model_path = self.model_dir / "sam_model.onnx"
        if not model_path.exists():
            print(f"[Segmenter] Model not found at {model_path}")
            return
        try:
            import onnxruntime as ort
            self.model = ort.InferenceSession(str(model_path))
            print(f"[Segmenter] Loaded model from {model_path}")
        except ImportError:
            print("[Segmenter] onnxruntime not installed")
        except Exception as e:
            print(f"[Segmenter] Failed to load model: {e}")
            self.model = None

    def segment(
        self,
        image: Image.Image,
        points: Optional[List[Tuple[int, int]]] = None,
        boxes: Optional[List[Tuple[int, int, int, int]]] = None,
    ) -> Optional[Image.Image]:
        """Segment image and return mask(s)."""
        if not self.model:
            return self._fallback_segment(image, points, boxes)

        try:
            # Use onnxruntime SAM model
            # Simplified: return a basic mask
            input_size = 1024
            scale = input_size / max(image.size)
            resized = image.resize((int(image.width * scale), int(image.height * scale)))

            arr = np.array(resized).astype(np.float32) / 255.0
            arr = np.transpose(arr, (2, 0, 1))
            arr = np.expand_dims(arr, axis=0)

            input_name = self.model.get_inputs()[0].name
            output_name = self.model.get_outputs()[0].name

            if points:
                # Convert points to model input format
                point_coords = np.array([[p[0] * scale, p[1] * scale] for p in points])
                point_coords = np.expand_dims(point_coords, axis=0)
                point_labels = np.ones((1, len(points)), dtype=np.int32)
                result = self.model.run(
                    [output_name],
                    {input_name: arr, "point_coords": point_coords, "point_labels": point_labels}
                )
            else:
                result = self.model.run([output_name], {input_name: arr})

            mask = result[0][0][0]  # H, W
            mask = (mask > 0).astype(np.uint8) * 255
            mask_img = Image.fromarray(mask, mode='L')
            mask_img = mask_img.resize(image.size, Image.LANCZOS)
            return mask_img

        except Exception as e:
            print(f"[Segmenter] Inference failed: {e}")
            return self._fallback_segment(image, points, boxes)

    def _fallback_segment(
        self,
        image: Image.Image,
        points: Optional[List[Tuple[int, int]]] = None,
        boxes: Optional[List[Tuple[int, int, int, int]]] = None,
    ) -> Optional[Image.Image]:
        """Fallback segmentation using simple color clustering."""
        w, h = image.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)

        if boxes:
            for x1, y1, x2, y2 in boxes:
                draw.rectangle([x1, y1, x2, y2], fill=255)
        elif points:
            # Dilate around click points
            for px, py in points:
                r = 50
                draw.ellipse([px - r, py - r, px + r, py + r], fill=255)
        else:
            # Default: edge-based mask
            arr = np.array(image.convert("L"))
            from scipy import ndimage
            edges = ndimage.sobel(arr, axis=0)
            edges = (edges > 10).astype(np.uint8) * 255
            mask = Image.fromarray(edges, mode='L')

        return mask
