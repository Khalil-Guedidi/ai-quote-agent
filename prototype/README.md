# Prototype: n8n + Odoo Community Environment

Local Docker environment for validating the n8n ↔ Odoo integration prototype.

## Prerequisites

- Docker and Docker Compose (v2+)
- curl, python3 (for verification script)

## Quick Start

```bash
# 1. Copy and configure environment variables
cp .env.example .env

# 2. Start all services
docker compose up -d

# 3. Wait for initialization (Odoo first boot takes 2-3 minutes)
docker compose logs -f odoo   # Watch for "HTTP service (werkzeug) running"

# 4. Verify everything is working
./scripts/verify-setup.sh
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Odoo 18 Community | http://localhost:8069 | ERP with demo data (login: admin / admin) |
| n8n | http://localhost:5678 | Workflow automation |
| PostgreSQL 16 | localhost:5432 | Odoo database backend |

## n8n ↔ Odoo Connection

The connection uses **HTTP Request nodes** with JSON-RPC (not the built-in Odoo node) for reliability.

### Test Workflow

Import `n8n-workflows/test-odoo-connection.json` into n8n to test the connection:

1. Open n8n at http://localhost:5678
2. Go to Workflows → Import from File
3. Select `n8n-workflows/test-odoo-connection.json`
4. Execute the workflow — it should authenticate and list products

### JSON-RPC Connection Details

- **Endpoint**: `http://odoo:8069/jsonrpc` (from within Docker network)
- **Authentication**: POST to `http://odoo:8069/web/session/authenticate`
- **Database**: `odoo_db`
- **Credentials**: admin / admin

## Useful Commands

```bash
# View logs
docker compose logs -f

# Stop services
docker compose down

# Stop and remove volumes (full reset)
docker compose down -v

# Restart a specific service
docker compose restart odoo
```

## Troubleshooting

- **Odoo not loading**: First boot takes 2-3 minutes for DB initialization. Check `docker compose logs odoo`.
- **n8n can't reach Odoo**: Both must be on the `proto-net` network. Check with `docker network inspect proto-net`.
- **Products not found**: Ensure Odoo initialized with demo data. The entrypoint script handles this automatically on first boot.
