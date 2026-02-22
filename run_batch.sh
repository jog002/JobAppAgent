#!/bin/bash
# Batch Job Runner for Job Search Agent
# This script is designed to be called by launchd for scheduled automation
#
# Usage: ./run_batch.sh
#
# Features:
# - Uses caffeinate to prevent sleep during execution
# - Logs output to logs/batch_stdout.log and logs/batch_stderr.log
# - Returns Mac to sleep after completion

set -e

# Change to project directory
cd /Users/oscargiller/Projects/JobApp_Agent

# Log start time
echo "=========================================="
echo "Batch job started at: $(date)"
echo "=========================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the batch job with caffeinate to prevent sleep
# -i: prevent idle sleep
# -s: prevent system sleep
caffeinate -is python main.py batch

# Log completion
echo "=========================================="
echo "Batch job completed at: $(date)"
echo "=========================================="

# Return to sleep after job completes
# Note: pmset sleepnow requires root, so we use a softer approach
# The system will naturally return to sleep based on Energy Saver settings
# If you want immediate sleep, uncomment the line below and run with sudo
# sudo pmset sleepnow

exit 0
