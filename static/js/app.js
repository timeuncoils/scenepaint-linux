/* ScenePaint Web — Main Application */

// ── State ──────────────────────────────────────────────────────────
const state = {
  projectId: null,
  canvasWidth: 1920,
  canvasHeight: 1080,
  tool: 'brush',
  color: '#ffffff',
  brushSize: 8,
  opacity: 1.0,
  feather: 0,
  hardness: 1.0,
  spacing: 0.25,
  zoom: 1.0,
  panX: 0,
  panY: 0,
  isDrawing: false,
  lastX: 0,
  lastY: 0,
  layers: [],
  activeLayerId: null,
  selectedPoints: [], // for bucket fill
  effectIntensity: 0.5,
  effectSpeed: 1.0,
  effectFrames: 60,
  textFont: 'sans-serif',
  textSize: 24,
  textBold: false,
  textItalic: false,
  lightIntensity: 0.5,
  lightAngle: 45,
  lightHeight: 30,
  lightColor: '#ffffff',
  showGrid: false,
  showNormals: false,
  // History for undo (client-side)
  undoStack: [],
  redoStack: [],
  maxUndo: 50,
};

// ── Canvas refs ────────────────────────────────────────────────────
const canvas = document.getElementById('main-canvas');
const ctx = canvas.getContext('2d');
const canvasContainer = document.getElementById('canvas-container');

