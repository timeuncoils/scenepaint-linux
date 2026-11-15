"""ScenePaint Web — FastAPI application."""
import os
import io
import zipfile
import base64
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.core.document import Document, Layer
from app.core.paint_engine import PaintEngine, BrushTool
from app.core.motion_effects import MotionRenderer, EffectType
from app.analysis.depth import DepthEstimator
from app.analysis.sam import Segmenter

# Paths
DATA_DIR = Path(os.environ.get("SCENEPAINT_DATA_DIR", "/app/data"))
MODEL_DIR = Path(os.environ.get("SCENEPAINT_MODEL_DIR", "/app/models"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ScenePaint Web", version="0.1.0")

# Mount static files
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory state: project_id -> Document + PaintEngine + MotionRenderer
_projects: dict[str, dict] = {}
_state_counter = 0


def _get_state(project_id: str) -> dict:
    if project_id not in _projects:
        raise HTTPException(404, f"Project {project_id} not found")
    return _projects[project_id]


def _new_state(doc: Document) -> dict:
    global _state_counter
    _state_counter += 1
    pid = f"proj_{_state_counter}"
    _projects[pid] = {
        "doc": doc,
        "engine": PaintEngine(doc),
        "renderer": MotionRenderer(doc),
    }
    return pid


# ── Pydantic models ───────────────────────────────────────────

class ProjectCreate(BaseModel):
    width: int = 1920
    height: int = 1080
    bg_color: str = "#1a1a1a"


class ToolAction(BaseModel):
    tool: str  # brush, eraser, bucket, text, outline, move
    x1: int
    y1: int
    x2: Optional[int] = None
    y2: Optional[int] = None
    radius: int = 8
    opacity: float = 1.0
    color: str = "#ffffff"
    text: Optional[str] = None
    font_size: int = 24
    layer_id: Optional[str] = None
    fill_color: Optional[str] = None


class LayerMove(BaseModel):
    layer_id: str
    direction: str  # up, down


class MotionEffect(BaseModel):
    effect_type: str  # boil, blink, glitch, emission, light_spill
    intensity: float = 0.5
    speed: float = 1.0
    duration_frames: int = 60


# ── Routes ─────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/projects")
def create_project(req: ProjectCreate):
    doc = Document(
        width=req.width,
        height=req.height,
        bg_color=req.bg_color,
    )
    pid = _new_state(doc)
    return {"project_id": pid, "width": doc.width, "height": doc.height}


@app.get("/api/projects/{project_id}/canvas")
def get_canvas(project_id: str):
    state = _get_state(project_id)
    img = state["doc"].render()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")


@app.get("/api/projects/{project_id}/layers")
def get_layers(project_id: str):
    state = _get_state(project_id)
    layers = state["doc"].layers
    return {
        "layers": [
            {
                "id": l.id,
                "name": l.name,
                "visible": l.visible,
                "opacity": l.opacity,
                "locked": l.locked,
            }
            for l in layers
        ],
        "active_layer": state["doc"].active_layer_id,
    }


@app.post("/api/projects/{project_id}/layers/new")
def create_layer(project_id: str):
    state = _get_state(project_id)
    layer = state["doc"].add_layer("Layer")
    return {"id": layer.id, "name": layer.name}


@app.put("/api/projects/{project_id}/layers/{layer_id}")
def update_layer(project_id: str, layer_id: str, body: dict = None):
    state = _get_state(project_id)
    layer = state["doc"].get_layer(layer_id)
    if not layer:
        raise HTTPException(404, "Layer not found")
    if body:
        if "name" in body:
            layer.name = body["name"]
        if "opacity" in body:
            layer.opacity = max(0, min(1, body["opacity"]))
        if "visible" in body:
            layer.visible = body["visible"]
    return {"ok": True}


@app.delete("/api/projects/{project_id}/layers/{layer_id}")
def delete_layer(project_id: str, layer_id: str):
    state = _get_state(project_id)
    state["doc"].remove_layer(layer_id)
    return {"ok": True}


@app.post("/api/projects/{project_id}/layers/move")
def move_layer(project_id: str, body: LayerMove):
    state = _get_state(project_id)
    state["doc"].move_layer(body.layer_id, body.direction)
    return {"ok": True}


@app.post("/api/projects/{project_id}/active-layer")
def set_active_layer(project_id: str, body: dict = None):
    state = _get_state(project_id)
    lid = (body or {}).get("layer_id")
    if not lid:
        raise HTTPException(400, "layer_id required")
    state["doc"].set_active_layer(lid)
    return {"ok": True}


@app.post("/api/projects/{project_id}/undo")
def undo(project_id: str):
    state = _get_state(project_id)
    state["engine"].undo()
    return {"ok": True}


@app.post("/api/projects/{project_id}/redo")
def redo(project_id: str):
    state = _get_state(project_id)
    state["engine"].redo()
    return {"ok": True}


@app.post("/api/projects/{project_id}/tool")
def tool_action(project_id: str, action: ToolAction):
    """Execute a painting tool action."""
    state = _get_state(project_id)
    engine = state["engine"]

    # Validate tool
    valid_tools = {"brush", "eraser", "bucket", "text", "outline", "move"}
    if action.tool not in valid_tools:
        raise HTTPException(400, f"Unknown tool: {action.tool}")

    engine.execute_tool(
        tool=action.tool,
        x1=action.x1,
        y1=action.y1,
        x2=action.x2,
        y2=action.y2,
        radius=action.radius,
        opacity=action.opacity,
        color=action.color,
        text=action.text,
        font_size=action.font_size,
        fill_color=action.fill_color,
    )
    return {"ok": True}


@app.post("/api/projects/{project_id}/import")
def import_image(project_id: str, file: UploadFile = File(...)):
    """Import an image as a new layer."""
    state = _get_state(project_id)
    content = file.file.read()
    from PIL import Image
    img = Image.open(io.BytesIO(content))
    layer = state["doc"].add_layer_from_image(file.filename.rsplit(".", 1)[0], img)
    return {"id": layer.id, "width": layer.image.width, "height": layer.image.height}


@app.post("/api/projects/{project_id}/clear-layer")
def clear_layer(project_id: str, body: dict = None):
    lid = (body or {}).get("layer_id")
    if not lid:
        raise HTTPException(400, "layer_id required")
    state = _get_state(project_id)
    layer = state["doc"].get_layer(lid)
    if layer:
        from PIL import Image
        layer.image = Image.new("RGBA", (state["doc"].width, state["doc"].height), (0, 0, 0, 0))
    return {"ok": True}


@app.post("/api/projects/{project_id}/motion")
def apply_motion_effect(project_id: str, effect: MotionEffect):
    """Apply a motion effect and return frames as animated GIF frames."""
    state = _get_state(project_id)
    renderer = state["renderer"]

    effect_type_map = {
        "boil": EffectType.BOIL,
        "blink": EffectType.BLINK,
        "glitch": EffectType.GLITCH,
        "emission": EffectType.EMISSION,
        "light_spill": EffectType.LIGHT_SPILL,
    }
    etype = effect_type_map.get(effect.effect_type)
    if not etype:
        raise HTTPException(400, f"Unknown effect: {effect.effect_type}")

    frames = renderer.render_effect(
        effect_type=etype,
        intensity=effect.intensity,
        speed=effect.speed,
        num_frames=effect.duration_frames,
    )

    # Return frames as base64 list
    frame_data = []
    for frame in frames:
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        buf.seek(0)
        frame_data.append(base64.b64encode(buf.read()).decode())

    return {"frames": frame_data, "count": len(frame_data)}


@app.post("/api/projects/{project_id}/export-gif")
def export_gif(project_id: str, effect: MotionEffect):
    """Export as animated GIF."""
    state = _get_state(project_id)
    renderer = state["renderer"]

    effect_type_map = {
        "boil": EffectType.BOIL,
        "blink": EffectType.BLINK,
        "glitch": EffectType.GLITCH,
        "emission": EffectType.EMISSION,
        "light_spill": EffectType.LIGHT_SPILL,
    }
    etype = effect_type_map.get(effect.effect_type)
    if not etype:
        raise HTTPException(400, f"Unknown effect: {effect.effect_type}")

    frames = renderer.render_effect(
        effect_type=etype,
        intensity=effect.intensity,
        speed=effect.speed,
        num_frames=effect.duration_frames,
    )

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=1000 // effect.speed,
        loop=0,
        optimize=True,
    )
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="image/gif",
        headers={"Content-Disposition": f'attachment; filename="scenepaint_{effect.effect_type}.gif"'},
    )


