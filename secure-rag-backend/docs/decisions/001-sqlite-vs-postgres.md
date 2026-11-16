# ADR-001: SQLite vs PostgreSQL for Document Metadata

**Status**: Accepted (MVP)  
**Date**: 2026-09-02

## Context

The system requires persistent storage for document metadata (owner, status, chunk count, version) and user accounts. Two options were considered.

## Decision

**V1: SQLite** via `aiosqlite` + `SQLAlchemy` (async).

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| SQLite | Zero-ops, no container, trivial setup | Single-writer, not horizontally scalable |
| PostgreSQL | Production-grade, concurrent writes, JSONB, full ACID | Requires separate container, connection pooling |
| Qdrant only | Fewer moving parts | Qdrant is optimised for vectors, not relational queries |

## Rationale

For a portfolio MVP with single-instance deployment, SQLite provides:
- Zero additional infrastructure (no Postgres container)
- Full ACID compliance for single-writer workloads
- A clean ORM interface (SQLAlchemy) that is **database-agnostic**

The code is architected so that migrating to PostgreSQL requires only:
1. Changing `DATABASE_URL` in `.env` to `postgresql+asyncpg://...`
2. Running `alembic upgrade head`

No application code changes are required.

## Migration Path

```
V1: sqlite+aiosqlite:///./data/users.db    (current)
V2: postgresql+asyncpg://user:pw@host/db   (production)
```
