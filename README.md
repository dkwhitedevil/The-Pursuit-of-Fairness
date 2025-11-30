# The Pursuit of Fairness

![Walrus Haulout Hackathon 2025](https://img.shields.io/badge/Walrus%20Haulout-2025-blue)

**Made for the Walrus Haulout Hackathon 2025 — Provably Authentic (Truth Engine + Trust Oracle) track.**

Built for the Walrus Haulout Hackathon 2025 — Provably Authentic (Truth Engine + Trust Oracle) track.

Comprehensive toolkit for dataset fairness auditing, explanation, proof anchoring (Sui), and secure upload. This repository contains a Next.js frontend, a FastAPI backend, Move modules (in `move_modules/`), and tooling for interacting with Walrus and Sui.

This README documents how to run the project locally, how the pieces fit together, and how to publish the app publicly (frontend -> Vercel, backend -> Render or similar). It also covers Docker usage, Ollama integration, and security best-practices.

Hackathon context — Provably Authentic
------------------------------------
This project was developed as an entry for the Walrus Haulout Hackathon 2025 under the "Provably Authentic (Truth Engine + Trust Oracle)" track.

Under this track we focus on authenticity on-chain: verifying provenance of media, creating prediction markets for truth, and designing AI trust oracles that can prove source, training data provenance, or model reliability. The project explores systems that turn data into value — combining decentralized storage (Walrus), tamper-evident anchoring (Sui), and explainable fairness audits.

Key goals for the track:
- Verify provenance of media and datasets and anchor proofs on-chain.
- Build prediction markets or incentives that reward accurate reporting and oracle reliability.
- Create AI trust oracles that produce auditable explanations about models and datasets.
- Integrate storage, verification, and economic incentives to align truth and provenance.


Contents
- Architecture overview
- Quick start (local)
- Frontend (Next.js) — dev & deploy
- Backend (FastAPI) — dev, Docker & deploy
- ollama integration (optional LLM host)
- move_modules (Move bytecode) — notes
- Environment variables / secrets
- CI / Deployment
- Troubleshooting & tips
- Contributing

----

## Architecture overview

- `frontend/`: Next.js (App Router) UI. Login (NextAuth), dashboard, upload flows.
- `backend/`: FastAPI server that performs fairness audits, generates explanations (OpenAI or Ollama), encrypts bundles for Walrus, and anchors proofs on Sui.
- `move_modules/`: Compiled Move bytecode and source for on-chain logic (kept separate from runtime code).
- `walrus-uploader/`: Node uploader used by backend to push encrypted bundles to Walrus storage.

## Quick start (local)

Prerequisites
- Node.js (18+), npm
- Python 3.11
- Docker (for containerized runs)
- Optionally Ollama (if you plan to run a local LLM).

1) Clone repository
```
cd C:\Projects
git clone https://github.com\dkwhitedevil\The-Pursuit-of-Fairness.git
cd The-Pursuit-of-Fairness
```