// ── API helper ─────────────────────────────────────────────────────
async function api(path, method = 'GET', body = null, formData = false) {
  const opts = { method, headers: {} };
  if (formData) {
    // FormData — don't set Content-Type
  } else if (body instanceof Object && !(body instanceof Blob)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else {
    opts.body = body;
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path}: ${res.status} ${err}`);
  }
  const ct = res.headers.get('Content-Type') || '';
  if (ct.includes('application/json')) return res.json();
  if (ct.includes('image/') || ct.includes('video/')) return res.blob();
  return res.text();
}

// ── Project management ─────────────────────────────────────────────
async function newProject() {
  const w = parseInt(prompt('Width (px):', '1920')) || 1920;
  const h = parseInt(prompt('Height (px):', '1080')) || 1080;
  const bg = document.getElementById('bgColorInput')?.value || '#1a1a1a';
  const data = await api('/api/projects', 'POST', { width: w, height: h, bg_color: bg });
  state.projectId = data.project_id;
  state.canvasWidth = w;
  state.canvasHeight = h;
  state.layers = [];
  state.activeLayerId = null;
  state.undoStack = [];
  state.redoStack = [];
  setStatus('New project created');
  updateCanvasSize();
  renderCanvas();
  loadLayers();
}

async function openFile() {
  const input = document.getElementById('fileInput');
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    if (file.name.endsWith('.scenepaint') || file.name.endsWith('.zip')) {
      const data = await api('/api/projects/import-zip', 'POST', fd, true);
      state.projectId = data.project_id;
      state.canvasWidth = data.width;
      state.canvasHeight = data.height;
      state.undoStack = [];
      state.redoStack = [];
      setStatus(`Loaded ${file.name}`);
      updateCanvasSize();
      renderCanvas();
      loadLayers();
    } else {
      // Import as image layer
      if (!state.projectId) await newProjectAuto();
      const data = await api(`/api/projects/${state.projectId}/import`, 'POST', fd, true);
      setStatus(`Imported ${file.name} as layer`);
      loadLayers();
      renderCanvas();
    }
    input.value = '';
  };
  input.click();
}

async function newProjectAuto() {
  const data = await api('/api/projects', 'POST', { width: 1920, height: 1080, bg_color: '#1a1a1a' });
  state.projectId = data.project_id;
  state.canvasWidth = 1920;
  state.canvasHeight = 1080;
  state.undoStack = [];
  state.redoStack = [];
  updateCanvasSize();
  renderCanvas();
  loadLayers();
}

async function saveProject() {
  if (!state.projectId) return;
  const link = document.createElement('a');
  link.href = `/api/projects/${state.projectId}/save`;
  link.download = `project_${state.projectId}.scenepaint`;
  link.click();
  setStatus('Project saved');
}

async function exportPNG() {
  if (!state.projectId) return;
  const link = document.createElement('a');
  link.href = `/api/projects/${state.projectId}/canvas`;
  link.download = 'scenepaint_export.png';
  link.click();
}

async function exportGIF() {
  if (!state.projectId) return;
  const type = document.getElementById('effectType')?.value || 'boil';
  const intensity = (document.getElementById('intensitySlider')?.value || 50) / 100;
  const speed = (document.getElementById('speedSlider')?.value || 10) / 10;
  const frames = parseInt(document.getElementById('framesSlider')?.value || 60);
  showProgress('Generating GIF...');
  try {
    const blob = await api(`/api/projects/${state.projectId}/export-gif`, 'POST', {
      effect_type: type, intensity, speed, duration_frames: frames
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `scenepaint_${type}.gif`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus('GIF exported');
  } catch (e) {
    setStatus(`Export failed: ${e.message}`);
  }
  hideProgress();
}

async function exportMP4() {
  if (!state.projectId) return;
  const type = document.getElementById('effectType')?.value || 'boil';
  const intensity = (document.getElementById('intensitySlider')?.value || 50) / 100;
  const speed = (document.getElementById('speedSlider')?.value || 10) / 10;
  const frames = parseInt(document.getElementById('framesSlider')?.value || 60);
  showProgress('Rendering MP4...');
  try {
    const blob = await api(`/api/projects/${state.projectId}/export-mp4`, 'POST', {
      effect_type: type, intensity, speed, duration_frames: frames
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `scenepaint_${type}.mp4`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus('MP4 exported');
  } catch (e) {
    setStatus(`Export failed: ${e.message}`);
  }
  hideProgress();
}

// ── Canvas sizing & rendering ──────────────────────────────────────
function updateCanvasSize() {
  const containerRect = canvasContainer.getBoundingClientRect();
  const maxW = containerRect.width - 40;
  const maxH = containerRect.height - 40;
  const scale = Math.min(maxW / state.canvasWidth, maxH / state.canvasHeight, 1);
  state.zoom = scale;
  canvas.width = state.canvasWidth;
  canvas.height = state.canvasHeight;
  canvas.style.width = Math.round(state.canvasWidth * scale) + 'px';
  canvas.style.height = Math.round(state.canvasHeight * scale) + 'px';
  canvas.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${scale})`;
  canvas.style.transformOrigin = 'center center';
  document.getElementById('zoomDisplay').textContent = Math.round(scale * 100) + '%';
  document.getElementById('canvasSize').textContent = `${state.canvasWidth} × ${state.canvasHeight}`;
}

function fitCanvas() {
  state.panX = 0;
  state.panY = 0;
  updateCanvasSize();
}

function zoomIn() {
  state.zoom = Math.min(5, state.zoom * 1.25);
  updateCanvasSize();
}

function zoomOut() {
  state.zoom = Math.max(0.05, state.zoom / 1.25);
  updateCanvasSize();
}

function renderCanvas() {
  if (!state.projectId) return;
  // Fetch current canvas from server
  fetch(`/api/projects/${state.projectId}/canvas`)
    .then(r => r.blob())
    .then(blob => {
      const img = new Image();
      img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#1a1a1a';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        // Draw checkerboard pattern for transparency
        drawCheckerboard();
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      };
      img.src = URL.createObjectURL(blob);
    })
    .catch(e => setStatus('Error loading canvas: ' + e.message));
}

function drawCheckerboard() {
  const size = 10;
  ctx.fillStyle = '#222';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#2a2a2a';
  for (let y = 0; y < canvas.height; y += size) {
    for (let x = 0; x < canvas.width; x += size) {
      if ((Math.floor(x / size) + Math.floor(y / size)) % 2 === 0) {
        ctx.fillRect(x, y, size, size);
      }
    }
  }
}

// ── Layer management ───────────────────────────────────────────────
async function loadLayers() {
  if (!state.projectId) return;
  try {
    const data = await api(`/api/projects/${state.projectId}/layers`);
    state.layers = data.layers;
    state.activeLayerId = data.active_layer_id;
    renderLayerList();
  } catch (e) {
    setStatus('Error loading layers: ' + e.message);
  }
}