@app.post("/api/projects/{project_id}/export-mp4")
def export_mp4(project_id: str, effect: MotionEffect):
    """Export as MP4 video."""
    import subprocess
    import tempfile

    state = _get_state(project_id)
    renderer = state["renderer"]

    effect_type_map = {
        "boil": EffectType.BOIL,
        "blink": EffectType.BLINK,
        "glitch": EffectType.GLITCH,
        "emission": EffectType.EMISSION,
        "light_spill": EffectType.LIGHT_SPILL,
    }
    etype = effect_type_map.get(effect.effect_type)
    if not etype:
        raise HTTPException(400, f"Unknown effect: {effect.effect_type}")

    frames = renderer.render_effect(
        effect_type=etype,
        intensity=effect.intensity,
        speed=effect.speed,
        num_frames=effect.duration_frames,
    )

    # Write frames to temp dir, then ffmpeg
    with tempfile.TemporaryDirectory() as tmpdir:
        frame_paths = []
        for i, frame in enumerate(frames):
            fp = Path(tmpdir) / f"frame_{i:04d}.png"
            frame.save(str(fp))
            frame_paths.append(str(fp))

        out_path = Path(tmpdir) / "output.mp4"
        fps = int(effect.speed * 30)
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(tmpdir) + "/frame_%04d.png",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)

        with open(out_path, "rb") as f:
            data = f.read()

    return Response(
        content=data,
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="scenepaint_{effect.effect_type}.mp4"'},
    )


