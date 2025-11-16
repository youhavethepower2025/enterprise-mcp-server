# Developer Access Guide

This guide shows you how to access and work with the MedTainer MCP server from your own computer after it's been deployed to DigitalOcean.

## Quick Start

After deployment, you'll have received the server IP address. Let's call it `YOUR_SERVER_IP`.

### 1. Access via HTTP API

The simplest way to interact with the server is through HTTP requests:

```bash
# Health check
curl http://YOUR_SERVER_IP:8000/health

# List all available tools
curl http://YOUR_SERVER_IP:8000/mcp/tools | python3 -m json.tool

# Run a specific tool
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/gohighlevel.read_contacts \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

### 2. SSH Access

You can SSH into the server for debugging and management:

```bash
# SSH as medtainer user (recommended)
ssh medtainer@YOUR_SERVER_IP

# SSH as root (if needed)
ssh root@YOUR_SERVER_IP
```

### 3. Use Your Own MCP Client

If you're building your own MCP client or want to integrate with your own tools:

**Python Example:**
```python
import httpx

SERVER_URL = "http://YOUR_SERVER_IP:8000"

# List tools
response = httpx.get(f"{SERVER_URL}/mcp/tools")
tools = response.json()
print(f"Available tools: {tools['count']}")

# Run a tool
response = httpx.post(
    f"{SERVER_URL}/mcp/run/gohighlevel.read_contacts",
    json={"limit": 10}
)
result = response.json()
print(result)
```

**JavaScript/Node.js Example:**
```javascript
const SERVER_URL = "http://YOUR_SERVER_IP:8000";

// List tools
fetch(`${SERVER_URL}/mcp/tools`)
  .then(res => res.json())
  .then(data => console.log(`Available tools: ${data.count}`));

// Run a tool
fetch(`${SERVER_URL}/mcp/run/gohighlevel.read_contacts`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ limit: 10 })
})
  .then(res => res.json())
  .then(result => console.log(result));
```

---

## DigitalOcean MCP Tools

The server now includes 5 DigitalOcean management tools that you can use programmatically:

### 1. List Droplets
```bash
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.list_droplets
```

Returns all droplets with their IPs, status, and configuration.

### 2. Get Droplet Details
```bash
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.get_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": 123456789}'
```

Returns detailed information about a specific droplet.

### 3. Create Droplet
```bash
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.create_droplet \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-server",
    "region": "sfo3",
    "size": "s-1vcpu-1gb",
    "image": "ubuntu-22-04-x64",
    "tags": ["test"]
  }'
```

Creates a new droplet. Useful for spinning up test environments.

### 4. Reboot Droplet
```bash
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.reboot_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": 123456789}'
```

Gracefully reboots a droplet.

### 5. Delete Droplet
```bash
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.delete_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": 123456789}'
```

**Warning:** This permanently deletes a droplet. Use with caution!

---

## Server Management

### View Logs

```bash
# SSH into server
ssh medtainer@YOUR_SERVER_IP

# View application logs
cd medtainer-mcp
docker-compose -f docker-compose.prod.yml logs -f

# View just the MCP server logs
docker-compose -f docker-compose.prod.yml logs -f mcp

# View just the database logs
docker-compose -f docker-compose.prod.yml logs -f postgres
```

### Check Container Status

```bash
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml ps'
```

### Restart Services

```bash
# Restart all services
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart'

# Restart just the MCP server
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart mcp'

# Restart just the database
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart postgres'
```

### Database Access

```bash
# Access PostgreSQL directly
ssh medtainer@YOUR_SERVER_IP 'docker exec -it medtainer-postgres psql -U mcp medtainer'

# From inside psql:
# \dt                          -- List all tables
# SELECT * FROM contacts;      -- View contacts
# SELECT * FROM tool_executions ORDER BY timestamp DESC LIMIT 10;  -- Recent tool executions
# \q                          -- Quit
```

### Update Code

When you make changes to the code on your local machine:

#### Option A: Use the automated deployment script

```bash
cd "/Users/johnberfelo/AI Projects/MedTainer MCP"
python3 deploy_automated.py
```

This will create a new droplet. If you want to update the existing droplet, use Option B.

#### Option B: Use the manual deployment script

```bash
cd "/Users/johnberfelo/AI Projects/MedTainer MCP"
./deploy.sh

# When prompted:
# - Enter droplet IP: YOUR_SERVER_IP
# - Choose: 2 (Update existing deployment)
```

#### Option C: Manual deployment

```bash
# Create tarball
cd "/Users/johnberfelo/AI Projects/MedTainer MCP"
tar --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
    --exclude='*.log' --exclude='.DS_Store' \
    -czf medtainer-mcp.tar.gz .

