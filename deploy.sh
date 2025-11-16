#!/bin/bash

# MedTainer MCP Server - Deployment Script
# This script automates deployment to DigitalOcean

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DROPLET_USER="medtainer"
DROPLET_IP=""  # Will be prompted
APP_DIR="medtainer-mcp"

echo -e "${GREEN}=== MedTainer MCP Server Deployment ===${NC}\n"

# Check if we have required commands
command -v ssh >/dev/null 2>&1 || { echo -e "${RED}Error: ssh is required but not installed.${NC}" >&2; exit 1; }
command -v scp >/dev/null 2>&1 || { echo -e "${RED}Error: scp is required but not installed.${NC}" >&2; exit 1; }
command -v tar >/dev/null 2>&1 || { echo -e "${RED}Error: tar is required but not installed.${NC}" >&2; exit 1; }

# Get droplet IP if not set
if [ -z "$DROPLET_IP" ]; then
    read -p "Enter your DigitalOcean Droplet IP: " DROPLET_IP
fi

# Get deployment type
echo -e "\n${YELLOW}Select deployment type:${NC}"
echo "1. Initial deployment (first time setup)"
echo "2. Update deployment (code changes only)"
read -p "Choice (1 or 2): " DEPLOY_TYPE

if [ "$DEPLOY_TYPE" == "1" ]; then
    echo -e "\n${GREEN}=== Initial Deployment ===${NC}"

    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo -e "${RED}Error: .env file not found. Please create it from .env.example${NC}"
        exit 1
    fi

    # Create tarball
    echo -e "\n${YELLOW}Creating deployment package...${NC}"
    tar --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
        --exclude='*.log' --exclude='.DS_Store' \
        -czf medtainer-mcp.tar.gz .

    echo -e "${GREEN}Package created: medtainer-mcp.tar.gz${NC}"

    # Upload to server
    echo -e "\n${YELLOW}Uploading to server...${NC}"
    scp medtainer-mcp.tar.gz ${DROPLET_USER}@${DROPLET_IP}:~/

    # Extract and setup on server
    echo -e "\n${YELLOW}Setting up on server...${NC}"
    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        set -e

        # Create directory
        mkdir -p ~/medtainer-mcp

        # Extract
        tar -xzf medtainer-mcp.tar.gz -C ~/medtainer-mcp

        # Go to directory
        cd ~/medtainer-mcp

        # Start services
        docker-compose -f docker-compose.prod.yml up -d --build

        echo "Waiting for services to start..."
        sleep 10

        # Check status
        docker-compose -f docker-compose.prod.yml ps

        echo "Deployment complete!"
ENDSSH

    # Clean up local tarball
    rm medtainer-mcp.tar.gz

    echo -e "\n${GREEN}=== Initial Deployment Complete ===${NC}"
    echo -e "Server is running at: http://${DROPLET_IP}:8000"
    echo -e "Test with: curl http://${DROPLET_IP}:8000/health"

elif [ "$DEPLOY_TYPE" == "2" ]; then
    echo -e "\n${GREEN}=== Update Deployment ===${NC}"

    # Create tarball (excluding .env this time to preserve server settings)
    echo -e "\n${YELLOW}Creating update package...${NC}"
    tar --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
        --exclude='*.log' --exclude='.DS_Store' --exclude='.env' \
        -czf medtainer-mcp-update.tar.gz .

    echo -e "${GREEN}Package created: medtainer-mcp-update.tar.gz${NC}"

    # Upload to server
    echo -e "\n${YELLOW}Uploading to server...${NC}"
    scp medtainer-mcp-update.tar.gz ${DROPLET_USER}@${DROPLET_IP}:~/

    # Extract and restart on server
    echo -e "\n${YELLOW}Updating on server...${NC}"
    ssh ${DROPLET_USER}@${DROPLET_IP} << 'ENDSSH'
        set -e

        # Backup current .env
        cp ~/medtainer-mcp/.env ~/medtainer-mcp/.env.backup

        # Extract update (will preserve .env since it's excluded)
        tar -xzf medtainer-mcp-update.tar.gz -C ~/medtainer-mcp

        # Restore .env
        cp ~/medtainer-mcp/.env.backup ~/medtainer-mcp/.env

        # Go to directory
        cd ~/medtainer-mcp

        # Rebuild and restart
        docker-compose -f docker-compose.prod.yml build mcp
        docker-compose -f docker-compose.prod.yml up -d

        echo "Waiting for services to restart..."
        sleep 10

        # Check status
        docker-compose -f docker-compose.prod.yml ps

        echo "Update complete!"
ENDSSH

    # Clean up local tarball
    rm medtainer-mcp-update.tar.gz

    echo -e "\n${GREEN}=== Update Deployment Complete ===${NC}"
    echo -e "Server updated at: http://${DROPLET_IP}:8000"

else
    echo -e "${RED}Invalid choice${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Useful commands:${NC}"
echo "  View logs:    ssh ${DROPLET_USER}@${DROPLET_IP} 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml logs -f'"
echo "  Check status: ssh ${DROPLET_USER}@${DROPLET_IP} 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml ps'"
echo "  Restart:      ssh ${DROPLET_USER}@${DROPLET_IP} 'cd medtainer-mcp && docker-compose -f docker-compose.prod.yml restart'"
echo ""
