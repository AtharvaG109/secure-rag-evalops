# Production Guide

## Intended deployment

SecureRAG EvalOps is hardened for a private internal deployment: authenticated users, namespace-scoped access, admin-only metrics, explicit audit records for destructive actions, and local model endpoints managed inside a trusted network.

## Before first deploy

1. Copy `.env.production.example` to `.env.production`.
2. Replace every placeholder, especially:
   - `DATABASE_URL`
   - `POSTGRES_PASSWORD`
   - `QDRANT_API_KEY`
   - `AUTH_TOKEN_PEPPER`
   - `TRUSTED_HOSTS`
   - local model names and dimensions
3. Keep `ALLOW_LOCAL_DEV_AUTH=false`.
4. Keep `RUN_MIGRATIONS_ON_STARTUP=false`; run migrations as a release step.

## Deploy

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
docker compose -f docker-compose.production.yml --env-file .env.production exec app alembic upgrade head
docker compose -f docker-compose.production.yml --env-file .env.production exec app \
  python scripts/create_api_key.py create \
  admin admin@example.com "Admin User" security-policy --permission admin --superuser
```

Store the emitted API key in a secret manager. It is shown once and only the keyed hash is stored.

## Health and operations

- `GET /health/live` proves the process is up.
- `GET /health/ready` checks Postgres, Redis, and Qdrant.
- `GET /api/v1/auth/me` verifies the API key identity.
- `GET /api/v1/audit/events` is superuser-only and exposes destructive-action audit history.

## Backups

- Back up Postgres and Qdrant volumes together.
- Test restore procedures before handling real documents.
- Retain `.env.production` only in a secret-management system, not in Git.

## Security posture

- Production startup rejects insecure settings such as wildcard trusted hosts, disabled rate limiting, local auth bypass, or the development token pepper.
- API identity is derived from bearer API keys, not caller-supplied `user_id` values.
- Bulk deletion is preview-first and requires explicit confirmation.
- The browser UI can accept an API token for internal use, but deployments should still sit behind HTTPS and an authenticated reverse proxy.