function renderLayerList() {
  const list = document.getElementById('layerList');
  list.innerHTML = '';

  // Render in reverse (top layer first)
  [...state.layers].reverse().forEach(layer => {
    const isActive = layer.id === state.activeLayerId;
    const item = document.createElement('div');
    item.className = `layer-item${isActive ? ' active' : ''}`;
    item.onclick = () => setActiveLayer(layer.id);

    item.innerHTML = `
      <button class="small-btn" onclick="event.stopPropagation(); toggleLayerVisibility('${layer.id}')" title="Toggle visibility">
        ${layer.visible ? '👁' : '👁‍🗨'}
      </button>
      <div class="layer-info">
        <div class="layer-name">${layer.name}</div>
        <div class="layer-props">${layer.opacity < 1 ? Math.round(layer.opacity * 100) + '% opacity' : ''}</div>
      </div>
      <div class="layer-actions">
        <button onclick="event.stopPropagation(); moveLayer('${layer.id}', 'up')" title="Move up">▲</button>
        <button onclick="event.stopPropagation(); moveLayer('${layer.id}', 'down')" title="Move down">▼</button>
        <button onclick="event.stopPropagation(); deleteLayer('${layer.id}')" title="Delete">✕</button>
      </div>
    `;
    list.appendChild(item);
  });
}

async function setActiveLayer(layerId) {
  if (!state.projectId) return;
  await api(`/api/projects/${state.projectId}/active-layer`, 'POST', null, {
    formData: true,
    extra: [[['layer_id', layerId]]]
  });
  // Use form-based approach
  const fd = new FormData();
  fd.append('layer_id', layerId);
  await api(`/api/projects/${state.projectId}/active-layer`, 'POST', fd, true);
  state.activeLayerId = layerId;
  renderLayerList();
}

async function toggleLayerVisibility(layerId) {
  const layer = state.layers.find(l => l.id === layerId);
  if (!layer) return;
  layer.visible = !layer.visible;
  await api(`/api/projects/${state.projectId}/layers/${layerId}`, 'PUT', {
    visible: layer.visible
  });
  renderLayerList();
  renderCanvas();
}

async function moveLayer(layerId, direction) {
  if (!state.projectId) return;
  await api(`/api/projects/${state.projectId}/layers/move`, 'POST', {
    layer_id: layerId,
    direction
  });
  renderCanvas();
  loadLayers();
}

async function deleteLayer(layerId) {
  if (!state.projectId) return;
  if (state.layers.length <= 1) {
    setStatus('Cannot delete the last layer');
    return;
  }
  await api(`/api/projects/${state.projectId}/layers/${layerId}`, 'DELETE');
  renderCanvas();
  loadLayers();
}

async function addLayer() {
  if (!state.projectId) return;
  const name = prompt('Layer name:', 'Layer ' + (state.layers.length + 1));
  if (!name) return;
  const data = await api(`/api/projects/${state.projectId}/layers/new`, 'POST');
  renderCanvas();
  loadLayers();
}

// ── Tool handling ──────────────────────────────────────────────────
function setTool(tool) {
  state.tool = tool;
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tool === tool);
  });

  // Update cursor style
  switch (tool) {
    case 'brush': canvas.style.cursor = 'crosshair'; break;
    case 'eraser': canvas.style.cursor = 'crosshair'; break;
    case 'bucket': canvas.style.cursor = 'pointer'; break;
    case 'text': canvas.style.cursor = 'text'; break;
    case 'outline': canvas.style.cursor = 'crosshair'; break;
    case 'move': canvas.style.cursor = 'grab'; break;
    default: canvas.style.cursor = 'crosshair';
  }
}

function setColor(color) {
  state.color = color;
  document.getElementById('colorPicker').value = color;
}

function setBrushSize(size) {
  state.brushSize = parseInt(size);
  document.getElementById('brushSizeVal').textContent = size;
  document.getElementById('panelBrushSize').textContent = size;
}

function setOpacity(val) {
  state.opacity = parseInt(val) / 100;
  document.getElementById('opacityVal').textContent = val;
  document.getElementById('panelOpacity').textContent = val;
}

function setFeather(val) {
  state.feather = parseInt(val);
  document.getElementById('featherVal').textContent = val;
}

function setHardness(val) {
  state.hardness = parseInt(val) / 100;
  document.getElementById('panelHardness').textContent = val;
}

function setSpacing(val) {
  state.spacing = parseInt(val) / 100;
  document.getElementById('panelSpacing').textContent = val;
}

function setTextSize(size) {
  state.textSize = parseInt(size);
  document.getElementById('panelTextSize').textContent = size;
}

function setLightIntensity(val) {
  state.lightIntensity = parseInt(val) / 100;
  document.getElementById('lightIntensity').textContent = val;
  updateLightPreview();
}

function setLightAngle(val) {
  state.lightAngle = parseInt(val);
  document.getElementById('lightAngle').textContent = val;
  updateLightPreview();
}

