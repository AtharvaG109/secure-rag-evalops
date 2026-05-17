# Security Policy

## Supported versions

Security reports are accepted for the current `main` branch.

## Reporting a vulnerability

Please do not open public issues for suspected vulnerabilities. Report them privately to the repository owner with:

- a clear description of the issue
- reproduction steps
- the affected endpoint or component
- any recommended mitigation

## Security posture

- Production mode requires bearer API keys and rejects insecure runtime settings.
- Namespace authorization runs before retrieval.
- Bulk deletion is preview-first and audit-logged.
- Raw source files are not stored after ingestion.
- Local development conveniences such as `demo-admin` are disabled outside local mode.
