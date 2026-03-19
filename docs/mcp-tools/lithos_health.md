# lithos_health

Get the health status of the Lithos server and its backends.

<div class="tool-sig">lithos_health()</div>

No parameters.

---

## Returns

```json
{
  "status": "ok",
  "backends": {
    "tantivy": "ok",
    "chroma": "ok",
    "graph": "ok",
    "coordination": "ok"
  },
  "version": "0.1.4"
}
```

If any backend is unavailable:

```json
{
  "status": "degraded",
  "backends": {
    "tantivy": "ok",
    "chroma": "error: unable to connect",
    "graph": "ok",
    "coordination": "ok"
  },
  "version": "0.1.4"
}
```

---

## Examples

### Health check on startup

```python
health = lithos_health()
if health["status"] != "ok":
    print(f"⚠️  Lithos is degraded: {health['backends']}")
else:
    print("✅ Lithos is healthy")
```

### HTTP health check (without MCP)

Lithos also exposes an HTTP endpoint for infrastructure monitoring:

```bash
curl http://localhost:8765/health
```

---

## Notes

- Use `lithos_stats` for knowledge base statistics (document count, agents, tasks).
- A `"degraded"` status means one or more search backends are unavailable. Knowledge writes and reads may still work if only the search index is affected.
