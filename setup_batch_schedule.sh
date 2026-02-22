#!/bin/bash
# Setup Script for Batch Job Scheduling
# This script configures macOS to run the job agent automatically at 3 AM daily
#
# Usage: ./setup_batch_schedule.sh
#
# What this does:
# 1. Schedules Mac to wake at 3:00 AM daily (pmset)
# 2. Installs launchd agent to run the batch job at 3:01 AM
#
# Requirements:
# - Admin password (for pmset)
# - Mac must be plugged in or have sufficient battery

set -e

echo "=========================================="
echo "Job Agent Batch Schedule Setup"
echo "=========================================="
echo ""

PROJECT_DIR="/Users/oscargiller/Projects/JobApp_Agent"
PLIST_NAME="com.oscar.jobagent.batch.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

# Step 1: Create logs directory if it doesn't exist
echo "Step 1: Ensuring logs directory exists..."
mkdir -p "$PROJECT_DIR/logs"
echo "  Done."
echo ""

# Step 2: Schedule wake with pmset
echo "Step 2: Scheduling Mac to wake at 3:00 AM daily..."
echo "  (This requires your admin password)"
sudo pmset repeat wake MTWRFSU 03:00:00
echo "  Done. Current schedule:"
pmset -g sched
echo ""

# Step 3: Copy plist to LaunchAgents
echo "Step 3: Installing launchd agent..."
mkdir -p "$LAUNCH_AGENTS_DIR"

# Unload existing agent if present
if launchctl list | grep -q "com.oscar.jobagent.batch"; then
    echo "  Unloading existing agent..."
    launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_NAME" 2>/dev/null || true
fi

cp "$PROJECT_DIR/$PLIST_NAME" "$LAUNCH_AGENTS_DIR/"
echo "  Copied plist to $LAUNCH_AGENTS_DIR"
echo ""

# Step 4: Load the agent
echo "Step 4: Loading launchd agent..."
launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_NAME"
echo "  Done."
echo ""

# Step 5: Verify
echo "Step 5: Verifying installation..."
echo ""
echo "  pmset schedule:"
pmset -g sched
echo ""
echo "  launchd status:"
launchctl list | grep -E "(PID|jobagent)" || echo "  Agent loaded (will run at scheduled time)"
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Your Mac will now:"
echo "  1. Wake from sleep at 3:00 AM daily"
echo "  2. Run the job search at 3:01 AM"
echo "  3. Return to sleep after completion"
echo ""
echo "To test manually, run:"
echo "  ./run_batch.sh"
echo ""
echo "To check logs:"
echo "  tail -f logs/batch_stdout.log"
echo "  tail -f logs/batch_stderr.log"
echo ""
echo "To uninstall:"
echo "  launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo "  sudo pmset repeat cancel"
echo ""
