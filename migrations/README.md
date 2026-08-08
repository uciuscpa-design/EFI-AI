# Database migrations

This directory is reserved for Alembic migrations. The initial API uses an in-process audit sink; durable persistence is intentionally a separate migration step so the storage contract can be finalized before production data is written.