function setLightHeight(val) {
  state.lightHeight = parseInt(val);
  document.getElementById('lightHeight').textContent = val;
  updateLightPreview();
}

function updateLightPreview() {
  const preview = document.getElementById('lightPreview');
  if (!preview) return;
  const angle = state.lightAngle * Math.PI / 180;
  const x = 50 + 40 * Math.cos(angle);
  const y = 50 + 40 * Math.sin(angle);
  preview.style.background = `radial-gradient(circle at ${x}% ${y}%, ${state.lightColor}40, transparent 60%), linear-gradient(135deg, #333, #111)`;
}

// ── Canvas mouse events ────────────────────────────────────────────
let mouseDownPos = null;
let lastStrokePos = null;

canvas.addEventListener('mousedown', (e) => {
  if (!state.projectId) return;
  const rect = canvas.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left) / state.zoom - state.panX / state.zoom);
  const y = Math.round((e.clientY - rect.top) / state.zoom - state.panY / state.zoom);

  state.isDrawing = true;
  mouseDownPos = { x, y };
  lastStrokePos = { x, y };

  if (state.tool === 'bucket') {
    state.selectedPoints = [{ x, y }];
    floodFillPreview(x, y);
    return;
  }

  if (state.tool === 'text') {
    showTextPopup(x, y);
    return;
  }

  // Save state for undo
  saveUndoState();

  if (state.tool === 'outline') {
    // Store start for rectangle preview
    state.outlineStart = { x, y };
  }

  sendToolAction(state.tool, x, y, x, y);
});

canvas.addEventListener('mousemove', (e) => {
  const rect = canvas.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left) / state.zoom - state.panX / state.zoom);
  const y = Math.round((e.clientY - rect.top) / state.zoom - state.panY / state.zoom);
  document.getElementById('cursorPos').textContent = `${x}, ${y}`;

  if (!state.isDrawing) return;

  if (state.tool === 'outline' && state.outlineStart) {
    // Draw live preview of outline rectangle
    renderCanvas();
    ctx.strokeStyle = state.color;
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.strokeRect(
      state.outlineStart.x,
      state.outlineStart.y,
      x - state.outlineStart.x,
      y - state.outlineStart.y
    );
    ctx.setLineDash([]);
    return;
  }

  sendToolAction(state.tool, lastStrokePos.x, lastStrokePos.y, x, y);
  lastStrokePos = { x, y };
});

canvas.addEventListener('mouseup', (e) => {
  if (!state.isDrawing) return;
  state.isDrawing = false;

  const rect = canvas.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left) / state.zoom - state.panX / state.zoom);
  const y = Math.round((e.clientY - rect.top) / state.zoom - state.panY / state.zoom);

  if (state.tool === 'outline' && state.outlineStart) {
    sendToolAction('outline', state.outlineStart.x, state.outlineStart.y, x, y);
    state.outlineStart = null;
  }

  if (state.tool === 'bucket' && state.selectedPoints.length > 0) {
    sendToolAction('bucket', state.selectedPoints[0].x, state.selectedPoints[0].y, null, null, 0, 1.0, null, null, state.color);
  }

  lastStrokePos = null;
  mouseDownPos = null;

  // Re-render after tool action
  renderCanvas();
  loadLayers();
});

canvas.addEventListener('mouseleave', () => {
  if (state.isDrawing) {
    state.isDrawing = false;
  }
});

// ── Pan & zoom with mouse wheel ────────────────────────────────────
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  state.zoom = Math.max(0.05, Math.min(5, state.zoom * delta));
  updateCanvasSize();
}, { passive: false });

// ── Keyboard shortcuts ─────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'z' && e.shiftKey) { e.preventDefault(); redo(); }
    else if (e.key === 'z') { e.preventDefault(); undo(); }
    else if (e.key === 's') { e.preventDefault(); saveProject(); }
    else if (e.key === 'o') { e.preventDefault(); openFile(); }
    else if (e.key === 'e') { e.preventDefault(); exportPNG(); }
    return;
  }

  const toolKeys = { 'a': 'brush', 'e': 'eraser', 'b': 'bucket', 't': 'text', 'o': 'outline', 'v': 'move' };
  if (toolKeys[e.key]) {
    setTool(toolKeys[e.key]);
  }

  if (e.key === '[') {
    setBrushSize(Math.max(1, state.brushSize - 2));
    document.getElementById('brushSize').value = state.brushSize;
    document.getElementById('brushSizeVal').textContent = state.brushSize;
  }
  if (e.key === ']') {
    setBrushSize(Math.min(100, state.brushSize + 2));
    document.getElementById('brushSize').value = state.brushSize;
    document.getElementById('brushSizeVal').textContent = state.brushSize;
  }
});

