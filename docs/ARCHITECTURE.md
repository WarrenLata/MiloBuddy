# Architecture

High-level architecture for Milo:

- Frontend: React (Vite) — SPA connecting to backend APIs.
- Backend: FastAPI — REST endpoints, background workers for heavy tasks.
- Infra: Cloud Run for services, Cloud SQL or Firestore for persistent storage, GCS for blobs, Vertex AI for LLM if used.

Deployment pattern: use CI to build container images, push to GCR/Artifact Registry, and deploy to Cloud Run.
