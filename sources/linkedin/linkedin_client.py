"""LinkedIn MCP Server client interface."""

import subprocess
import json
import logging
import os
import atexit
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import LINKEDIN_COOKIE, LINKEDIN_SESSION_PATH, MAX_RESULTS_PER_SEARCH

logger = logging.getLogger(__name__)

MCP_DOCKER_IMAGE = "stickerdaniel/linkedin-mcp-server:latest"

# Global MCP session state
_mcp_process = None
_mcp_request_id = 0
_mcp_initialized = False


def _ensure_mcp_session():
    """
    Ensure MCP server session is initialized.

    MCP servers require a stateful session with proper initialization.
    This function maintains a persistent Docker container and initializes
    it if not already done.
    """
    global _mcp_process, _mcp_initialized, _mcp_request_id

    if _mcp_process is None:
        logger.info("Starting MCP server Docker container")

        # Build command based on available authentication method
        if LINKEDIN_COOKIE:
            logger.info("Using cookie-based authentication")
            cmd = [
                "docker", "run", "--rm", "-i",
                "-e", f"LINKEDIN_COOKIE={LINKEDIN_COOKIE}",
                MCP_DOCKER_IMAGE
            ]
        else:
            # Use session file authentication
            logger.info(f"Using session file authentication: {LINKEDIN_SESSION_PATH}")
            # Mount the session file into the container
            cmd = [
                "docker", "run", "--rm", "-i",
                "-v", f"{LINKEDIN_SESSION_PATH}:/root/.linkedin-mcp/session.json:ro",
                MCP_DOCKER_IMAGE
            ]

        _mcp_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Register cleanup handler
        atexit.register(_cleanup_mcp_session)

    if not _mcp_initialized:
        logger.info("Initializing MCP server session")
        _mcp_request_id += 1

        init_request = {
            "jsonrpc": "2.0",
            "id": _mcp_request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "linkedin-job-agent",
                    "version": "1.0.0"
                }
            }
        }

        _send_mcp_request(init_request)
        _mcp_initialized = True
        logger.info("MCP server initialized successfully")


def _send_mcp_request(request: dict) -> dict:
    """
    Send a request to the MCP server and read the response.

    Args:
        request: JSON-RPC request dictionary

    Returns:
        Parsed JSON-RPC response

    Raises:
        RuntimeError: If the request fails
    """
    global _mcp_process

    if _mcp_process is None or _mcp_process.poll() is not None:
        raise RuntimeError("MCP server process is not running")

    # Send request
    request_str = json.dumps(request) + "\n"
    logger.debug(f"MCP Request: {request}")

    _mcp_process.stdin.write(request_str)
    _mcp_process.stdin.flush()

    # Read response
    response_line = _mcp_process.stdout.readline()
    if not response_line:
        raise RuntimeError("No response from MCP server")

    response = json.loads(response_line)
    logger.debug(f"MCP Response: {response}")

    return response


