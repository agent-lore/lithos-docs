# Self-Hosted (Bare Metal)

Running Lithos directly on a host gives you more control over resource usage, service management, and data location. Good for Raspberry Pi, VPS, or dedicated home servers.

## Prerequisites

- Python 3.11+ (`python3 --version`)
- pip or uv
- 512 MB RAM minimum (1 GB recommended)
- ~200 MB disk for the package + ~90 MB for the embedding model

## Install

=== "uv (recommended)"

    ```bash
    uv pip install lithos-mcp
    ```

=== "pip"

    ```bash
    pip install lithos-mcp
    ```

=== "pipx (isolated)"

    ```bash
    pipx install lithos-mcp
    ```

Verify:

```bash
lithos --version
```

## Run as a systemd Service

For a persistent background service on Linux:

```bash
# Create a systemd unit file
sudo tee /etc/systemd/system/lithos.service > /dev/null << 'EOF'
[Unit]
Description=Lithos MCP Knowledge Base Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=lithos
Group=lithos
WorkingDirectory=/opt/lithos
ExecStart=/usr/local/bin/lithos --data-dir /opt/lithos/data serve --transport sse --host 0.0.0.0 --port 8765
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=LITHOS_LOG_LEVEL=info

[Install]
WantedBy=multi-user.target
EOF

# Create a dedicated user
sudo useradd --system --home /opt/lithos --shell /usr/sbin/nologin lithos

# Create the data directory
sudo mkdir -p /opt/lithos/data
sudo chown -R lithos:lithos /opt/lithos

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable lithos
sudo systemctl start lithos

# Check status
sudo systemctl status lithos
sudo journalctl -u lithos -f
```

## Run as a launchd Service (macOS)

```bash
# Create a plist
cat > ~/Library/LaunchAgents/dev.getlithos.lithos.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>dev.getlithos.lithos</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/lithos</string>
        <string>--data-dir</string>
        <string>/Users/YOUR_USER/lithos-data</string>
        <string>serve</string>
        <string>--transport</string>
        <string>sse</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8765</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/lithos.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/lithos.err</string>
</dict>
</plist>
EOF

# Load the service
launchctl load ~/Library/LaunchAgents/dev.getlithos.lithos.plist
launchctl start dev.getlithos.lithos
```

## Raspberry Pi

Lithos runs well on a Raspberry Pi 4 (4 GB RAM recommended for the embedding model). The sentence-transformers model (`all-MiniLM-L6-v2`) runs on ARM CPU without modification.

```bash
# Raspberry Pi OS (64-bit) setup
sudo apt update
sudo apt install python3 python3-pip

pip3 install lithos-mcp

# Run in the background with nohup during setup
nohup lithos serve --transport sse --host 0.0.0.0 --port 8765 &

# Check it's running
curl http://localhost:8765/health
```

For a permanent install, use the systemd instructions above.

## Backup Strategy

The two directories that **must** be backed up:

| Path | Contents | Back up? |
|------|---------|:--------:|
| `data/knowledge/` | Your Markdown knowledge files | ✅ Yes |
| `data/.lithos/` | SQLite coordination DB | ✅ Yes |
| `data/.tantivy/` | Full-text index | ❌ Rebuildable |
| `data/.chroma/` | Vector embeddings | ❌ Rebuildable |
| `data/.graph/` | Graph cache | ❌ Rebuildable |

Simple cron backup:

```bash
# /etc/cron.daily/lithos-backup
#!/bin/bash
BACKUP_DIR=/backup/lithos/$(date +%Y-%m-%d)
mkdir -p "$BACKUP_DIR"
cp -r /opt/lithos/data/knowledge "$BACKUP_DIR/"
cp -r /opt/lithos/data/.lithos "$BACKUP_DIR/"
# Keep 30 days
find /backup/lithos -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
```

## Rebuilding Indices

If indices become corrupt or you move data to a new machine:

```bash
lithos --data-dir /opt/lithos/data reindex --clear
```

This rebuilds Tantivy and ChromaDB from the Markdown files. The coordination DB (`.lithos/`) is preserved.

## Upgrading

```bash
pip install --upgrade lithos-mcp
sudo systemctl restart lithos
```

Check the [Changelog](../changelog.md) before upgrading for breaking changes.

## Monitoring

Basic health monitoring with curl:

```bash
# Add to a cron job or monitoring script
HEALTH=$(curl -sf http://localhost:8765/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")
if [ "$HEALTH" != "ok" ]; then
    echo "Lithos health check failed: $HEALTH" | mail -s "Lithos alert" admin@example.com
fi
```
