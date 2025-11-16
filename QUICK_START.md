# MedTainer MCP - Quick Start Guide

## What Just Happened?

You now have a complete DigitalOcean API integration for the MedTainer MCP server, allowing you to deploy and manage your infrastructure programmatically.

## Files Created

### 1. DigitalOcean API Client
**Location:** `app/mcp/ecosystems/digitalocean/client.py`

Complete DigitalOcean API client with methods for:
- Droplet management (create, list, get, delete, power on/off, reboot)
- SSH key management
- Account information
- Region and size queries

### 2. DigitalOcean MCP Tools
**Location:** `app/mcp/ecosystems/digitalocean/tools.py`

Five MCP tools for droplet management:
- `digitalocean.list_droplets` - List all droplets
- `digitalocean.create_droplet` - Create new droplet
- `digitalocean.get_droplet` - Get droplet details
- `digitalocean.delete_droplet` - Delete droplet
- `digitalocean.reboot_droplet` - Reboot droplet

### 3. Fully Automated Deployment Script
**Location:** `deploy_automated.py`

Programmatic deployment script that:
- Creates a new DigitalOcean droplet via API
- Waits for droplet to be ready
- Installs Docker and dependencies
- Deploys the MedTainer MCP application
- Returns connection information

**Usage:**
```bash
python3 deploy_automated.py
```

### 4. Developer Access Documentation
**Location:** `DEVELOPER_ACCESS.md`

Comprehensive guide for developers on:
- Accessing the server via HTTP API
- SSH access and server management
- Using DigitalOcean tools programmatically
- Monitoring and debugging
- Updating code and deployments

---

## Deployment Options

You now have **3 ways** to deploy:

### Option 1: Fully Automated (Recommended for New Deployments)
```bash
python3 deploy_automated.py
```

This will:
- Create a new droplet automatically
- Set up everything
- Deploy the application
- Print connection info

**Best for:** First-time deployment or creating new environments

### Option 2: Manual Deployment Script
```bash
./deploy.sh
```

This will:
- Ask for droplet IP (you need to create droplet first)
- Upload and deploy code
- Restart services

**Best for:** Updating existing deployments

### Option 3: Follow Step-by-Step Guide
See `DEPLOY_NOW.md` for manual step-by-step instructions.

**Best for:** Learning the deployment process

---

## What's Configured

### Configuration Updated
- `app/core/config.py` - Added `digitalocean_api_token` setting
- `.env` - Added DigitalOcean API token
- `.env.example` - Added DigitalOcean token template

### Tool Registry Updated
- `app/mcp/ecosystems/bootstrap.py` - Added digitalocean ecosystem
- `app/api/routes.py` - Added digitalocean to enabled ecosystems

### Total Tools Available
- **GoHighLevel:** 13 tools (CRM, contacts, pipeline, intelligence)
- **GoDaddy:** 8 tools (domains, DNS, contacts)
- **DigitalOcean:** 5 tools (droplet management) ✨ NEW
- **Total:** 26 tools across 3 ecosystems

---

## Testing the DigitalOcean Tools

### 1. Start the local server (optional)
```bash
docker-compose up
```

### 2. List your droplets
```bash
curl -X POST http://localhost:8000/mcp/run/digitalocean.list_droplets
```

### 3. Get droplet details
```bash
curl -X POST http://localhost:8000/mcp/run/digitalocean.get_droplet \
  -H "Content-Type: application/json" \
  -d '{"droplet_id": YOUR_DROPLET_ID}'
```

### 4. Create a test droplet
```bash
curl -X POST http://localhost:8000/mcp/run/digitalocean.create_droplet \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-server",
    "region": "sfo3",
    "size": "s-1vcpu-1gb",
    "image": "ubuntu-22-04-x64"
  }'
```

---

## Next Steps

### For Immediate Deployment

1. **Run the automated deployment:**
   ```bash
   python3 deploy_automated.py
   ```

2. **Wait for completion** (5-10 minutes)

3. **Note the server IP** from the output

4. **Update the stdio bridge** for the business owner:
   ```bash
   nano mcp_stdio_bridge.py
   # Change SERVER_URL to http://YOUR_SERVER_IP:8000
   ```