def _cleanup_mcp_session():
    """Clean up MCP session on exit."""
    global _mcp_process, _mcp_initialized

    if _mcp_process is not None:
        logger.info("Cleaning up MCP server session")
        try:
            _mcp_process.stdin.close()
            _mcp_process.terminate()
            _mcp_process.wait(timeout=5)
        except Exception as e:
            logger.warning(f"Error during MCP cleanup: {e}")
            _mcp_process.kill()
        finally:
            _mcp_process = None
            _mcp_initialized = False


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    Call a LinkedIn MCP server tool.

    This function maintains a persistent MCP server session and properly
    handles the initialization sequence required by the MCP protocol.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Dictionary of arguments for the tool

    Returns:
        Parsed result from the MCP server

    Raises:
        RuntimeError: If the MCP server call fails
    """
    global _mcp_request_id

    logger.debug(f"Calling MCP tool: {tool_name} with args: {arguments}")

    try:
        # Ensure session is initialized
        _ensure_mcp_session()

        # Prepare the tool call request
        _mcp_request_id += 1
        tool_request = {
            "jsonrpc": "2.0",
            "id": _mcp_request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Send the request
        response = _send_mcp_request(tool_request)

        # Check for errors in the response
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        # Extract result
        result = response.get("result", {})

        # Check if the result indicates an error (only for isError=true)
        if isinstance(result, dict) and result.get("isError"):
            error_text = result.get("content", [{}])[0].get("text", "Unknown error")
            raise RuntimeError(f"MCP tool error: {error_text}")

        # Note: We don't throw exceptions for authentication errors
        # (structuredContent.error) - we return the result and let
        # the calling function handle it appropriately
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MCP response: {e}")
        raise RuntimeError(f"Invalid JSON response from MCP: {e}")
    except Exception as e:
        logger.error(f"Unexpected error calling MCP tool: {e}")
        raise


def search_jobs(keywords: str, location: str = None, limit: int = None) -> list[dict]:
    """
    Search for jobs using LinkedIn MCP server.

    Args:
        keywords: Search keywords (e.g., "software engineer")
        location: Location filter (e.g., "Remote", "New York") - optional
        limit: Maximum number of results (default from config)

    Returns:
        List of job dictionaries with URLs
    """
    if limit is None:
        limit = MAX_RESULTS_PER_SEARCH

    logger.info(f"Searching jobs: keywords='{keywords}', location='{location}', limit={limit}")

    # Build arguments (only include location if provided)
    arguments = {
        "keywords": keywords,
        "limit": limit
    }
    if location:
        arguments["location"] = location

    try:
        result = call_mcp_tool("search_jobs", arguments)

        # Parse the response - MCP returns data in structuredContent
        if isinstance(result, dict):
            structured = result.get("structuredContent", {})

            # Check for authentication errors
            if structured.get("error") == "authentication_failed":
                logger.error(f"LinkedIn authentication failed: {structured.get('message')}")
                logger.error(f"Resolution: {structured.get('resolution')}")
                return []

            if structured:
                job_urls = structured.get("job_urls", [])
                count = structured.get("count", len(job_urls))
                logger.info(f"Found {count} job URLs for query: {keywords}")

                # Convert job URLs to job dictionaries
                jobs = []
                for url in job_urls:
                    # Extract job ID from URL (format: https://www.linkedin.com/jobs/view/JOBID/)
                    job_id = url.split("/")[-2] if "/" in url else None
                    jobs.append({
                        "url": url,
                        "id": job_id,
                        "linkedin_job_id": job_id
                    })
                return jobs

        logger.warning(f"Unexpected response format from search_jobs: {result}")
        return []

    except Exception as e:
        logger.error(f"Failed to search jobs: {e}")
        return []


def get_job_details(job_id: str) -> Optional[dict]:
    """
    Get detailed information for a specific job.

    Args:
        job_id: LinkedIn job ID

    Returns:
        Detailed job information dictionary or None if failed
    """
    logger.info(f"Fetching job details for job_id={job_id}")

    try:
        result = call_mcp_tool("get_job_details", {"job_id": job_id})

        # Parse the response - MCP returns data in structuredContent
        if isinstance(result, dict):
            structured = result.get("structuredContent", {})
            if structured:
                return structured

            # Fallback: check for content array with text
            content = result.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "")
                if text_content:
                    # Try to parse as JSON
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError:
                        return {"description": text_content}

        return result

    except Exception as e:
        logger.error(f"Failed to get job details for {job_id}: {e}")
        return None


def enrich_job_data(job: dict) -> dict:
    """
    Enrich basic job data with detailed information.

    Args:
        job: Basic job dictionary from search results

    Returns:
        Enriched job dictionary with more details
    """
    job_id = job.get('id') or job.get('linkedin_job_id')
    if not job_id:
        logger.warning("Job missing ID, cannot enrich")
        return job

    details = get_job_details(job_id)
    if details:
        job.update(details)

    return job
