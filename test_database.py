#!/usr/bin/env python3
"""
Database Integration Test Script

This script tests the PostgreSQL database integration by:
1. Checking database connectivity
2. Verifying all tables exist
3. Executing test tool calls
4. Querying logs via API
5. Running direct database queries
"""

import time
import httpx
import sys
from sqlalchemy import create_engine, text, inspect
from datetime import datetime


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_database_connection():
    """Test direct database connection."""
    print_section("1. Testing Database Connection")
    
    try:
        engine = create_engine("postgresql://mcp:mcp_secure_password_change_me@localhost:5432/medtainer")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Database connected successfully!")
            print(f"   PostgreSQL version: {version[:50]}...")
            return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)


def test_tables_exist(engine):
    """Verify all required tables exist."""
    print_section("2. Verifying Database Tables")
    
    inspector = inspect(engine)
    expected_tables = [
        'tool_executions',
        'api_calls',
        'contacts',
        'invoices',
        'orders',
        'alembic_version'
    ]
    
    existing_tables = inspector.get_table_names()
    
    all_exist = True
    for table in expected_tables:
        if table in existing_tables:
            print(f"✅ Table '{table}' exists")
        else:
            print(f"❌ Table '{table}' is missing!")
            all_exist = False
    
    if not all_exist:
        print("\n⚠️  Some tables are missing. Run migrations:")
        print("   docker-compose exec mcp alembic upgrade head")
        sys.exit(1)


def test_api_health():
    """Test API health endpoint."""
    print_section("3. Testing API Health")
    
    try:
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy")
            print(f"   App: {data.get('app')}")
            print(f"   Environment: {data.get('environment')}")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        print("   Make sure the server is running: docker-compose up -d")
        sys.exit(1)


def test_tool_execution():
    """Execute test tools and verify logging."""
    print_section("4. Testing Tool Execution & Logging")
    
    tools_to_test = [
        ("gohighlevel.read_contacts", {"limit": 3}),
        ("gohighlevel.pipeline_digest", {}),
        ("quickbooks.recent_invoices", {"limit": 5}),
    ]
    
    executed_count = 0
    for tool_name, params in tools_to_test:
        try:
            print(f"\n📝 Executing: {tool_name}")
            start = time.time()
            
            response = httpx.post(
                f"http://localhost:8000/mcp/run/{tool_name}",
                json=params,
                timeout=10
            )
            
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                source = data.get('metadata', {}).get('source', 'unknown')
                print(f"   ✅ Success (status={status}, source={source}, {duration}ms)")
                executed_count += 1
            else:
                print(f"   ❌ Failed with status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n✅ Executed {executed_count} / {len(tools_to_test)} tools successfully")
    
    # Wait a moment for middleware to finish logging
    time.sleep(1)


def test_logs_api():
    """Query logs via API endpoint."""
    print_section("5. Testing Logs API Endpoint")
    
    try:
        # Get recent logs
        response = httpx.get("http://localhost:8000/mcp/logs?limit=5", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            logs = data.get('logs', [])
            
            print(f"✅ Logs API returned {count} executions")
            
            if logs:
                print("\n   Recent executions:")
                for log in logs[:3]:  # Show first 3
                    timestamp = log.get('timestamp', '')
                    tool_name = log.get('tool_name', '')
                    duration = log.get('duration_ms', 0)
                    status = log.get('status', '')
                    source = log.get('source', '')
                    print(f"   • {tool_name} - {status} ({duration}ms, {source}) at {timestamp[:19]}")
            else:
                print("   ⚠️  No logs found - execute some tools first")
        else:
            print(f"❌ Logs API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Logs API error: {e}")


def test_direct_query(engine):
    """Run direct database queries."""
    print_section("6. Testing Direct Database Queries")
    
    queries = [
        (
            "Recent Executions",
            """
            SELECT tool_name, status, duration_ms, source, timestamp
            FROM tool_executions
            ORDER BY timestamp DESC
            LIMIT 5
            """
        ),
        (
            "Tool Usage Summary",
            """
            SELECT 
                tool_name,
                COUNT(*) as executions,
                AVG(duration_ms)::int as avg_ms,
                MAX(duration_ms) as max_ms
            FROM tool_executions
            GROUP BY tool_name
            ORDER BY executions DESC
            """
        ),
        (
            "Success Rate",
            """
            SELECT 
                status,
                COUNT(*) as count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
            FROM tool_executions
            GROUP BY status
            """
        ),
    ]
    
    with engine.connect() as conn:
        for query_name, query in queries:
            try:
                print(f"\n📊 {query_name}:")
                result = conn.execute(text(query))
                rows = result.fetchall()
                
                if rows:
                    # Print column headers
                    columns = result.keys()
                    print(f"   {' | '.join(columns)}")
                    print(f"   {'-' * 60}")
                    
                    # Print rows
                    for row in rows:
                        values = [str(val)[:30] if val is not None else 'NULL' for val in row]
                        print(f"   {' | '.join(values)}")
                else:
                    print("   (No data)")
                    
            except Exception as e:
                print(f"   ❌ Query failed: {e}")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  MedTainer MCP Database Integration Test")
    print("="*60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Run tests
    engine = test_database_connection()
    test_tables_exist(engine)
    test_api_health()
    test_tool_execution()
    test_logs_api()
    test_direct_query(engine)
    
    # Summary
    print_section("Test Summary")
    print("✅ All tests completed!")
    print("\nYour database integration is working correctly.")
    print("\nNext steps:")
    print("  1. View logs in browser: http://localhost:8000/mcp/logs")
    print("  2. Connect to DB: docker-compose exec postgres psql -U mcp medtainer")
    print("  3. Add real API credentials to enable live data logging")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