// ── Tool API calls ─────────────────────────────────────────────────
async function sendToolAction(tool, x1, y1, x2, y2, radius = null, opacity = null, color = null, text = null, fillColor = null) {
  if (!state.projectId) return;

  const data = {
    tool,
    x1, y1, x2: x2 || x1, y2: y2 || y1,
    radius: radius ?? state.brushSize,
    opacity: opacity ?? state.opacity,
    color: color ?? state.color,
    fill_color: fillColor ?? state.color,
  };

  if (text) data.text = text;
  if (state.textSize) data.font_size = state.textSize;
  if (state.activeLayerId) data.layer_id = state.activeLayerId;

  try {
    await api(`/api/projects/${state.projectId}/tool`, 'POST', data);
  } catch (e) {
    setStatus(`Tool error: ${e.message}`);
  }
}

// ── Bucket fill preview ────────────────────────────────────────────
function floodFillPreview(x, y) {
  // Show preview of where the fill will go
  renderCanvas();
  ctx.fillStyle = state.color + '40'; // semi-transparent
  ctx.beginPath();
  ctx.arc(x, y, state.brushSize * 3, 0, Math.PI * 2);
  ctx.fill();
}

// ── Text tool ──────────────────────────────────────────────────────
function showTextPopup(x, y) {
  const popup = document.getElementById('textPopup');
  const input = document.getElementById('textInput');
  popup.classList.remove('hidden');
  // Position popup near click
  const canvasRect = canvas.getBoundingClientRect();
  popup.style.left = (canvasRect.left + x * state.zoom + state.panX) + 'px';
  popup.style.top = (canvasRect.top + y * state.zoom + state.panY) + 'px';
  input.value = '';
  input.focus();
  state.textPos = { x, y };
}

function commitText() {
  const text = document.getElementById('textInput').value;
  if (text && state.textPos) {
    sendToolAction('text', state.textPos.x, state.textPos.y, null, null, 0, 1.0, state.color, text, null);
    renderCanvas();
    setStatus(`Text added: "${text}"`);
  }
  hideTextPopup();
}

function cancelText() {
  hideTextPopup();
}

function hideTextPopup() {
  document.getElementById('textPopup').classList.add('hidden');
}

// ── Undo / Redo ────────────────────────────────────────────────────
async function undo() {
  if (!state.projectId) return;
  await api(`/api/projects/${state.projectId}/undo`, 'POST');
  renderCanvas();
  setStatus('Undo');
}

async function redo() {
  if (!state.projectId) return;
  await api(`/api/projects/${state.projectId}/redo`, 'POST');
  renderCanvas();
  setStatus('Redo');
}

function saveUndoState() {
  // Client-side visual state is managed via server round-trip
  // This is a no-op placeholder; actual undo is server-side
}

// ── Analysis ───────────────────────────────────────────────────────
async function analyzePhoto() {
  if (!state.projectId) {
    setStatus('Open or create a project first');
    return;
  }

  showProgress('Analyzing photo...');
  try {
    // Fetch current canvas
    const res = await fetch(`/api/projects/${state.projectId}/canvas`);
    const blob = await res.blob();
    const fd = new FormData();
    fd.append('image', blob, 'canvas.png');

    const depthBlob = await api('/api/analysis/depth', 'POST', fd, true);
    setStatus('Depth analysis complete');

    // Show depth preview
    const url = URL.createObjectURL(depthBlob);
    const depthPreview = document.getElementById('depthPreview');
    if (depthPreview) {
      depthPreview.innerHTML = `<img src="${url}" style="width:100%;height:100%;object-fit:contain">`;
    }
  } catch (e) {
    setStatus(`Analysis failed: ${e.message}`);
  }
  hideProgress();
}

async function importDepthMap() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/png';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('image', file);
    const blob = await api('/api/analysis/depth', 'POST', fd, true);
    setStatus('Depth map imported');
  };
  input.click();
}

