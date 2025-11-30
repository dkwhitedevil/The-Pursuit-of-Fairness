# Deploying The Pursuit of Fairness (Public)

This document walks through publishing the app publicly using GitHub, Vercel (frontend), and Render (backend). It assumes you have an account on each provider.

1) Create a GitHub repository and push
-------------------------------
- Create a repository on GitHub (private or public).
- Add the remote and push:

```cmd
cd C:\Projects\The-Pursuit-of-Fairness
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

2) Frontend — Deploy to Vercel
-------------------------------
- Go to https://vercel.com and sign in with GitHub.
- Click "New Project" -> Import Git Repository -> select your repo.
- When asked, set the Project Root to `frontend`.
- Ensure the Framework is detected as Next.js. Build & Output settings are usually automatic.
- Add environment variables (if frontend needs any) in Project Settings.
- Deploy. Vercel will provide a public URL and automatic HTTPS.

CLI alternative:

```cmd
cd C:\Projects\The-Pursuit-of-Fairness\frontend
npm i -g vercel
vercel login
vercel --prod
```

3) Backend — Deploy to Render (Docker)
-------------------------------------
- Render can deploy the backend using the repository and the `backend/Dockerfile` already present.
- Go to https://dashboard.render.com -> New -> Web Service -> Connect GitHub -> select repo.
- When configuring the service:
  - Set the Root to `/` or `backend` and point `Dockerfile` path to `backend/Dockerfile` (this repo includes one).
  - Set environment variables (see below).
  - Choose free plan if acceptable.
- Deploy. Render will build the Docker image and provide a public HTTPS URL for the backend.

4) Environment variables / Secrets
---------------------------------
- Do NOT commit `.env` or API keys. Add these to Vercel/Render in project settings / secrets.
- Minimum suggested variables:
  - `OPENAI_API_KEY` — for LLM explanations (optional but recommended).
  - `FRONTEND_URL` — set to your frontend URL (Vercel) to allow CORS.

5) Optional: Domain, TLS, DNS
-----------------------------
- Add a custom domain in Vercel (Frontend) and Render (Backend) if you own one.
- Update DNS records (CNAME or A) as instructed by each provider; TLS is automatic with both.

6) CI / Tests
---------------
- This repo includes a GitHub Actions workflow at `.github/workflows/ci.yml` which:
  - Builds the frontend
  - Installs backend dependencies and runs `pytest` (if tests exist)

7) Troubleshooting
--------------------
- If the LLM explainer returns fallback text, ensure `OPENAI_API_KEY` is set and valid.
- For CORS issues, confirm `FRONTEND_URL` is present in `backend/main.py` CORS middleware or set to `*` for testing (not recommended for production).

8) Next steps / automation
---------------------------
- To automate deployments from CI, use provider-specific GitHub Apps (Vercel/Render auto-deploy on push) or set up GitHub Actions with provider CLI and secrets.

If you want, I can:
- Create a `vercel.json` or `render.yaml` for zero-config deploys (I added `render.yaml` already).
- Configure an Action to auto-deploy to Render using `render-cli` (requires Render API key).
- Push these changes to GitHub for you if you grant a remote or run the `git` commands above.
