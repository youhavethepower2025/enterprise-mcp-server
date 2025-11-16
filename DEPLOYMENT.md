# MedTainer MCP Server - DigitalOcean Deployment Guide

This guide will help you deploy the MedTainer MCP server to DigitalOcean so you can access and manage it from any computer.

## Prerequisites

1. DigitalOcean account
2. Domain name (or use DigitalOcean IP)
3. SSH key for secure access
4. All API credentials (GoHighLevel, GoDaddy, etc.)

## Architecture

```
Internet
    ↓
DigitalOcean Droplet (Ubuntu 22.04)
    ↓
Nginx (HTTPS/SSL)
    ↓
MedTainer MCP Server (Docker)
    ↓
PostgreSQL (Docker)
```

## Step 1: Create DigitalOcean Droplet

### Via DigitalOcean Web Interface:

1. **Log in to DigitalOcean**
2. **Create Droplet:**
   - Image: Ubuntu 22.04 LTS
   - Plan: Basic
   - CPU: Regular (2 GB RAM / 1 vCPU) - $18/month
     - Or: 4 GB RAM / 2 vCPU - $24/month (recommended)
   - Datacenter: Choose closest to you (e.g., NYC, SFO)
   - Authentication: SSH Key (add your public key)
   - Hostname: `medtainer-mcp`

3. **Note the Droplet IP Address** (e.g., 143.198.123.45)

### Via DigitalOcean CLI (doctl):

```bash
# Install doctl
brew install doctl

# Authenticate
doctl auth init

# Create droplet
doctl compute droplet create medtainer-mcp \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --region nyc1 \
  --ssh-keys YOUR_SSH_KEY_ID
```

## Step 2: Configure DNS (Optional but Recommended)

If you have a domain (e.g., `medtainer.com`):

1. **Add A Record:**
   - Host: `mcp` (or `api`)
   - Value: Your Droplet IP
   - Result: `mcp.medtainer.com` → Droplet IP

2. **Wait for DNS propagation** (5-30 minutes)

## Step 3: Initial Server Setup

SSH into your droplet:

```bash
ssh root@YOUR_DROPLET_IP
```

### Update System

```bash
apt update && apt upgrade -y
```

### Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Start Docker
systemctl start docker
systemctl enable docker
```

### Create Application User

```bash
# Create a non-root user for running the application
adduser medtainer
usermod -aG docker medtainer
usermod -aG sudo medtainer

# Switch to the new user
su - medtainer
```

### Setup Firewall

```bash
# As root or with sudo
ufw allow OpenSSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

## Step 4: Deploy Application

### Clone or Upload Code

**Option A: Upload from local machine**

From your local machine:

```bash
# Create a tarball of the project (excluding .venv, __pycache__, etc.)
cd "/Users/johnberfelo/AI Projects/MedTainer MCP"
tar --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
    -czf medtainer-mcp.tar.gz .

# Upload to server
scp medtainer-mcp.tar.gz medtainer@YOUR_DROPLET_IP:~/

# SSH into server and extract
ssh medtainer@YOUR_DROPLET_IP
mkdir -p ~/medtainer-mcp
tar -xzf medtainer-mcp.tar.gz -C ~/medtainer-mcp
cd ~/medtainer-mcp
```

**Option B: Use Git (recommended for ongoing development)**

```bash
# On the server
cd ~
git clone https://github.com/YOUR_USERNAME/medtainer-mcp.git
cd medtainer-mcp
```

### Configure Environment Variables

```bash
cd ~/medtainer-mcp

# Copy example env file
cp .env.example .env

# Edit with your actual credentials
nano .env
```

**Required variables in `.env`:**

```bash
# Application
APP_NAME="MedTainer MCP Server"
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database (Docker will use these)
POSTGRES_USER=mcp
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE
POSTGRES_DB=medtainer
DATABASE_URL=postgresql://mcp:YOUR_SECURE_PASSWORD_HERE@postgres:5432/medtainer

# GoHighLevel
GOHIGHLEVEL_API_KEY=YOUR_GHL_API_KEY
GOHIGHLEVEL_LOCATION_ID=YOUR_GHL_LOCATION_ID

# GoDaddy
GODADDY_API_KEY=YOUR_GODADDY_API_KEY
GODADDY_API_SECRET=YOUR_GODADDY_API_SECRET

# QuickBooks (when ready)
# QUICKBOOKS_CLIENT_ID=
# QUICKBOOKS_CLIENT_SECRET=
# QUICKBOOKS_REALM_ID=

# Future APIs as you configure them...
```