// ── Motion effects ─────────────────────────────────────────────────
async function previewEffect() {
  if (!state.projectId) return;

  const type = document.getElementById('effectType').value;
  const intensity = parseInt(document.getElementById('intensitySlider').value) / 100;
  const speed = parseInt(document.getElementById('speedSlider').value) / 10;
  const frames = parseInt(document.getElementById('framesSlider').value);

  showProgress('Generating preview...');
  document.getElementById('previewBtn').classList.add('animating');

  try {
    const data = await api(`/api/projects/${state.projectId}/motion`, 'POST', {
      effect_type: type, intensity, speed, duration_frames: frames
    });

    // Create animation preview
    const previewDiv = document.createElement('div');
    previewDiv.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:200;background:#111;border:1px solid #444;border-radius:8px;padding:16px;max-width:80vw;max-height:80vh;overflow:auto;';

    const video = document.createElement('video');
    video.controls = true;
    video.autoplay = true;
    video.loop = true;
    video.style.maxWidth = '640px';
    video.style.maxHeight = '480px';

    const stream = video.mozCaptureStream || video.captureStream;
    const blobUrl = URL.createObjectURL(
      new Blob(data.frames.map(f => Uint8Array.from(atob(f), c => c.charCodeAt(0))), { type: 'image/png' })
    );

    // Use canvas-based animation
    const animCanvas = document.createElement('canvas');
    animCanvas.width = state.canvasWidth;
    animCanvas.height = state.canvasHeight;
    animCanvas.style.maxWidth = '640px';
    animCanvas.style.maxHeight = '480px';
    const animCtx = animCanvas.getContext('2d');

    const images = data.frames.map(f => {
      const img = new Image();
      img.src = 'data:image/png;base64,' + f;
      return img;
    });

    let frameIdx = 0;
    const fps = Math.max(1, Math.round(speed * 30));
    const interval = setInterval(() => {
      animCtx.clearRect(0, 0, animCanvas.width, animCanvas.height);
      if (images[frameIdx]) {
        animCtx.drawImage(images[frameIdx], 0, 0);
      }
      frameIdx = (frameIdx + 1) % images.length;
    }, 1000 / fps);

    previewDiv.appendChild(animCanvas);

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '✕ Close';
    closeBtn.style.marginTop = '12px';
    closeBtn.onclick = () => {
      clearInterval(interval);
      previewDiv.remove();
    };
    previewDiv.appendChild(closeBtn);

    document.body.appendChild(previewDiv);
    setStatus('Preview playing');

  } catch (e) {
    setStatus(`Preview error: ${e.message}`);
  }

  document.getElementById('previewBtn').classList.remove('animating');
  hideProgress();
}

// ── UI helpers ─────────────────────────────────────────────────────
function switchTab(tabName) {
  document.querySelectorAll('.sidebar-tabs .tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabName);
  });
  document.querySelectorAll('#sidebar .panel').forEach(p => {
    p.classList.toggle('active', p.id === `panel-${tabName}`);
  });
}

function setIntensity(val) {
  state.effectIntensity = val / 100;
  document.getElementById('intensityVal').textContent = val;
}

function setSpeed(val) {
  state.effectSpeed = val / 10;
  document.getElementById('speedVal').textContent = (val / 10).toFixed(1);
}

function setFrames(val) {
  state.effectFrames = parseInt(val);
  document.getElementById('framesVal').textContent = val;
}

function setStatus(msg) {
  document.getElementById('statusBar').textContent = msg;
  console.log('[ScenePaint]', msg);
}

function showProgress(text) {
  document.getElementById('progressText').textContent = text;
  document.getElementById('progressFill').style.width = '0%';
  document.getElementById('progressOverlay').classList.remove('hidden');
}

function hideProgress() {
  document.getElementById('progressOverlay').classList.add('hidden');
}

function setProgress(pct) {
  document.getElementById('progressFill').style.width = pct + '%';
}

// ── Drag & drop ────────────────────────────────────────────────────
document.addEventListener('dragover', (e) => {
  e.preventDefault();
  e.stopPropagation();
});

document.addEventListener('drop', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  const files = e.dataTransfer.files;
  if (!files.length) return;

  const file = files[0];
  const fd = new FormData();
  fd.append('file', file);

  if (!state.projectId) {
    await newProjectAuto();
  }

  const data = await api(`/api/projects/${state.projectId}/import`, 'POST', fd, true);
  setStatus(`Imported ${file.name}`);
  renderCanvas();
  loadLayers();
});

// ── Window resize ──────────────────────────────────────────────────
window.addEventListener('resize', () => {
  if (state.projectId) {
    updateCanvasSize();
    renderCanvas();
  }
});

// ── Init ───────────────────────────────────────────────────────────
setStatus('ScenePaint — Open or create a project to begin');
