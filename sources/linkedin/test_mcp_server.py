#!/usr/bin/env python3
"""
Diagnostic script to test the LinkedIn MCP server directly.
This will help us understand the correct MCP protocol format.
"""

import subprocess
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_COOKIE = os.getenv("LINKEDIN_COOKIE")
MCP_DOCKER_IMAGE = "stickerdaniel/linkedin-mcp-server:latest"


def send_mcp_request(request: dict) -> dict:
    """Send a single MCP request to the Docker container."""
    print(f"\n{'='*80}")
    print(f"SENDING REQUEST:")
    print(json.dumps(request, indent=2))
    print(f"{'='*80}\n")

    cmd = [
        "docker", "run", "--rm", "-i",
        "-e", f"LINKEDIN_COOKIE={LINKEDIN_COOKIE}",
        MCP_DOCKER_IMAGE
    ]

    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30
        )

        print(f"RETURN CODE: {result.returncode}")
        print(f"\nSTDOUT:")
        print(result.stdout)
        print(f"\nSTDERR:")
        print(result.stderr)

        if result.returncode == 0 and result.stdout:
            try:
                response = json.loads(result.stdout)
                print(f"\nPARSED RESPONSE:")
                print(json.dumps(response, indent=2))
                return response
            except json.JSONDecodeError as e:
                print(f"\nERROR: Failed to parse JSON response: {e}")
                return {"error": "JSON parse error", "raw_output": result.stdout}
        else:
            return {"error": "Docker command failed", "returncode": result.returncode, "stderr": result.stderr}

    except subprocess.TimeoutExpired:
        print("\nERROR: Request timed out")
        return {"error": "Timeout"}
    except Exception as e:
        print(f"\nERROR: {e}")
        return {"error": str(e)}


def test_initialize():
    """Test MCP initialization."""
    print("\n" + "="*80)
    print("TEST 1: MCP Initialize")
    print("="*80)

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    return send_mcp_request(request)


def test_list_tools():
    """Test tools/list to discover available tools."""
    print("\n" + "="*80)
    print("TEST 2: List Available Tools")
    print("="*80)

    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }

    return send_mcp_request(request)


def test_search_jobs_v1():
    """Test search_jobs with current parameter format."""
    print("\n" + "="*80)
    print("TEST 3: search_jobs (current format)")
    print("="*80)

    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_jobs",
            "arguments": {
                "keywords": "software engineer",
                "location": "Remote",
                "limit": 5
            }
        }
    }

    return send_mcp_request(request)


def test_search_jobs_v2():
    """Test search_jobs with alternative parameter format."""
    print("\n" + "="*80)
    print("TEST 4: search_jobs (alternative format - query/count)")
    print("="*80)

    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "search_jobs",
            "arguments": {
                "query": "software engineer",
                "location": "Remote",
                "count": 5
            }
        }
    }

    return send_mcp_request(request)


def test_search_jobs_v3():
    """Test search_jobs with minimal parameters."""
    print("\n" + "="*80)
    print("TEST 5: search_jobs (minimal - keywords only)")
    print("="*80)

    request = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "search_jobs",
            "arguments": {
                "keywords": "software engineer"
            }
        }
    }

    return send_mcp_request(request)


def test_recommended_jobs():
    """Test get_recommended_jobs."""
    print("\n" + "="*80)
    print("TEST 6: get_recommended_jobs")
    print("="*80)

    request = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "get_recommended_jobs",
            "arguments": {
                "limit": 5
            }
        }
    }

    return send_mcp_request(request)


def main():
    """Run all diagnostic tests."""
    if not LINKEDIN_COOKIE:
        print("ERROR: LINKEDIN_COOKIE environment variable not set")
        sys.exit(1)

    print("\n" + "="*80)
    print("LINKEDIN MCP SERVER DIAGNOSTIC TESTS")
    print("="*80)
    print(f"Docker Image: {MCP_DOCKER_IMAGE}")
    print(f"Cookie Length: {len(LINKEDIN_COOKIE)} characters")

    results = {}

    # Run all tests
    results['initialize'] = test_initialize()
    results['list_tools'] = test_list_tools()
    results['search_jobs_v1'] = test_search_jobs_v1()
    results['search_jobs_v2'] = test_search_jobs_v2()
    results['search_jobs_v3'] = test_search_jobs_v3()
    results['recommended_jobs'] = test_recommended_jobs()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, result in results.items():
        if isinstance(result, dict):
            if "error" in result and "code" not in result:
                status = "❌ FAILED"
            elif "error" in result:
                status = f"❌ MCP ERROR (code: {result['error'].get('code', 'unknown')})"
            elif "result" in result:
                status = "✅ SUCCESS"
            else:
                status = "⚠️  UNKNOWN"
        else:
            status = "⚠️  UNEXPECTED RESPONSE"

        print(f"{test_name}: {status}")

    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    print("\nCheck the output above to see which parameter format works.")
    print("Look for tools/list response to see the official schema.\n")


if __name__ == "__main__":
    main()
