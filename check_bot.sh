#!/bin/bash
# Quick bot status check
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
python check_status.py