@app.post("/api/projects/{project_id}/save")
def save_project(project_id: str):
    """Save project as .scenepaint file."""
    state = _get_state(project_id)
    doc = state["doc"]
    buf = io.BytesIO()
    doc.save_to_zip(buf)
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}.scenepaint"'},
    )


@app.post("/api/projects/import-zip")
def load_project(file: UploadFile = File(...)):
    """Load a .scenepaint project."""
    content = file.file.read()
    doc = Document.load_from_zip(io.BytesIO(content))
    pid = _new_state(doc)
    return {"project_id": pid, "width": doc.width, "height": doc.height}


@app.post("/api/analysis/depth")
async def analyze_depth(image: UploadFile = File(...)):
    """Run depth estimation on uploaded image."""
    content = await image.read()
    from PIL import Image
    img = Image.open(io.BytesIO(content))

    estimator = DepthEstimator(MODEL_DIR)
    depth_map = estimator.estimate(img)
    if depth_map is None:
        return {"error": "Depth model not found. Place model in /app/models/"}

    buf = io.BytesIO()
    depth_map.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")


@app.post("/api/analysis/segment")
async def segment_image(image: UploadFile = File(...)):
    """Run SAM segmentation on uploaded image."""
    content = await image.read()
    from PIL import Image
    img = Image.open(io.BytesIO(content))

    segmenter = Segmenter(MODEL_DIR)
    mask = segmenter.segment(img)
    if mask is None:
        return {"error": "Segmentation model not found. Place model in /app/models/"}

    buf = io.BytesIO()
    mask.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    _projects.pop(project_id, None)
    return {"ok": True}


@app.get("/api/projects/{project_id}/info")
def project_info(project_id: str):
    state = _get_state(project_id)
    doc = state["doc"]
    return {
        "project_id": project_id,
        "width": doc.width,
        "height": doc.height,
        "layers": len(doc.layers),
        "bg_color": doc.bg_color,
        "undo_count": len(state["engine"].history),
    }
