# Deploy to DigitalOcean NOW - One Time Setup

This is a one-time deployment from the business owner's computer. After this, you (the developer) will work from your own machine.

## What's Happening

1. **Deploy from this computer** (business owner's Mac) → DigitalOcean
2. **Business owner** continues using Claude Desktop → Cloud server
3. **Developer** (you) works from own computer → Cloud server

After deployment, you'll never need this Mac again.

## Step 1: Create DigitalOcean Droplet (Do This First)

### Via DigitalOcean Website:

1. Go to: https://cloud.digitalocean.com/droplets/new
2. **Image:** Ubuntu 22.04 LTS
3. **Plan:** Basic Shared CPU
4. **CPU:** Regular - 4 GB / 2 vCPU - $24/month
5. **Region:** San Francisco 3 (or closest to business owner)
6. **Authentication:** Password (for now, easier for one-time setup)
   - Choose a strong password and save it
7. **Hostname:** `medtainer-mcp`
8. **Click Create Droplet**

**WRITE DOWN THE IP ADDRESS:** `___.___.___.___ `

## Step 2: Initial Server Setup (5 minutes)

Open Terminal and run these commands:

```bash
# SSH into the server (use the password you set)
ssh root@YOUR_DROPLET_IP

# When prompted, say "yes" to continue connecting
# Enter the password you set

# Copy and paste this entire block:
apt update && apt upgrade -y && \
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && \
apt install docker-compose -y && \
systemctl start docker && systemctl enable docker && \
adduser --disabled-password --gecos "" medtainer && \
usermod -aG docker medtainer && \
usermod -aG sudo medtainer && \
mkdir -p /home/medtainer && \
chown medtainer:medtainer /home/medtainer

# This will take 2-3 minutes. Wait for it to complete.

# When done, exit
exit
```

## Step 3: Deploy the Application (2 minutes)

```bash
# Go to the project directory
cd "/Users/johnberfelo/AI Projects/MedTainer MCP"

# Make sure .env exists and has real credentials
# If not, copy from example and edit:
# cp .env.example .env
# nano .env  # Add real API keys

# Run the deployment
./deploy.sh
```

**When prompted:**
- Enter droplet IP: `YOUR_DROPLET_IP`
- Choose: `1` (Initial deployment)

The script will:
- Package everything
- Upload to DigitalOcean
- Start the server

**Wait 2-3 minutes for completion.**

## Step 4: Test It (30 seconds)

```bash
# Test the health endpoint
curl http://YOUR_DROPLET_IP:8000/health

# Should return:
# {"app":"MedTainer MCP Server","environment":"production","status":"ok"}

# Test the tools endpoint
curl http://YOUR_DROPLET_IP:8000/mcp/tools | python3 -m json.tool | head -20
```

If you see JSON output, **it's working!**

## Step 5: Update Business Owner's Claude Desktop (1 minute)

Edit the bridge script to point to the cloud server:

```bash
nano "/Users/johnberfelo/AI Projects/MedTainer MCP/mcp_stdio_bridge.py"
```

**Change line 25 from:**
```python
SERVER_URL = "http://localhost:8000"
```

**To:**
```python
SERVER_URL = "http://YOUR_DROPLET_IP:8000"  # Use actual IP
```

**Save:** `Ctrl+O`, `Enter`, `Ctrl+X`

Restart Claude Desktop and test!

## Step 6: Send Info to Developer (YOU)

Create a file with connection details:

```bash
cat > ~/Desktop/MCP_SERVER_INFO.txt << EOF
MedTainer MCP Server Deployed

Server IP: YOUR_DROPLET_IP
Server URL: http://YOUR_DROPLET_IP:8000

API Endpoints:
- Health: http://YOUR_DROPLET_IP:8000/health
- Tools: http://YOUR_DROPLET_IP:8000/mcp/tools
- Run tool: http://YOUR_DROPLET_IP:8000/mcp/run/{tool_name}

SSH Access:
- User: medtainer
- Command: ssh medtainer@YOUR_DROPLET_IP

Root SSH (if needed):
- User: root
- Command: ssh root@YOUR_DROPLET_IP

Database:
- Running in Docker
- Access: ssh medtainer@YOUR_DROPLET_IP 'docker exec -it medtainer-postgres psql -U mcp medtainer'

Logs:
- View: ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs -f'

To update code:
1. Make changes on your local computer
2. Run: ./deploy.sh
3. Choose option 2 (Update)

Cost: $24/month
EOF
```

**Email this file to yourself** or save it somewhere you can access from your own computer.

## ✅ Done!

You're finished with this computer. Everything is now running in the cloud.

### What Happens Next:

1. **Business Owner:**
   - Uses Claude Desktop on this Mac
   - Connects to: `http://YOUR_DROPLET_IP:8000`
   - All 21 MCP tools work
   - Intelligence, sync, actions all work

2. **You (Developer):**
   - Work from your own computer
   - Access same server at: `http://YOUR_DROPLET_IP:8000`
   - Make changes, deploy with `./deploy.sh`
   - Use your own MCP tools to access the server
   - Full admin access via SSH

## Troubleshooting

### Server not responding?
```bash
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml ps'
```

### Restart everything:
```bash
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart'
```

### View logs:
```bash
ssh medtainer@YOUR_DROPLET_IP 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs -f mcp | tail -50'
```

---

**Total Time:** 10 minutes
**Cost:** $24/month
**You're Done!** 🎉

Never touch this computer again. Work from your own machine from now on.
