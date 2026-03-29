Milo — repo scaffold

This repository contains a starter scaffold for the Milo mobile/web app.

Structure

milo/
├── frontend/              # React (Vite)
├── backend/               # FastAPI (Python)
├── infra/                 # Terraform or GCP config
├── docs/                  # Product & architecture
├── .github/
│   └── workflows/         # CI/CD to GCP Cloud Run
├── docker-compose.yml     # Local dev compose
└── README.md

How to use

- Backend: `cd backend` — see `requirements.txt` and `Dockerfile`.
- Frontend: `cd frontend` — Vite React starter.
- CI/CD: See `.github/workflows/ci-cd.yml` for a template to deploy to Cloud Run.

Notes

- Replace placeholder values in workflows with your GCP project, region and service account secret.
- This is a minimal scaffold to get started; expand services and tests as needed.