**Save and secure the file:**

```bash
chmod 600 .env
```

## Step 5: Start the Application

```bash
cd ~/medtainer-mcp

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f mcp
```

## Step 6: Install and Configure Nginx

### Install Nginx

```bash
sudo apt install nginx -y
```

### Configure Nginx as Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/medtainer-mcp
```

**Basic HTTP Configuration (for testing):**

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable the site:**

```bash
sudo ln -s /etc/nginx/sites-available/medtainer-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Test HTTP Access

```bash
curl http://YOUR_DROPLET_IP/health
# Should return: {"app":"MedTainer MCP Server","environment":"production","status":"ok"}
```

## Step 7: Enable HTTPS with Let's Encrypt (Recommended)

**Only if you have a domain name:**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d mcp.medtainer.com

# Follow the prompts
# Certbot will automatically update your nginx config
```

**Auto-renewal is configured automatically by certbot.**

## Step 8: Connect from Your Computer

### Update Claude Desktop Config

On your local machine, edit:
`~/Library/Application Support/Claude/claude_desktop_config.json`

**Update the bridge script URL:**

Edit `mcp_stdio_bridge.py` line 25:

```python
# Change from
SERVER_URL = "http://localhost:8000"

# To your DigitalOcean server
SERVER_URL = "https://mcp.medtainer.com"  # or http://YOUR_DROPLET_IP:8000
```

### Test Connection

```bash
# From your local machine
curl https://mcp.medtainer.com/health
curl https://mcp.medtainer.com/mcp/tools
```

## Step 9: Secure Access

### Setup SSH Key Authentication (if not already done)

```bash
# On your local machine
ssh-copy-id medtainer@YOUR_DROPLET_IP
```

### Disable Password Authentication

```bash
# On the server
sudo nano /etc/ssh/sshd_config

# Change these lines:
PasswordAuthentication no
PermitRootLogin no

# Restart SSH
sudo systemctl restart ssh
```

### Setup API Key for MCP Server (Future Enhancement)

Currently the MCP server is open. For production, you should add authentication:

1. Add API key middleware to FastAPI
2. Require API key in headers
3. Update bridge to include API key

## Maintenance Commands

### View Logs

```bash
cd ~/medtainer-mcp

# All logs
docker-compose logs -f

# Just MCP server
docker-compose logs -f mcp

# Just database
docker-compose logs -f postgres
```

### Restart Services

```bash
cd ~/medtainer-mcp

# Restart all
docker-compose restart

# Restart just MCP server
docker-compose restart mcp
```

### Update Code

```bash
cd ~/medtainer-mcp

# Pull latest code (if using git)
git pull

# Or upload new tarball and extract

# Rebuild and restart
docker-compose build mcp
docker-compose up -d
```

### Database Backup

```bash
# Create backup
docker exec medtainer-postgres pg_dump -U mcp medtainer > backup_$(date +%Y%m%d).sql

# Restore backup
docker exec -i medtainer-postgres psql -U mcp medtainer < backup_20241112.sql
```

## Troubleshooting

### Check if services are running

```bash
docker-compose ps
```

### Check if ports are listening

```bash
sudo netstat -tulpn | grep LISTEN
```

### Test database connection

```bash
docker exec -it medtainer-postgres psql -U mcp medtainer
```

### Check nginx errors

```bash
sudo tail -f /var/log/nginx/error.log
```

### Restart everything

```bash
cd ~/medtainer-mcp
docker-compose down
docker-compose up -d
sudo systemctl restart nginx
```

## Cost Estimate

**DigitalOcean Droplet:**
- 2 GB RAM / 1 vCPU: $18/month
- 4 GB RAM / 2 vCPU: $24/month (recommended)

**Domain (optional):**
- ~$12/year (if you don't already have one)

**Total:** ~$24-30/month

## Next Steps After Deployment

1. **Test all MCP tools** work from Claude Desktop
2. **Set up monitoring** (DigitalOcean Monitoring, Uptime Robot, etc.)
3. **Configure backups** (DigitalOcean automated backups +$4.80/month)
4. **Add remaining API integrations** (QuickBooks, Google Workspace, Amazon)
5. **Implement API authentication** for production security
6. **Set up alerts** for sync failures or errors

## Support

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Check nginx: `sudo nginx -t`
3. Check firewall: `sudo ufw status`
4. Verify DNS: `dig mcp.medtainer.com`
5. Test connectivity: `curl http://YOUR_IP/health`
