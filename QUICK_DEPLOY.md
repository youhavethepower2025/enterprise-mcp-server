# Quick Deployment Checklist

Use this as a quick reference when deploying to DigitalOcean.

## Before You Start

- [ ] DigitalOcean account created
- [ ] SSH key added to DigitalOcean
- [ ] Domain name configured (optional)
- [ ] All API credentials ready (GoHighLevel, GoDaddy, etc.)

## Deployment Steps

### 1. Create Droplet (5 minutes)

```bash
# Via web interface or CLI
doctl compute droplet create medtainer-mcp \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --region nyc1 \
  --ssh-keys YOUR_SSH_KEY_ID
```

**Note the IP address:** `___.___.___.___`

### 2. Initial Server Setup (10 minutes)

```bash
# SSH into server
ssh root@YOUR_DROPLET_IP

# Run setup commands
apt update && apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
apt install docker-compose nginx certbot python3-certbot-nginx -y

# Create user
adduser medtainer
usermod -aG docker,sudo medtainer

# Setup firewall
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable

# Switch to app user
su - medtainer
```

### 3. Deploy Application (5 minutes)

**On your local machine:**

```bash
cd "/Users/johnberfelo/AI Projects/MedTainer MCP"

# Make sure .env is configured
cp .env.example .env
# Edit .env with actual credentials

# Run deployment script
./deploy.sh
```

**Enter your droplet IP when prompted**
**Choose option 1 (Initial deployment)**

### 4. Configure Nginx (5 minutes)

```bash
# SSH back to server
ssh medtainer@YOUR_DROPLET_IP

# Copy nginx config
sudo nano /etc/nginx/sites-available/medtainer-mcp
# Paste content from nginx-config-example.conf
# Update server_name with your domain or IP

# Enable site
sudo ln -s /etc/nginx/sites-available/medtainer-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Test (2 minutes)

```bash
# From your local machine
curl http://YOUR_DROPLET_IP/health
curl http://YOUR_DROPLET_IP/mcp/tools
```

Expected response:
```json
{"app":"MedTainer MCP Server","environment":"production","status":"ok"}
```

### 6. Enable HTTPS (5 minutes) - Optional but Recommended

**Only if you have a domain:**

```bash
# On server
ssh medtainer@YOUR_DROPLET_IP
sudo certbot --nginx -d mcp.medtainer.com
```

### 7. Connect Claude Desktop (2 minutes)

Edit your local `mcp_stdio_bridge.py` line 25:

```python
SERVER_URL = "https://mcp.medtainer.com"  # or http://YOUR_DROPLET_IP:8000
```

Restart Claude Desktop and test!

## Total Time: ~30-40 minutes

## Common Issues

### Can't connect to server
```bash
# Check if server is running
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml ps'

# Check firewall
ssh medtainer@YOUR_DROPLET_IP 'sudo ufw status'
```

### Database connection errors
```bash
# Check database logs
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs postgres'

# Restart database
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart postgres'
```

### Tools not working
```bash
# Check MCP server logs
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs mcp | tail -50'

# Verify environment variables
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && cat .env | grep -v PASSWORD'
```

## Updating Code

When you make changes locally:

```bash
cd "/Users/johnberfelo/AI Projects/MedTainer MCP"
./deploy.sh
# Choose option 2 (Update deployment)
```

## Backup Database

```bash
# SSH to server
ssh medtainer@YOUR_DROPLET_IP

# Create backup
docker exec medtainer-postgres pg_dump -U mcp medtainer > ~/backup_$(date +%Y%m%d).sql

# Download to local machine (from your computer)
scp medtainer@YOUR_DROPLET_IP:~/backup_*.sql ~/backups/
```

## Monitoring

Set up monitoring at: https://cloud.digitalocean.com/monitoring

Enable alerts for:
- CPU usage > 80%
- Memory usage > 90%
- Disk usage > 80%

## Cost

- Droplet (4GB RAM): $24/month
- Backups (optional): $4.80/month
- **Total: ~$24-29/month**

---

**You're now running a production MCP server!** 🎉

Access it from anywhere, develop from your own computer, and let the business owner use it via Claude Desktop.
