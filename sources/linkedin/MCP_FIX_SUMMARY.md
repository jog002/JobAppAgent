# LinkedIn MCP Server Fix Summary

## The Problem

You were receiving this error:
```
MCP error: {'code': -32602, 'message': 'Invalid request parameters', 'data': ''}
```

Error code `-32602` is the JSON-RPC standard error for "Invalid params".

## Root Cause

The LinkedIn MCP server requires a **stateful session** with proper initialization before it can accept tool calls. Your original code was creating a new Docker container for each request (`docker run --rm`) and immediately sending `tools/call` without initializing the session first.

The MCP protocol requires this sequence:
1. **Initialize** - Establish session with `initialize` request
2. **Use tools** - Make `tools/call` requests
3. **Cleanup** - Close session when done

Your code was skipping step 1, causing the server to reject all requests with "Invalid request parameters" because it expected initialization first.

## The Fix

Updated [linkedin_client.py](linkedin_client.py) to:

### 1. Maintain Persistent Session
- Changed from one-shot Docker runs to a persistent subprocess
- Global `_mcp_process` maintains the Docker container across multiple requests
- Automatic cleanup on exit using `atexit.register()`

### 2. Proper MCP Initialization
- Added `_ensure_mcp_session()` function that:
  - Starts Docker container if not running
  - Sends `initialize` request on first use
  - Tracks initialization state to avoid re-initializing

### 3. Bidirectional Communication
- Changed from `subprocess.run()` to `subprocess.Popen()`
- Enables reading/writing multiple JSON-RPC messages
- Uses line-delimited JSON (one message per line)

### 4. Updated Response Parsing
- MCP returns results in `result.structuredContent` format
- Updated `search_jobs()` to parse `job_urls` array from structured content
- Updated `get_job_details()` to handle MCP response format
- Added proper error handling for authentication failures

### 5. Removed Non-Existent Tool
- Removed `get_recommended_jobs()` - this tool doesn't exist in the MCP server
- Available tools are: `search_jobs`, `get_job_details`, `get_person_profile`, `get_company_profile`, `get_company_posts`, `close_session`
- Updated [main.py](main.py) to remove the call to `get_recommended_jobs()`

## Testing Results

The MCP protocol now works correctly. The test output shows:

```
✅ MCP server initialized successfully
✅ Tools list retrieved successfully
✅ search_jobs request processed (though authentication failed)
```

The error changed from:
- **Before**: `"Invalid request parameters"` (protocol error ❌)
- **After**: `"authentication_failed"` (authentication error ⚠️)

This confirms the MCP protocol is working - we just need valid LinkedIn authentication.

## Current Issue: Authentication

Your `LINKEDIN_COOKIE` is either expired or invalid. The server responds with:

```json
{
  "error": "authentication_failed",
  "message": "Session expired or invalid.",
  "resolution": "Run with --get-session to re-authenticate or set LINKEDIN_COOKIE environment variable."
}
```

### How to Get a Valid LinkedIn Cookie

1. **Log into LinkedIn** in your browser
2. **Open Developer Tools** (F12 or right-click → Inspect)
3. **Go to Application/Storage tab**
4. **Find Cookies** → `https://www.linkedin.com`
5. **Copy the `li_at` cookie value**
6. **Update your `.env` file**:
   ```
   LINKEDIN_COOKIE=<paste the li_at value here>
   ```

The cookie value should be a long alphanumeric string (around 150+ characters).

### Important Notes

- LinkedIn cookies expire periodically (usually after a few weeks)
- You'll need to refresh the cookie when it expires
- Keep the cookie secure - it provides full access to your LinkedIn account

## Files Modified

1. **[linkedin_client.py](linkedin_client.py)** - Complete rewrite of MCP client implementation
   - Added session management (`_ensure_mcp_session`, `_send_mcp_request`, `_cleanup_mcp_session`)
   - Updated `call_mcp_tool()` to use persistent session
   - Updated `search_jobs()` to parse MCP response format
   - Updated `get_job_details()` to parse MCP response format
   - Removed `get_recommended_jobs()` (tool doesn't exist)

2. **[main.py](main.py)** - Removed call to non-existent tool
   - Removed `get_recommended_jobs()` call from `fetch_jobs_from_linkedin()`
   - Now only uses `search_jobs()` for job discovery

## Testing

Run the test script to verify the fix:

```bash
python test_linkedin_client.py
```

Once you update your LinkedIn cookie, the jobs should be fetched successfully.

## Next Steps

1. **Update your LinkedIn cookie** in `.env` file with a fresh `li_at` value
2. **Test the client**: `python test_linkedin_client.py`
3. **Run the full workflow**: `python main.py`

The MCP protocol is now working correctly!