# Upload
scp medtainer-mcp.tar.gz medtainer@YOUR_SERVER_IP:~/

# Deploy
ssh medtainer@YOUR_SERVER_IP << 'ENDSSH'
    cd ~/medtainer-mcp
    tar -xzf ../medtainer-mcp.tar.gz
    docker-compose -f docker-compose.prod.yml up -d --build
ENDSSH
```

---

## Working from Your Own Computer

### Set Up Your Development Environment

1. **Clone or sync the repository** (if you haven't already):
   ```bash
   # If you have the code:
   cd your-local-project-directory

   # If starting fresh, you'll need the code from the business owner's computer
   ```

2. **Install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create your own .env file**:
   ```bash
   cp .env.example .env

   # Edit .env with your own credentials or point to the cloud server
   nano .env
   ```

### Option 1: Point Your Local MCP Client to the Cloud Server

Edit your local `mcp_stdio_bridge.py`:

```python
# Change this line:
SERVER_URL = "http://localhost:8000"

# To this:
SERVER_URL = "http://YOUR_SERVER_IP:8000"
```

Now when you use Claude Desktop on your computer, it will connect to the cloud server instead of localhost.

### Option 2: Run Your Own Local Development Server

```bash
# Run locally for development
docker-compose up

# Your local server runs on http://localhost:8000
# The cloud server runs on http://YOUR_SERVER_IP:8000
```

This is useful for testing changes before deploying to production.

### Option 3: Use the DigitalOcean Tools Directly

You can use the MCP server's DigitalOcean tools to manage the infrastructure programmatically:

```bash
# List all droplets (including the MedTainer MCP server)
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.list_droplets

# Check the server's own status
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.get_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": YOUR_DROPLET_ID}'

# Reboot the server remotely
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.reboot_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": YOUR_DROPLET_ID}'
```

---

## API Endpoints Reference

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp/tools` | GET | List all available tools |
| `/mcp/logs` | GET | View recent tool execution logs |

### Tool Execution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/run/{tool_name}` | POST | Execute a specific tool |

### Resources & Context (for AI agents)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/resources` | GET | List available context resources |
| `/mcp/resources/read?uri={uri}` | GET | Read a specific resource |
| `/mcp/prompts` | GET | List available guided prompts |
| `/mcp/prompts/get` | POST | Get a specific prompt |

### GoHighLevel Sync

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gohighlevel/sync` | POST | Manually trigger contact sync |
| `/gohighlevel/sync/status` | GET | Get sync status and history |

### GoDaddy Sync

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/godaddy/sync` | POST | Manually trigger domain sync |
| `/godaddy/sync/status` | GET | Get sync status and history |
| `/godaddy/domains/summary` | GET | Get domain statistics |

---

## Available Tools by Ecosystem

### GoHighLevel (13 tools)
- `gohighlevel.read_contacts` - List contacts
- `gohighlevel.read_pipeline` - View pipeline stages
- `gohighlevel.get_insights` - Get intelligence insights
- `gohighlevel.analyze_contact` - Analyze specific contact
- `gohighlevel.create_contact` - Create new contact
- `gohighlevel.update_contact` - Update existing contact
- `gohighlevel.send_sms` - Send SMS message
- `gohighlevel.add_note` - Add note to contact
- `gohighlevel.add_tags` - Add tags to contact
- `gohighlevel.remove_tags` - Remove tags from contact
- Plus 3 more...

### GoDaddy (8 tools)
- `godaddy.list_domains` - List all domains
- `godaddy.get_domain` - Get domain details
- `godaddy.list_dns_records` - List DNS records
- `godaddy.get_domain_contacts` - Get domain contact info
- Plus 4 more...

### DigitalOcean (5 tools)
- `digitalocean.list_droplets` - List all droplets
- `digitalocean.create_droplet` - Create new droplet
- `digitalocean.get_droplet` - Get droplet details
- `digitalocean.delete_droplet` - Delete droplet
- `digitalocean.reboot_droplet` - Reboot droplet

---

## Monitoring & Debugging

### Check API Health

```bash
# Simple health check
curl http://YOUR_SERVER_IP:8000/health

# Get tool execution statistics
curl http://YOUR_SERVER_IP:8000/mcp/logs?limit=50 | python3 -m json.tool

# Filter logs by specific tool
curl "http://YOUR_SERVER_IP:8000/mcp/logs?tool_name=gohighlevel.read_contacts&limit=20" | python3 -m json.tool
```

