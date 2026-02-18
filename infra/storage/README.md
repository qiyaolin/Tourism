# Storage Strategy (Phase 1.1 Reserved)

## Current Default

Use local disk for uploaded/static assets in development:

- base path suggestion: `backend/storage/`

## Future OSS Migration Contract

Keep business logic independent from storage provider with this interface contract:

- `save(file) -> path`
- `get(path) -> stream_or_url`
- `delete(path) -> bool`

## Migration Rule

Business code should call only the storage abstraction.
Switching from local disk to OSS should not require business-layer rewrite.

