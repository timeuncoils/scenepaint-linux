"""Motion effects — boil, blink, glitch, emission, light-spill."""
from enum import Enum
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


class EffectType(Enum):
    BOIL = "boil"
    BLINK = "blink"
    GLITCH = "glitch"
    EMISSION = "emission"
    LIGHT_SPILL = "light_spill"


class MotionRenderer:
    """Generate frame sequences for motion effects."""

    def __init__(self, document):
        self.doc = document

    def render_effect(
        self,
        effect_type: EffectType,
        intensity: float = 0.5,
        speed: float = 1.0,
        num_frames: int = 60,
    ) -> list:
        """Render effect frames and return list of PIL Images."""
        base = self.doc.render()
        frames = []

        if effect_type == EffectType.BOIL:
            frames = self._boil(base, intensity, speed, num_frames)
        elif effect_type == EffectType.BLINK:
            frames = self._blink(base, intensity, speed, num_frames)
        elif effect_type == EffectType.GLITCH:
            frames = self._glitch(base, intensity, speed, num_frames)
        elif effect_type == EffectTypeEMISSION:
            frames = self._emission(base, intensity, speed, num_frames)
        elif effect_type == EffectType.LIGHT_SPILL:
            frames = self._light_spill(base, intensity, speed, num_frames)
        else:
            frames = [base] * num_frames

        return frames

    def _boil(self, base: Image, intensity: float, speed: float, num_frames: int) -> list:
        """Line boil — wavy distortion that ripples over time."""
        arr = np.array(base, dtype=np.float32)
        h, w = arr.shape[:2]
        frames = []

        for i in range(num_frames):
            t = (i / num_frames) * math.pi * 2 * speed
            img_arr = arr.copy()

            # Horizontal ripple
            for y in range(h):
                offset = int(math.sin(y * 0.05 * intensity + t) * 10 * intensity)
                if offset != 0:
                    if offset > 0:
                        img_arr[y, offset:] = arr[y, :-offset]
                    else:
                        img_arr[y, :offset] = arr[y, -offset:]

            # Vertical ripple (subtle)
            for x in range(w):
                offset = int(math.cos(x * 0.05 * intensity + t * 0.7) * 3 * intensity)
                if offset != 0:
                    if offset > 0 and y + offset < h:
                        img_arr[y + offset, x] = arr[y, x]

            frames.append(Image.fromarray(img_arr.astype(np.uint8)))

        return frames

    def _blink(self, base: Image, intensity: float, speed: float, num_frames: int) -> list:
        """Blink — rapid visibility pulse."""
        frames = []
        for i in range(num_frames):
            t = i / num_frames
            # Square wave blink
            visible = math.sin(t * math.pi * speed * 4) > 0
            alpha = 255 if visible else max(0, int(255 - intensity * 100))

            if alpha < 255:
                img_arr = np.array(base, dtype=np.float32)
                img_arr[:, :, 3] = img_arr[:, :, 3] * alpha / 255
                frames.append(Image.fromarray(img_arr.astype(np.uint8)))
            else:
                frames.append(base.copy())

        return frames

    def _glitch(self, base: Image, intensity: float, speed: float, num_frames: int) -> list:
        """Glitch — random slice displacement."""
        arr = np.array(base, dtype=np.float32)
        h, w = arr.shape[:2]
        frames = []

        for i in range(num_frames):
            img_arr = arr.copy()
            t = (i / num_frames) * speed

            # Random slice shifts
            num_slices = int(5 * intensity + 1)
            for _ in range(num_slices):
                y_start = np.random.randint(0, h - 10)
                slice_h = np.random.randint(3, min(30, h - y_start))
                shift = int((np.random.random() - 0.5) * 50 * intensity)
                y_end = min(y_start + slice_h, h)

                if abs(shift) > 0:
                    if shift > 0:
                        img_arr[y_start:y_end, shift:] = arr[y_start:y_end, :-shift]
                    else:
                        img_arr[y_start:y_end, :shift] = arr[y_start:y_end, -shift:]

            # Color channel separation (RGB shift)
            if intensity > 0.3:
                shift_amt = int(intensity * 5)
                r = np.roll(img_arr[:, :, 0], shift_amt)
                b = np.roll(img_arr[:, :, 2], -shift_amt)
                img_arr[:, :, 0] = r
                img_arr[:, :, 2] = b

            frames.append(Image.fromarray(img_arr.astype(np.uint8)))

        return frames

    def _emission(self, base: Image, intensity: float, speed: float, num_frames: int) -> list:
        """Emission — glowing outline effect that pulses."""
        frames = []
        for i in range(num_frames):
            t = (i / num_frames) * math.pi * 2 * speed
            glow = int(intensity * 127 * (0.5 + 0.5 * math.sin(t)))

            # Convert to grayscale for edge detection
            gray = base.convert("L")
            edges = gray.filter(ImageFilter.FIND_EDGES)

            # Create glow mask from edges
            glow_arr = np.zeros((base.height, base.width, 4), dtype=np.uint8)

            edge_mask = np.array(edges)
            glow_mask = np.clip(edge_mask, 0, glow)

            rgb = base.convert("RGB")
            rgb_arr = np.array(rgb, dtype=np.float32)

            # Add glow to edge areas
            alpha_channel = np.clip(edge_mask.astype(float) * intensity * 2, 0, 255).astype(np.uint8)
            result_arr = rgb_arr.copy()
            result_arr[:, :, 3] = alpha_channel

            # Blend with original
            blend = np.clip(
                rgb_arr * 0.7 + result_arr * 0.3,
                0, 255
            ).astype(np.uint8)

            # Add colored glow overlay
            glow_color = np.array([
                int(255 * intensity * (0.5 + 0.5 * math.sin(t))),
                int(200 * intensity * (0.5 + 0.5 * math.cos(t))),
                int(100 * intensity),
                glow
            ])

            frames.append(Image.fromarray(blend))

        return frames

    def _light_spill(self, base: Image, intensity: float, speed: float, num_frames: int) -> list:
        """Light spill — directional light that sweeps across."""
        frames = []
        for i in range(num_frames):
            t = (i / num_frames) * math.pi * 2 * speed

            # Create light direction
            light_x = int(math.cos(t) * base.width * 0.5 + base.width * 0.5)
            light_y = int(math.sin(t) * base.height * 0.5 + base.height * 0.5)

            arr = np.array(base, dtype=np.float32)

            # Add light gradient
            for y in range(base.height):
                for x in range(base.width):
                    dist = math.sqrt((x - light_x) ** 2 + (y - light_y) ** 2)
                    max_dist = max(base.width, base.height) * 0.5
                    if dist < max_dist:
                        brightness = intensity * (1 - dist / max_dist) * 40
                        arr[y, x, 0] = min(255, arr[y, x, 0] + brightness * 1.2)
                        arr[y, x, 1] = min(255, arr[y, x, 1] + brightness * 0.9)
                        arr[y, x, 2] = min(255, arr[y, x, 2] + brightness * 0.6)

            frames.append(Image.fromarray(arr.astype(np.uint8)))

        return frames
