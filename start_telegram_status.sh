#!/bin/bash
# Start Telegram status bot in background
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
nohup python telegram_status_bot.py > logs/telegram_status.log 2>&1 &
echo $! > telegram_status.pid
echo "Telegram status bot started with PID: $(cat telegram_status.pid)"
echo "View logs: tail -f logs/telegram_status.log"
