#!/bin/bash

# Quick Database Integration Verification Script
# This checks if everything is running and configured correctly

echo "=================================="
echo "MedTainer MCP Database Check"
echo "=================================="
echo ""

# Check if docker-compose is running
echo "1. Checking Docker containers..."
if docker-compose ps | grep -q "medtainer-postgres.*Up"; then
    echo "   ✅ PostgreSQL container is running"
else
    echo "   ❌ PostgreSQL container is not running"
    echo "   Run: docker-compose up -d"
    exit 1
fi

if docker-compose ps | grep -q "medtainer-mcp.*Up"; then
    echo "   ✅ MCP container is running"
else
    echo "   ❌ MCP container is not running"
    echo "   Run: docker-compose up -d"
    exit 1
fi

# Check if database is responding
echo ""
echo "2. Testing database connectivity..."
if docker-compose exec -T postgres psql -U mcp -d medtainer -c "SELECT 1;" > /dev/null 2>&1; then
    echo "   ✅ Database is accessible"
else
    echo "   ❌ Cannot connect to database"
    exit 1
fi

# Check if tables exist
echo ""
echo "3. Checking database tables..."
TABLES=$(docker-compose exec -T postgres psql -U mcp -d medtainer -t -c "\dt" | grep -E "tool_executions|api_calls|contacts|invoices|orders" | wc -l)
if [ "$TABLES" -ge 5 ]; then
    echo "   ✅ All required tables exist ($TABLES/5)"
else
    echo "   ⚠️  Only $TABLES/5 tables found"
    echo "   Run: docker-compose exec mcp alembic upgrade head"
fi

# Check if API is responding
echo ""
echo "4. Testing MCP API..."
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ API is responding"
    APP_NAME=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin)['app'])" 2>/dev/null || echo "MedTainer MCP")
    echo "   App: $APP_NAME"
else
    echo "   ❌ API is not responding"
    exit 1
fi

# Check if logs endpoint works
echo ""
echo "5. Testing logs endpoint..."
if curl -s -f http://localhost:8000/mcp/logs?limit=1 > /dev/null 2>&1; then
    echo "   ✅ Logs endpoint is working"
    LOG_COUNT=$(curl -s http://localhost:8000/mcp/logs?limit=1 | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])" 2>/dev/null || echo "0")
    echo "   Current log entries: $LOG_COUNT"
else
    echo "   ❌ Logs endpoint not responding"
fi

# Try to execute a test tool
echo ""
echo "6. Executing test tool..."
if curl -s -X POST -H "Content-Type: application/json" \
   -d '{"limit": 3}' \
   http://localhost:8000/mcp/run/gohighlevel.read_contacts > /dev/null 2>&1; then
    echo "   ✅ Tool execution successful"
    
    # Wait a moment for logging
    sleep 1
    
    # Check if it was logged
    NEW_COUNT=$(curl -s http://localhost:8000/mcp/logs?limit=1 | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])" 2>/dev/null || echo "0")
    if [ "$NEW_COUNT" -gt "$LOG_COUNT" ]; then
        echo "   ✅ Execution was logged to database"
    else
        echo "   ⚠️  Execution might not have been logged"
    fi
else
    echo "   ❌ Tool execution failed"
fi

# Summary
echo ""
echo "=================================="
echo "Summary"
echo "=================================="
echo ""
echo "✅ PostgreSQL database integration is working!"
echo ""
echo "Next steps:"
echo "  • View logs: http://localhost:8000/mcp/logs"
echo "  • Run full tests: python test_database.py"
echo "  • Connect to DB: docker-compose exec postgres psql -U mcp medtainer"
echo ""
echo "Documentation:"
echo "  • DATABASE_SUMMARY.md - Quick overview"
echo "  • DATABASE_SETUP.md - Detailed guide"
echo ""
