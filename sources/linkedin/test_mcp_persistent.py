#!/usr/bin/env python3
"""
Test MCP server with persistent session.
This maintains a single Docker container and sends multiple requests.
"""

import subprocess
import json
import os
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_COOKIE = os.getenv("LINKEDIN_COOKIE")
MCP_DOCKER_IMAGE = "stickerdaniel/linkedin-mcp-server:latest"


def test_persistent_session():
    """Test MCP server with persistent Docker container."""
    print("="*80)
    print("TESTING MCP SERVER WITH PERSISTENT SESSION")
    print("="*80)

    cmd = [
        "docker", "run", "--rm", "-i",
        "-e", f"LINKEDIN_COOKIE={LINKEDIN_COOKIE}",
        MCP_DOCKER_IMAGE
    ]

    # Start the Docker container
    print("\nStarting Docker container...")
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    def send_request(request_dict):
        """Send a request and read the response."""
        request_str = json.dumps(request_dict) + "\n"
        print(f"\n{'='*80}")
        print(f"SENDING: {request_dict['method']}")
        print(json.dumps(request_dict, indent=2))
        print(f"{'='*80}")

        process.stdin.write(request_str)
        process.stdin.flush()

        # Read response
        response_line = process.stdout.readline()
        if response_line:
            try:
                response = json.loads(response_line)
                print(f"\nRESPONSE:")
                print(json.dumps(response, indent=2))
                return response
            except json.JSONDecodeError as e:
                print(f"\nERROR parsing response: {e}")
                print(f"Raw line: {response_line}")
                return None
        else:
            print("\nNo response received")
            return None

    try:
        # Step 1: Initialize
        init_response = send_request({
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
        })

        if not init_response or "error" in init_response:
            print("\n❌ Initialization failed!")
            return

        print("\n✅ Initialization successful!")

        # Step 2: List tools
        tools_response = send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        })

        if tools_response and "result" in tools_response:
            print("\n✅ Tools list retrieved!")
            print("\nAVAILABLE TOOLS:")
            print("="*80)
            for tool in tools_response["result"].get("tools", []):
                print(f"\nTool: {tool['name']}")
                print(f"Description: {tool.get('description', 'N/A')}")
                if 'inputSchema' in tool:
                    print(f"Input Schema:")
                    print(json.dumps(tool['inputSchema'], indent=2))
        else:
            print("\n❌ Failed to list tools")

        # Step 3: Try search_jobs (now with correct schema)
        print("\n" + "="*80)
        print("TESTING search_jobs")
        print("="*80)

        search_response = send_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_jobs",
                "arguments": {
                    "keywords": "software engineer",
                    "location": "Remote",
                    "limit": 3
                }
            }
        })

        if search_response and "result" in search_response:
            print("\n✅ search_jobs successful!")
            result = search_response["result"]
            if isinstance(result, list):
                print(f"Found {len(result)} jobs")
            elif isinstance(result, dict) and "content" in result:
                # MCP often returns content array
                for content_item in result["content"]:
                    if content_item["type"] == "text":
                        print(f"\n{content_item['text'][:500]}...")
        else:
            print("\n❌ search_jobs failed")

        # Step 4: Try get_recommended_jobs
        print("\n" + "="*80)
        print("TESTING get_recommended_jobs")
        print("="*80)

        rec_response = send_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_recommended_jobs",
                "arguments": {
                    "limit": 3
                }
            }
        })

        if rec_response and "result" in rec_response:
            print("\n✅ get_recommended_jobs successful!")
        else:
            print("\n❌ get_recommended_jobs failed")

    finally:
        # Clean up
        process.stdin.close()
        process.terminate()
        process.wait(timeout=5)
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)


if __name__ == "__main__":
    if not LINKEDIN_COOKIE:
        print("ERROR: LINKEDIN_COOKIE environment variable not set")
        exit(1)

    test_persistent_session()