### Monitor Resource Usage

```bash
# SSH into server
ssh medtainer@YOUR_SERVER_IP

# Check disk usage
df -h

# Check memory usage
free -h

# Check Docker container stats
docker stats

# Check running processes
top
```

### View Database Statistics

```bash
ssh medtainer@YOUR_SERVER_IP << 'ENDSSH'
docker exec medtainer-postgres psql -U mcp medtainer -c "
SELECT
    tool_name,
    COUNT(*) as executions,
    AVG(duration_ms) as avg_duration_ms,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as errors
FROM tool_executions
GROUP BY tool_name
ORDER BY executions DESC
LIMIT 10;
"
ENDSSH
```

---

## Security Considerations

### SSH Key Setup (Recommended)

For better security, set up SSH key authentication:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy your public key to the server
ssh-copy-id medtainer@YOUR_SERVER_IP

# Now you can SSH without password
ssh medtainer@YOUR_SERVER_IP
```

### Firewall Configuration

The server is currently open on port 8000. For production, you should:

1. **Add firewall rules** to restrict access
2. **Use HTTPS** with SSL certificates
3. **Add authentication** to the API endpoints

See `DEPLOYMENT.md` for production hardening steps.

### API Token Security

- Never commit `.env` file to git
- Rotate API tokens regularly
- Use separate tokens for development and production

---

## Troubleshooting

### Server Not Responding

```bash
# Check if server is running
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml ps'

# Restart if needed
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart'

# Check logs for errors
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs mcp | tail -100'
```

### Database Connection Issues

```bash
# Check database is running
ssh medtainer@YOUR_SERVER_IP 'docker exec medtainer-postgres pg_isready -U mcp'

# Restart database
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart postgres'

# Check database logs
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs postgres | tail -100'
```

### Tool Execution Failures

```bash
# Check recent execution logs
curl "http://YOUR_SERVER_IP:8000/mcp/logs?limit=20" | python3 -m json.tool

# Check specific tool
curl "http://YOUR_SERVER_IP:8000/mcp/logs?tool_name=gohighlevel.read_contacts&limit=10" | python3 -m json.tool

# Test tool directly
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/gohighlevel.read_contacts \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}' | python3 -m json.tool
```

### Out of Memory

```bash
# Check memory usage
ssh medtainer@YOUR_SERVER_IP 'free -h'

# If memory is low, upgrade droplet size:
# Use the DigitalOcean dashboard or API to resize
# Or use the digitalocean tools:
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.get_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": YOUR_DROPLET_ID}'
```

---

## Cost Management

### Current Monthly Cost

- **Basic Droplet** (s-2vcpu-4gb): $24/month
- **Bandwidth**: 2 TB included (sufficient for most use cases)
- **Backups**: $0 (not enabled)

### Optimization Tips

1. **Downgrade if possible**: If traffic is low, you can resize to s-1vcpu-2gb ($18/month)
2. **Use snapshots instead of backups**: Snapshots are cheaper ($0.05/GB/month)
3. **Monitor bandwidth**: If you exceed 2TB, you'll pay $0.01/GB

### Resize Droplet

```bash
# Get current droplet info
curl -X POST http://YOUR_SERVER_IP:8000/mcp/run/digitalocean.get_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": YOUR_DROPLET_ID}'

# To resize, use DigitalOcean dashboard or API
# (Resize tool not implemented in MCP yet)
```

---

## Next Steps

1. **Test the server** from your own computer
2. **Set up monitoring** (see `DEPLOYMENT.md` for Grafana/Prometheus setup)
3. **Enable HTTPS** with Let's Encrypt (see `DEPLOYMENT.md`)
4. **Add authentication** to API endpoints (see `DEPLOYMENT.md`)
5. **Set up automated backups** (see `DEPLOYMENT.md`)
6. **Implement CI/CD** for automated deployments

---

## Getting Help

### Check Logs
```bash
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs -f'
```

### Check Tool Execution History
```bash
curl http://YOUR_SERVER_IP:8000/mcp/logs?limit=50 | python3 -m json.tool
```

### Access Database
```bash
ssh medtainer@YOUR_SERVER_IP 'docker exec -it medtainer-postgres psql -U mcp medtainer'
```

### Emergency Restart
```bash
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml up -d'
```

---

**Last Updated:** 2025-11-14
**Server Version:** 0.1.0
**Deployment Type:** Production (DigitalOcean)
