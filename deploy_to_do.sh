#!/bin/bash
#
# MedTainer MCP Server - Deploy to DigitalOcean
#
# This script deploys the MedTainer MCP server from your local machine
# to the DigitalOcean production server at 24.199.118.227
#
# Usage: ./deploy_to_do.sh
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 MedTainer MCP - Deploy to DigitalOcean${NC}"
echo "========================================"
echo ""

# Configuration
DO_HOST="root@24.199.118.227"
DO_PATH="/root/medtainer-mcp"
LOCAL_PATH="$(pwd)"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -f "app/main.py" ]; then
    echo -e "${RED}❌ Error: Must run from medtainer-dev directory${NC}"
    exit 1
fi

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    echo ""
    git status --short
    echo ""
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        echo "Deployment cancelled"
        exit 0
    fi
fi

echo -e "${GREEN}✓${NC} Pre-flight checks passed"
echo ""

# Show what will be deployed
CURRENT_COMMIT=$(git log -1 --oneline)
echo -e "Deploying commit: ${GREEN}${CURRENT_COMMIT}${NC}"
echo ""

# Confirm deployment
read -p "Deploy to production? (y/n): " DEPLOY
if [ "$DEPLOY" != "y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo -e "${YELLOW}📦 Step 1/5: Syncing code to DigitalOcean...${NC}"
rsync -avz \
    --exclude '.git' \
    --exclude '.env' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude 'medtainer-mcp.tar.gz' \
    --exclude 'postgres_data' \
    --exclude 'redis_data' \
    "${LOCAL_PATH}/" "${DO_HOST}:${DO_PATH}/"

echo -e "${GREEN}✓${NC} Code synced"
echo ""

echo -e "${YELLOW}🔧 Step 2/5: Updating .env on server...${NC}"
ssh ${DO_HOST} "cd ${DO_PATH} && echo 'MCP_API_KEY=y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A' >> .env"
echo -e "${GREEN}✓${NC} Environment configured"
echo ""

echo -e "${YELLOW}🏗️  Step 3/5: Building Docker image...${NC}"
ssh ${DO_HOST} "cd ${DO_PATH} && docker-compose build mcp"
echo -e "${GREEN}✓${NC} Image built"
echo ""

echo -e "${YELLOW}🔄 Step 4/5: Restarting containers...${NC}"
ssh ${DO_HOST} "cd ${DO_PATH} && docker-compose down && docker-compose up -d"
echo -e "${GREEN}✓${NC} Containers restarted"
echo ""

echo -e "${YELLOW}🏥 Step 5/5: Checking health...${NC}"
sleep 5  # Give server time to start

HEALTH_CHECK=$(ssh ${DO_HOST} "curl -s http://localhost:8000/health" || echo '{"status":"error"}')
if echo "$HEALTH_CHECK" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓${NC} Health check passed"
    echo ""
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    echo "Production URLs:"
    echo "  - HTTPS: https://medtainer.aijesusbro.com"
    echo "  - Health: https://medtainer.aijesusbro.com/health"
    echo "  - SSE Endpoint: https://medtainer.aijesusbro.com/sse"
    echo ""
    echo "Authentication:"
    echo "  - Method 1: OAuth Bearer token (Claude Desktop)"
    echo "  - Method 2: X-API-Key header"
    echo ""
    echo "Check logs:"
    echo "  ssh ${DO_HOST} 'docker logs medtainer-mcp --tail 50'"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Response: $HEALTH_CHECK"
    echo ""
    echo "Check logs with:"
    echo "  ssh ${DO_HOST} 'docker logs medtainer-mcp'"
    exit 1
fi