2) Backend – virtualenv, install, run
```
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Visit: http://localhost:8000/

3) Frontend – install & run
```
cd frontend
npm ci
npm run dev
```
Visit: http://localhost:3000/

4) Upload a sample CSV from the dashboard to test the full pipeline.

## Frontend details (development & Vercel deploy)

- Project root: `frontend/` (select this as the Root Directory when creating a Vercel project for this monorepo).
- Local dev:
  - `npm run dev` starts Next dev server.
  - Copy `.env.local.example` -> `.env.local` for local env vars.
- Build for production: `npm run build`.
- Vercel deploy (interactive):
```
cd frontend
npm i -g vercel
vercel login
vercel --prod
```
- When importing the repo on Vercel, choose `frontend` as the Root Directory (important for monorepos).

## Backend details (development, Docker, Render)

### 1) Local dev (venv) — see Quick start above.

### 2) Docker (recommended for deployment)

- The repository includes `backend/Dockerfile` which installs Python deps and runs Uvicorn.
- Build image locally:
```
cd C:\Projects\The-Pursuit-of-Fairness
docker build -t tpf-backend:latest -f backend/Dockerfile .
```
- Run container (pass secrets at runtime):
```
docker run --rm -p 8000:8000 -e PORT=8000 -e OPENAI_API_KEY=your_key_here tpf-backend:latest
```

### 3) Render (Docker) — easy production deploy

- Create a new Web Service on Render, connect your GitHub repo.
- Choose Docker as the environment and set Dockerfile path to `backend/Dockerfile`.
- No Build or Start command is required for Docker services — Render will build and run the container.
- Set environment variables in Render (OPENAI_API_KEY, FRONTEND_URL, etc.).

### 4) Render (without Docker) — build & start commands

- Root directory: `backend`
- Build command:
```
python -m pip install --upgrade pip && pip install -r requirements.txt
```
- Start command:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Ollama / local LLM host

You can run Ollama beside the backend for local LLM inference. For local dev a docker-compose setup is convenient:

`docker-compose.yml` (example):
```
version: "3.8"
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    environment:
      - PORT=8000
      - OLLAMA_URL=http://ollama:11434
      - FRONTEND_URL=http://localhost:3000
    ports:
      - "8000:8000"
    depends_on:
      - ollama
```

Notes:
- For production you should host Ollama on a separate host or managed instance and set `OLLAMA_URL` in the backend environment.
- The backend will prefer `OLLAMA_URL` if configured (fallback to OpenAI if not available).

## move_modules (Move bytecode) notes

- `move_modules/` contains compiled Move modules and source for `fairness_oracle` and `seal_policy`.
- These are static artifacts used for on-chain interactions; the backend does not automatically compile them at runtime. If you need to publish these Move modules to Sui, follow your standard Move/Move CLI process.

## Environment variables (important)

Common env vars (do NOT commit secrets to git):
- `OPENAI_API_KEY` — OpenAI API key for LLM explanations (optional if you use Ollama)
- `OLLAMA_URL` — URL for self-hosted Ollama (e.g., `http://ollama:11434`)
- `FRONTEND_URL` — e.g., `http://localhost:3000` or your Vercel URL
- `NEXTAUTH_SECRET` — NextAuth secret for session encryption (frontend only)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth for NextAuth

Local example files
- `frontend/.env.local.example` — example values for frontend. Copy to `.env.local` for local dev.
- `backend/.env.example` — create a local env containing keys for local Docker runs (do not commit).

## Security & best practices

- NEVER commit `.env.local`, `.env`, or secrets into the repository. Use the provider's secret store (Vercel/Render/GCP Secret Manager).
- Rotate keys if secret leaks are suspected. Remove any committed secrets from git history using BFG or `git filter-repo`.
- Protect the Ollama endpoint in production behind authentication or internal network.

## CI & Deployment

- This repository includes GitHub Actions workflows:
  - `.github/workflows/ci.yml` — builds frontend and runs backend tests on push/PR to `main`.
  - `.github/workflows/deploy-frontend-vercel.yml` — deploys the `frontend/` directory to Vercel on push to `main` (requires Vercel secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`).
- For backend auto-deploy, create a Render service (Docker) or add a GitHub Action that triggers Render via API (requires Render API key stored in GitHub Secrets).

## Testing

- Backend tests are in `backend/tests`. Run locally from project root:
```
cd backend
.venv\Scripts\activate
pytest -q
```

## Troubleshooting & tips

- If the frontend shows an empty explanation, make sure `OPENAI_API_KEY` or `OLLAMA_URL` is set in the backend and reachable.
- For CORS issues, ensure `FRONTEND_URL` is configured in `backend/main.py` CORS middleware and in provider settings.
- If Docker container fails with port issues on Render, change the Dockerfile to use `$PORT` (Render injects this env at runtime). The repo includes an updated Dockerfile variant.

## Contributing

- Create a branch, make changes, open a pull request against `main`.
- Keep secrets out of PRs. Use mock/test keys for CI when needed and rotate them regularly.

## License

Check repository root or consult the project owner for license details.

## Contact

For questions about deploying to a particular provider, attaching domains, or automating deploys, open an issue or reach out to the project maintainer.
