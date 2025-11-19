#!/bin/bash
set -e

echo "=== Deploying Enhanced Logging to Medtainer MCP Server ==="
echo "Server: 24.199.118.227"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Copying updated routes.py to server...${NC}"
scp app/api/routes.py root@24.199.118.227:/root/medtainer-mcp/app/api/routes.py

echo ""
echo -e "${YELLOW}Step 2: Restarting MCP container...${NC}"
ssh root@24.199.118.227 "cd /root/medtainer-mcp && docker-compose restart mcp"

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo "=== Next Steps ==="
echo "1. Wait 10 seconds for container to fully restart"
echo "2. Test OAuth flow from Claude Desktop"
echo "3. View logs with: ssh root@24.199.118.227 'docker logs medtainer-mcp-local -f'"
echo ""
echo "=== Key Log Markers ==="
echo "  • === OAUTH FLOW === - OAuth authentication steps"
echo "  • === MCP SSE CONNECTION START === - SSE stream initiation"
echo "  • === SESSION === - Session management"
echo "  • === REQUEST BODY === - Request parsing"
echo "  • === SSE STREAM START === - Event generation begins"
echo "  • === STREAM CLOSING === - Stream termination (with reason)"
echo ""
