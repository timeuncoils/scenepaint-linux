# 🎨 Selfhosted Deep Brush

> A self-hosted, Dockerizable port of **SCENEPAINT** — the **Adobe MAX 2026** Project Deep Brush concept that was made into a mac app by [@TridentVibes](https://github.com/TridentVibes).

## 📖 Story

**Project Deep Brush** was showcased at **Adobe MAX 2026** — a revolutionary digital painting concept. [@TridentVibes](https://github.com/TridentVibes) vibe-coded **SCENEPAINT**, an open-source macOS version of that concept.

This project is our **self-hosted, Dockerizable Linux port** — bringing the same creative power to anyone, anywhere, without cloud dependency.

## ✨ Features

| Category | Details |
|----------|---------|
| **🖌️ Painting Tools** | Brush, eraser, bucket fill, text, outline, move tool |
| **🎭 Motion Effects** | Boil, blink, glitch, emission, light-spill animation engine |
| **🧠 AI Analysis** | Local depth estimation (ONNX), semantic segmentation masks |
| **📂 Project System** | Save/load `.scenepaint` zip archives, layer management, undo/redo |
| **🐳 Docker Deploy** | One-command deploy, browser accessible |
| **🔒 Self-hosted** | All processing local, no cloud dependency |

## 🚀 Quick Start

```bash
git clone https://github.com/timeuncoils/scenepaint-linux.git
cd scenepaint-linux
docker compose up -d --build
```

Open **http://localhost:8001** 🎨

API docs at **http://localhost:8001/docs**

## 🏗️ Tech Stack

- **Backend:** FastAPI (Python 3.12)
- **Frontend:** HTML5 Canvas, vanilla JS, dark theme CSS
- **AI:** ONNX Runtime (depth estimation, SAM segmentation)
- **Image Processing:** Pillow, NumPy, OpenCV
- **Video:** FFmpeg integration
- **Deployment:** Docker + docker-compose

## 📁 Project Structure

```
scenepaint-linux/
├── app/
│   ├── main.py              # FastAPI entry point & routes
│   ├── core/
│   │   ├── document.py      # Document, layers, undo/redo
│   │   ├── paint_engine.py  # Brush, eraser, fill, text tools
│   │   └── motion_effects.py # Boil, blink, glitch, emission
│   ├── analysis/
│   │   ├── depth.py         # Depth estimation (ONNX)
│   │   └── sam.py           # Semantic segmentation
│   ├── effects/             # Post-processing effects
│   └── models/              # AI model weights
├── static/
│   ├── index.html           # Canvas UI
│   ├── css/style.css        # Dark theme
│   └── js/app.js            # Frontend engine
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve the app |
| `GET` | `/docs` | Swagger API docs |
| `POST` | `/api/projects` | Create new project |
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/projects/{id}` | Get project details |
| `POST` | `/api/projects/{id}/layers` | Add layer |
| `POST` | `/api/projects/{id}/tools` | Execute painting tool |
| `POST` | `/api/projects/{id}/effects` | Apply motion effect |
| `GET` | `/api/projects/{id}/export` | Export image/video |
| `POST` | `/api/projects/{id}/save` | Save `.scenepaint` zip |

## 📝 License

MIT — vibecoded with 💛

## 🙏 Credits

This project is a self-hosted, Linux/Docker port of **[SCENEPAINT](https://github.com/TridentVibes/SCENEPAINT)** by **[TridentVibes](https://github.com/TridentVibes)**.

**SCENEPAINT** was vibe-coded by @TridentVibes as an open-source implementation of the **Project Deep Brush** concept originally showcased at **Adobe MAX 2026**.

Original concept, design, and source by [@TridentVibes](https://github.com/TridentVibes).
