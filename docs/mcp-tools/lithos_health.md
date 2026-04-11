# Health Endpoint

Check the health status of the Lithos server and its backends.

!!! info "Not an MCP tool"
    As of v0.1.5, `health` is a plain **HTTP endpoint**, not an MCP tool. Use `GET /health` directly via `curl` or any HTTP client. This makes it easy to use with Docker `HEALTHCHECK`, load balancers, and monitoring systems — no MCP client required.

---

## Endpoint

```
GET /health
```

**Response codes:**

| Code | Meaning |
|------|---------|
| `200 OK` | All components healthy |
| `503 Service Unavailable` | One or more components are degraded |

---

## Response Body

```json
{
  "status": "ok",
  "backends": {
    "tantivy": "ok",
    "chroma": "ok",
    "graph": "ok",
    "coordination": "ok"
  },
  "version": "0.1.8"
}
```

When degraded:

```json
{
  "status": "degraded",
  "backends": {
    "tantivy": "ok",
    "chroma": "error: unable to connect",
    "graph": "ok",
    "coordination": "ok"
  },
  "version": "0.1.8"
}
```

---

## Examples

### Shell / curl

```bash
# Basic liveness check
curl http://localhost:8765/health

# Check with exit code (useful in scripts)
curl -sf http://localhost:8765/health | python3 -c \
  "import sys, json; d=json.load(sys.stdin); sys.exit(0 if d['status']=='ok' else 1)"
```

### Docker HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -sf http://localhost:8765/health || exit 1
```

### Docker Compose

```yaml
healthcheck:
  test: ["CMD", "curl", "-sf", "http://localhost:8765/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 15s
```

### Python (httpx / requests)

```python
import httpx

response = httpx.get("http://localhost:8765/health")
if response.status_code != 200:
    health = response.json()
    print(f"⚠️  Lithos is degraded: {health['backends']}")
else:
    print("✅ Lithos is healthy")
```

---

## Notes

- Use [`lithos_stats`](index.md) (MCP tool) for knowledge base statistics — document counts, agent activity, task totals.
- A `"degraded"` status means one or more search backends are unavailable. Knowledge writes and reads may still work if only the search index is affected.
- The `/health` endpoint is always available, even when the MCP server is fully loaded, making it reliable for infrastructure monitoring.
