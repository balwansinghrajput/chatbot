# M00 AI Backend

FastAPI backend supporting NVIDIA NIM, MongoDB Atlas / Local MongoDB, Redis caching, Brave/DDG search, and RAG.

## Running with Docker

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 2. Run with Docker Compose (Recommended)
This starts the Backend (`http://localhost:8000`), MongoDB (`27017`), and Redis (`6379`) with persistent storage and healthchecks:
```bash
# From workspace root or backend directory:
docker compose up --build -d
```

To view logs:
```bash
docker compose logs -f backend
```

To stop all services:
```bash
docker compose down
```

### 3. Build & Run Backend Standalone Image
If you already have MongoDB and Redis running externally:
```bash
# Build image
docker build -t m00-backend .

# Run container with environment file
docker run -d --name m00-backend -p 8000:8000 --env-file .env m00-backend
```

## API Endpoints
- `GET /health` — Health check status
- `POST /api/chats` — Create chat
- `GET /api/chats` — List chats
- `GET /api/chats/{id}` — Get chat history
- `POST /api/chats/{id}/stream` — SSE stream endpoint
- `POST /api/scrape` — Web scraping endpoint
- `GET /api/knowledge` — Knowledge base management