5. **Restart Claude Desktop** and test

### For Developer Access

1. **Read the developer guide:**
   ```bash
   open DEVELOPER_ACCESS.md
   ```

2. **Access the server via API:**
   ```bash
   curl http://YOUR_SERVER_IP:8000/health
   curl http://YOUR_SERVER_IP:8000/mcp/tools
   ```

3. **SSH into the server:**
   ```bash
   ssh medtainer@YOUR_SERVER_IP
   ```

4. **View logs:**
   ```bash
   ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs -f'
   ```

---

## Architecture Overview

```
Developer's Computer
    │
    ├─→ HTTP API Access (http://SERVER_IP:8000)
    ├─→ SSH Access (ssh medtainer@SERVER_IP)
    └─→ DigitalOcean Tools (manage infrastructure via MCP)

Business Owner's Computer
    │
    └─→ Claude Desktop → stdio bridge → http://SERVER_IP:8000

DigitalOcean Droplet (SERVER_IP)
    │
    ├─→ Docker: MCP Server (port 8000)
    ├─→ Docker: PostgreSQL (port 5432)
    └─→ All 26 MCP tools available
        ├─→ GoHighLevel (13 tools)
        ├─→ GoDaddy (8 tools)
        └─→ DigitalOcean (5 tools)
```

---

## Key Features

### ✅ Completed
- DigitalOcean API client with full droplet management
- 5 DigitalOcean MCP tools
- Fully automated deployment script
- Developer access documentation
- Configuration and registry updates

### 🎯 Ready to Use
- Deploy to DigitalOcean with one command
- Manage droplets programmatically via MCP
- Access from any computer via HTTP API
- Full developer documentation

### 💡 Benefits
1. **One-time setup** - Run deployment script once, never touch business owner's computer again
2. **Programmatic management** - Use MCP tools to manage infrastructure
3. **Developer freedom** - Access from your own computer via API or SSH
4. **Cost effective** - $24/month for 4GB/2vCPU droplet
5. **Fully documented** - Complete guides for deployment and access

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| `QUICK_START.md` | This file - overview and quick reference |
| `DEVELOPER_ACCESS.md` | Complete developer guide for accessing and managing the server |
| `deploy_automated.py` | Fully automated deployment script |
| `deploy.sh` | Manual deployment script for updates |
| `DEPLOY_NOW.md` | Step-by-step manual deployment guide |
| `DEPLOYMENT.md` | Comprehensive production deployment guide |
| `QUICK_DEPLOY.md` | Fast reference checklist |
| `CLAUDE.md` | Overall project roadmap and architecture |
| `IMPLEMENTATION_GUIDE.md` | Technical implementation details |

---

## Costs

| Item | Cost |
|------|------|
| DigitalOcean Droplet (s-2vcpu-4gb) | $24/month |
| Bandwidth (2 TB included) | $0 |
| Backups (not enabled) | $0 |
| **Total** | **$24/month** |

---

## Support & Troubleshooting

### Quick Health Check
```bash
curl http://YOUR_SERVER_IP:8000/health
```

### View Recent Logs
```bash
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs mcp | tail -50'
```

### Restart Services
```bash
ssh medtainer@YOUR_SERVER_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart'
```

### Check Tool Execution History
```bash
curl http://YOUR_SERVER_IP:8000/mcp/logs?limit=20 | python3 -m json.tool
```

For more detailed troubleshooting, see `DEVELOPER_ACCESS.md`.

---

## Summary

You now have:

✅ Complete DigitalOcean API integration
✅ 5 new MCP tools for droplet management
✅ Fully automated deployment script
✅ Comprehensive developer documentation
✅ 26 total MCP tools across 3 ecosystems
✅ Ready to deploy to the cloud

**You're ready to deploy!** Run `python3 deploy_automated.py` to get started.

---

**Last Updated:** 2025-11-14
**Total MCP Tools:** 26 (GoHighLevel: 13, GoDaddy: 8, DigitalOcean: 5)
**Deployment Options:** 3 (Automated, Manual, Step-by-Step)
**Monthly Cost:** $24
