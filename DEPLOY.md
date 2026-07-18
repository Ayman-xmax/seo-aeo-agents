# Deployment — Cloud Run

The app ships as **one container** (FastAPI backend serving the React build) that also
bundles **headless Chromium** (for `run_lighthouse`), **git** (for repo editing), and
**Node** (for Lighthouse). Those needs are why it runs on Cloud Run/a container, not
pure serverless.

## Local build & run
```bash
docker build -t seo-agent .
docker run -p 8080:8080 --env-file app/.env seo-agent
# open http://localhost:8080  (UI + API in one container)
```

## Deploy manually (one-off)
```bash
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/seo-agent/app:latest
gcloud run deploy seo-agent \
  --image REGION-docker.pkg.dev/PROJECT/seo-agent/app:latest \
  --region REGION --allow-unauthenticated \
  --memory 2Gi --cpu 2 --concurrency 4 --timeout 900 \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-env-vars SEO_LLM_PROVIDER=openai,SEO_WORKER_MODEL=openai/gpt-4o-mini
```

## CI/CD (GitHub Actions)
- **`.github/workflows/ci.yml`** (every push/PR): ruff lint, agent-tree import smoke,
  **eval self-check** (offline grading logic), frontend build. An optional **eval-gate**
  job runs the live model eval and fails on quality regression — only if `OPENAI_API_KEY`
  is set as a repo secret.
- **`.github/workflows/deploy.yml`** (push to `main`): builds the image via Cloud Build,
  pushes to Artifact Registry, deploys to Cloud Run. Runs only when enabled (below).

### Enable auto-deploy
1. Put the model key in **Secret Manager**:
   ```bash
   echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-
   ```
2. Set up **Workload Identity Federation** (keyless GitHub→GCP auth) and grant the service
   account `run.admin`, `cloudbuild.builds.editor`, `artifactregistry.writer`,
   `iam.serviceAccountUser`, `secretmanager.secretAccessor`.
3. Add repo **secrets**: `GCP_PROJECT`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_SA_EMAIL`
   (+ `OPENAI_API_KEY` for the eval gate).
4. Add repo **variable** `DEPLOY_ENABLED = true` to turn the deploy job on.

## Runtime notes / honest caveats
- **Resources:** Chromium needs headroom — 2 GiB / 2 vCPU is the sane floor. A full
  Phase-1 (crawl + Lighthouse per page) can take minutes, so `--timeout 900` and low
  `--concurrency`.
- **Ephemeral disk:** the owned SEO index (`seo_index.db`), cloned repos, and the RAG
  vector store live on the container's writable-but-ephemeral disk — they reset on new
  instances. Fine for a prototype; for persistence, mount GCS/Cloud SQL or a volume, and
  run `ingest` at build time to bake in the RAG index.
- **Cost:** `min-instances 0` scales to zero — you pay only per request.
