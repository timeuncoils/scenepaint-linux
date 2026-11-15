"""Depth estimation — runs local onnx model for depth map."""
import io
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional


class DepthEstimator:
    """Depth estimation using a local onnx model."""

    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load onnx model if available."""
        model_path = self.model_dir / "depth_model.onnx"
        if not model_path.exists():
            print(f"[DepthEstimator] Model not found at {model_path}")
            return

        try:
            import onnxruntime as ort
            self.model = ort.InferenceSession(str(model_path))
            print(f"[DepthEstimator] Loaded model from {model_path}")
        except ImportError:
            print("[DepthEstimator] onnxruntime not installed")
        except Exception as e:
            print(f"[DepthEstimator] Failed to load model: {e}")
            self.model = None

    def estimate(self, image: Image.Image) -> Optional[Image.Image]:
        """Estimate depth map from image."""
        if not self.model:
            return self._fallback_depth(image)

        try:
            # Preprocess
            img = image.convert("RGB")
            img_resized = img.resize((512, 512))
            input_data = np.array(img_resized, dtype=np.float32) / 255.0
            input_data = np.transpose(input_data, (2, 0, 1))  # HWC -> CHW
            input_data = np.expand_dims(input_data, axis=0)

            # Run inference
            input_name = self.model.get_inputs()[0].name
            output_name = self.model.get_outputs()[0].name
            result = self.model.run([output_name], {input_name: input_data})

            # Post-process
            depth = result[0][0][0]  # H, W
            depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
            depth = (depth * 255).astype(np.uint8)

            depth_img = Image.fromarray(depth, mode='L')
            depth_img = depth_img.resize(image.size, Image.LANCZOS)
            return depth_img

        except Exception as e:
            print(f"[DepthEstimator] Inference failed: {e}")
            return self._fallback_depth(image)

    def _fallback_depth(self, image: Image.Image) -> Image.Image:
        """Fallback: generate a simple gradient depth map."""
        w, h = image.size
        depth = np.zeros((h, w), dtype=np.uint8)

        # Simple gradient: center is closer (brighter)
        center_x, center_y = w // 2, h // 2
        max_dist = np.sqrt(center_x**2 + center_y**2)

        for y in range(h):
            for x in range(w):
                dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                depth[y, x] = int(255 * (1 - dist / max_dist))

        return Image.fromarray(depth, mode='L')
