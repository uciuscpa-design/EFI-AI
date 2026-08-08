# EFI-AI Operator UI

The first operator UI is a dependency-free static dashboard. It is intentionally small and communicates with the FastAPI service over `/health` and `/v1/strategy/signal`.

For local development, serve this directory with any static file server and proxy API requests to the FastAPI application, or mount it behind the same reverse proxy in deployment.
