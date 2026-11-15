# 🎨 Selfhosted Deep Brush

> Vibecoded digital painting & animation studio. Self-hosted, browser-based, zero cloud dependency.

[![vibecoded](https://img.shields.io/badge/vibecoded-%23FF6B35?style=for-the-badge&logo=github)](https://github.com/timeuncoils/scenepaint-linux)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/)

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

## 📸 Screenshots

![ScenePaint Web](https://i.imgur.com/placeholder.png)

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

## 🤝 Contributing

PRs welcome. Please keep the vibecoded energy 🎨🔥

---

**Built for creators who value privacy and self-reliance.**
