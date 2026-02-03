
# Polymarket BTC Trading Bot - Implementation Guide v2.0
## Powered by OpenClaw

**Project:** Automated 15-minute BTC Up/Down trading on Polymarket  
**Execution Engine:** OpenClaw (formerly ClawdBot/Moltbot)  
**Target Market:** https://polymarket.com/event/btc-updown-15m-1769939100  
**Initial Capital:** $500
**Resolution Source:** CryptoCompare, Chainlink BTC/USD data stream  
**Communication Channel:** Telegram (real-time trade alerts)

---

## 0. OPENCLAW OVERVIEW

### What Is OpenClaw?

OpenClaw is an open-source autonomous artificial intelligence personal assistant software project. It gained media attention in early 2026 following coverage by Wired, CNET, Axios, and Forbes, which highlighted its ability to "automate tasks, run commands and act like a digital personal assistant that never sleeps." OpenClaw is designed to operate as an autonomous software agent capable of executing tasks on behalf of users rather than functioning solely as a conversational chatbot.[[3]](https://en.wikipedia.org/wiki/OpenClaw)

### Why OpenClaw for Trading?

OpenClaw (formerly Moltbot and Clawdbot) is an open-source, self-hosted AI assistant designed to execute local computing tasks and interface with users through standard messaging platforms. Unlike traditional chatbots that function as advisors generating text, OpenClaw operates as an autonomous agent that can execute shell commands, manage files, and automate browser operations on the host machine.[[9]](https://research.aimultiple.com/moltbot/)

### Key Capabilities for Our Use Case

It can be deployed locally or on private servers and accepts commands through messaging platforms such as WhatsApp, Telegram, and Signal. The software integrates with external AI models and application programming interfaces, allowing it to manage calendars, send messages, conduct research, and automate workflows across multiple services.[[3]](https://en.wikipedia.org/wiki/OpenClaw)

Instead of waiting for prompts, ClawdBot can send you morning briefings, reminders, alerts, and summaries exactly when they matter. With the right permissions, ClawdBot can manage emails, update calendars, perform web research, automate browser tasks, or work with developer tools like GitHub.[[5]](https://medium.com/modelmind/how-to-set-up-clawdbot-step-by-step-guide-to-setup-a-personal-bot-3e7957ed2975)

---

## 1. HARD CONSTRAINTS (Non-Negotiable)

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Max position size | 10% of account ($50 on $500) | Survives losing streaks |
| Max concurrent positions | 2 | Prevents overconcentration |
| Cooling off after 10% drawdown | 4 hours | Prevents revenge trading |
| API error rate >5% | Immediate halt | Data quality guard |
| OpenClaw command whitelist | ENABLED | Prevent unauthorized actions |

---

## 2. CORE METRICS (Ranked by Priority)

### FIRST PRIORITY: Survival Metrics
- **Account balance trajectory** - Daily, weekly, monthly
- **Maximum drawdown** - Peak to trough decline
- **Consecutive loss streak** - Must survive 10+ losses
- **API uptime/downtime** - Data availability percentage

### SECOND PRIORITY: Signal Quality
- **Win rate** - Target 55-60% (realistic for 15-min timeframe)
- **Average win vs average loss** - Ratio > 1.0 (wins larger than losses)
- **Signal-to-noise ratio** - Valid signals vs false positives
- **Latency to signal** - Time from data to decision

### THIRD PRIORITY: Operational Efficiency
- **Fill rate** - Orders executed vs attempted
- **Slippage** - Expected vs actual fill price
- **API call efficiency** - Stay within rate limits
- **System uptime** - Bot availability percentage

---

## 3. OPENCLAW SETUP & CONFIGURATION

### 3.1 Prerequisites

Runtime: Node ≥22.[[8]](https://github.com/clawdbot/clawdbot)

```bash
# Install Node.js 22+ on Ubuntu
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
```

### 3.2 Installation

npm install -g openclaw@latest openclaw onboard --install-daemon[[8]](https://github.com/clawdbot/clawdbot)

The wizard installs the Gateway daemon (launchd/systemd user service) so it stays running.

git clone https://github.com/openclaw/openclaw.git
cd openclaw
pnpm install
pnpm ui:build
pnpm build
pnpm openclaw onboard --install-daemon[[8]](https://github.com/clawdbot/clawdbot)

### 3.3 Architecture Understanding

ClawdBot is structured into three layers that turn an LLM into a functional employee: The Communication Layer (Channels) connects to WhatsApp, Telegram, Slack, or iMessage. Your assistant lives where you chat. The Brain Layer (Models) lets you choose your provider—Anthropic (Claude), OpenAI, or even local models via Ollama. The Action Layer (Tools/Skills) authorizes specific "Skills"—browser control, file system access, or terminal (Shell) commands.[[6]](https://www.iweaver.ai/blog/clawdbot-guide-how-to-deploy-ai-assistant/)

### 3.4 Telegram Integration

Telegram Bot: Search for @BotFather on Telegram, create a /newbot, and paste the Bot Token back into the ClawdBot wizard. Restart: Run clawdbot gateway restart to apply the changes.[[6]](https://www.iweaver.ai/blog/clawdbot-guide-how-to-deploy-ai-assistant/)

**Step-by-step Telegram setup:**

1. Open Telegram, search for @BotFather
2. Send `/newbot`
3. Choose a name (e.g., "PolyTrader Bot")
4. Choose a username (e.g., "polytrader_yourname_bot")
5. Copy the Bot Token

```bash
# Configure Telegram in OpenClaw
openclaw configure --section telegram
# Paste your bot token when prompted
```

Default: channels.telegram.dmPolicy = "pairing". Unknown senders receive a pairing code; messages are ignored until approved (codes expire after 1 hour).[[1]](https://docs.openclaw.ai/channels/telegram)

**Approve your pairing:**
```bash
# List pending pairing codes
openclaw pairing list telegram

# Approve your code
openclaw pairing approve telegram YOUR_CODE
```

### 3.5 Security Configuration (CRITICAL)

This is obviously dangerous. You're giving an AI shell access to a server, API tokens to your email and calendar, and an interface anyone can potentially message. A scan of ClawdBot instances running on VPS providers shows many with the gateway port open with zero authentication. API keys, email access, file permissions — exposed directly to the internet.[[4]](https://lukasniessen.medium.com/clawdbot-setup-guide-how-to-not-get-hacked-63bc951cbd90)

**Mandatory security measures:**

Don't let the agent run arbitrary commands. Explicitly list only what it needs: { "allowedCommands": ["git", "npm", "curl"], "blockedCommands": ["rm -rf", "sudo", "chmod"] } If the agent gets hijacked through prompt injection, it can only execute what you've whitelisted.[[4]](https://lukasniessen.medium.com/clawdbot-setup-guide-how-to-not-get-hacked-63bc951cbd90)

**Add to your OpenClaw config:**
```json
{
  "allowedCommands": ["python3", "curl", "node"],
  "blockedCommands": ["rm -rf", "sudo", "chmod", "chown", "shutdown"],
  "skills": {
    "shell": {
      "sandboxed": true
    }
  }
}
```

Never add ClawdBot to group chats. Every person in that chat can issue commands to your server through the bot.[[4]](https://lukasniessen.medium.com/clawdbot-setup-guide-how-to-not-get-hacked-63bc951cbd90)

Claude Opus 4.5 is specifically recommended because Anthropic trained it to resist prompt injection. That helps, but it's one layer. The command whitelisting, sandboxing, and scoped API tokens are the others.[[4]](https://lukasniessen.medium.com/clawdbot-setup-guide-how-to-not-get-hacked-63bc951cbd90)

---

## 4. TRADING BOT PROMPT FOR OPENCLAW

Save this as your agent's system prompt in OpenClaw:

```
You are PolyTrader, a trading signal generator and executor for 15-minute Bitcoin prediction markets on Polymarket.

## YOUR RESPONSIBILITIES
1. Monitor real-time BTC price data every 10 seconds
2. Calculate technical indicators (RSI, VWAP, momentum)
3. Generate BUY/SELL/HOLD signals based on convergence rules
4. Execute trades via Polymarket API when signals are HIGH confidence
5. Send Telegram notifications for every trade and significant event
6. Log all decisions with full rationale

## DATA INPUTS
- Primary: Chainlink BTC/USD data stream
- Secondary: CryptoCompare API for cross-validation
- Interval: Current 15-minute window in UTC-5

## SIGNAL RULES

**BUY (Bet UP) requires 3 of 4:**
- Price > 15-min VWAP + 0.15%
- RSI between 50-70 (momentum without overbought)
- At least 5 minutes remaining in interval
- Price trending up over last 60 seconds

**SELL (Bet DOWN) requires 3 of 4:**
- Price < 15-min VWAP - 0.15%
- RSI between 30-50 (momentum without oversold)
- At least 5 minutes remaining in interval
- Price trending down over last 60 seconds

**HOLD:** Any other condition

## HARD CONSTRAINTS (NEVER VIOLATE)
- Max $50 per trade (10% of $500 account)
- Max 2 concurrent positions
- No trades within final 3 minutes of interval
- After 10% daily drawdown: STOP and notify human
- After 5 consecutive losses: REDUCE size 50%, notify human
- Daily trade limit: 8 trades maximum

## TELEGRAM NOTIFICATIONS

Send to Telegram for:
- Every trade executed (direction, size, price, rationale)
- Hourly account balance summary
- Any constraint triggered (drawdown, loss streak)
- System errors or data quality issues
- Daily P&L summary at end of session

Format:
🟢 BUY: $50 on UP | Price: $78,450 | RSI: 58 | Conf: HIGH
🔴 SELL: $50 on DOWN | Price: $78,200 | RSI: 42 | Conf: HIGH  
⚪ HOLD: No signal | RSI: 55 | Mixed conditions
⚠️ ALERT: 10% drawdown reached - trading paused
📊 HOURLY: Balance $485 | Today: -$15 | Trades: 3

## LOGGING

Every 60 seconds, append to signals.csv:
timestamp,interval_15m,price,price_change_pct,rsi,vwap_diff,signal,confidence,action_taken

Every trade, append to trades.csv:
timestamp,interval,direction,size,entry_price,rationale,outcome,pnl

## OPERATIONAL MODE

Run continuously. Check price every 10 seconds. Generate signal assessment every 60 seconds. Execute trades only on HIGH confidence signals. Always prioritize capital preservation over profit maximization.

If uncertain, HOLD. Inaction is acceptable. Bad trades are not.
```

---

## 5. FILE STRUCTURE

```
polymarket-bot/
├── config/
│   ├── openclaw.json          # OpenClaw configuration
│   ├── settings.yaml          # API keys, thresholds
│   └── constraints.yaml       # Hard limits (code-enforced)
├── data/
│   ├── raw/                   # Incoming price data
│   │   └── btc_prices.csv
│   ├── signals/               # Generated signals
│   │   └── signals.csv
│   └── trades/                # Executed trades
│       └── trades.csv
├── src/
│   ├── data_ingestion.py      # Fetch from Chainlink/CryptoCompare
│   ├── indicators.py          # RSI, VWAP, momentum calculations
│   ├── smart_money.py         # Track top Polymarket traders
│   ├── signal_generator.py    # Convergence logic
│   ├── risk_manager.py        # Position sizing, limits
│   ├── polymarket_api.py      # Polymarket execution
│   ├── telegram_notify.py     # Notification helper
│   └── main.py                # Orchestration loop
├── skills/
│   └── trading_skill.js       # OpenClaw custom skill
├── logs/
│   └── bot.log                # Operational log
├── tests/
│   └── test_signals.py        # Backtest framework
└── README.md
```

---

## 6. TELEGRAM NOTIFICATION INTEGRATION

### 6.1 OpenClaw Telegram Tool Usage

Tool: telegram with sendMessage action (to, content, optional mediaUrl, replyToMessageId, messageThreadId). Tool: telegram with react action (chatId, messageId, emoji). Tool: telegram with deleteMessage action (chatId, messageId).[[1]](https://docs.openclaw.ai/channels/telegram)

### 6.2 Notification Templates

```python
# telegram_notify.py

TEMPLATES = {
    "trade_buy": "🟢 BUY: ${size} on UP\n📈 Price: ${price}\n📊 RSI: {rsi} | VWAP diff: {vwap_pct}%\n⏰ Interval: {interval}\n💡 Confidence: {confidence}",
    
    "trade_sell": "🔴 SELL: ${size} on DOWN\n📉 Price: ${price}\n📊 RSI: {rsi} | VWAP diff: {vwap_pct}%\n⏰ Interval: {interval}\n💡 Confidence: {confidence}",
    
    "trade_closed": "✅ CLOSED: {direction}\n💰 P&L: ${pnl} ({pnl_pct}%)\n📊 Entry: ${entry} → Exit: ${exit}\n⏱️ Duration: {duration}",
    
    "hourly_summary": "📊 HOURLY UPDATE\n💰 Balance: ${balance}\n📈 Today P&L: ${daily_pnl}\n🔢 Trades: {trade_count}\n✅ Wins: {wins} | ❌ Losses: {losses}",
    
    "alert_drawdown": "⚠️ DRAWDOWN ALERT\n📉 Account down {drawdown}% today\n🛑 Trading PAUSED for 4 hours\n👤 Human review required",
    
    "alert_loss_streak": "⚠️ LOSS STREAK: {streak} consecutive\n📉 Reducing position size 50%\n💰 New max: ${new_max}\n👤 Review recommended",
    
    "daily_summary": "📋 DAILY SUMMARY\n📅 {date}\n💰 Starting: ${start_balance}\n💰 Ending: ${end_balance}\n📈 P&L: ${pnl} ({pnl_pct}%)\n🔢 Total trades: {trades}\n✅ Win rate: {win_rate}%\n🏆 Best trade: ${best}\n💀 Worst trade: ${worst}"
}
```

---

## 7. AWS INFRASTRUCTURE

### 7.1 Instance Specifications

| Component | Specification | Purpose |
|-----------|-------------|---------|
| Instance | t3.small (2 vCPU, 2 GiB) | Run OpenClaw + trading bot |
| OS | Ubuntu Server 24.04 LTS | Stable, Node.js 22 support |
| Region | us-east-1 | Low latency to APIs |
| Storage | 20 GB SSD | Logs and data |
| Security | SSH only, My IP restricted | Minimal attack surface |
| Key Pair | RSA, .pem format | For Cursor/SSH access |

### 7.2 Initial Server Setup

```bash
# After SSH into your t3.small instance
sudo apt update && sudo apt upgrade -y

# Install Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version  # Should be v22.x.x

# Install OpenClaw
sudo npm install -g openclaw@latest

# Run onboarding
openclaw onboard --install-daemon

# During onboard:
# - Select Anthropic API Key for auth
# - Enable Telegram channel
# - Paste your Telegram bot token
# - Install as background service: YES

# Install Python for your trading scripts
sudo apt install -y python3 python3-pip python3-venv
```

### 7.3 Security Hardening

```bash
# Firewall - only allow SSH from your IP
sudo ufw allow from YOUR_IP to any port 22 proto tcp
sudo ufw enable

# Disable password auth
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PermitRootLogin no
sudo systemctl reload ssh

# Keep OpenClaw gateway on localhost only
# In ~/.openclaw/openclaw.json:
{
  "gateway": {
    "host": "127.0.0.1",
    "port": 18789
  }
}
```

---

## 8. IMPLEMENTATION PHASES

### Phase 0: Observation (Week 1)
- [ ] Watch Polymarket BTC Up/Down markets manually
- [ ] Note price patterns, spread behavior, resolution mechanics
- [ ] Identify 5-10 top traders via "Top Holders" section
- [ ] Document observations in trading journal
- [ ] Set up Telegram bot via @BotFather

### Phase 1: Infrastructure (Week 2)
- [ ] Deploy AWS t3.small instance
- [ ] Install and configure OpenClaw
- [ ] Connect Telegram channel and verify pairing
- [ ] Set up data logging (10-second intervals)
- [ ] Test Telegram notifications

### Phase 2: Signal Development (Week 3)
- [ ] Implement RSI, VWAP, momentum calculations
- [ ] Build signal convergence logic
- [ ] Create OpenClaw trading skill
- [ ] Paper trade for 5 days, log all signals
- [ ] Verify Telegram alerts working

### Phase 3: Risk & Execution (Week 4)
- [ ] Implement position sizing and hard limits
- [ ] Connect Polymarket API (read-only first)
- [ ] Test order placement with $5
- [ ] Verify fill reporting and reconciliation
- [ ] Test all failure mode responses

### Phase 4: Live Trading (Week 5+)
- [ ] Trade with $10 positions for 1 week
- [ ] Monitor via Telegram throughout day
- [ ] Verify signal quality, adjust thresholds
- [ ] Gradually increase to $50 max position
- [ ] Daily review, weekly strategy refinement

---

## 9. DAILY OPERATIONS

### Pre-Session Checklist
- [ ] SSH into server, run `openclaw doctor`
- [ ] Verify Telegram bot responding
- [ ] Check Chainlink data feed active
- [ ] Confirm account balance on Polymarket
- [ ] Risk limits reset for day

### During Session
- [ ] Monitor Telegram for trade notifications
- [ ] Respond to any ALERT messages
- [ ] Check hourly summaries
- [ ] Log any manual interventions

### Post-Session Review
- [ ] Request daily summary via Telegram
- [ ] Review all trades in trades.csv
- [ ] Identify any limit breaches
- [ ] Update strategy notes
- [ ] Back up data files

---

## 10. FAILURE MODE RESPONSES

| Scenario | Detection | Response | Telegram Alert |
|----------|-----------|----------|----------------|
| API timeout | 5s+ latency | Retry 3x, then pause 60s | ⚠️ Data feed timeout |
| Data gap | 30s+ missing data | Signal HOLD, alert human | ⚠️ Data gap detected |
| Position oversize | >10% account | Reject order, alert | 🛑 Order rejected: size limit |
| Drawdown >10% | Real-time calc | Pause 4 hours, review | ⚠️ DRAWDOWN ALERT |
| Consecutive losses | 5 in a row | Reduce size 50%, review | ⚠️ LOSS STREAK |
| OpenClaw crash | Gateway down | Auto-restart via systemd | 🛑 Bot restarted |
| Pre-resolution | <3 min to close | No new positions | ℹ️ Too close to resolution |

---

## 11. KEY INSIGHTS FROM RESEARCH

### From Successful Cases (247% return)
- Time-boxed: 24-hour experiment with hard stop
- Conservative risk: "protect principal at all costs"
- Multi-signal: sentiment + technical + pattern analysis
- Self-correcting: bot reviewed its own operations

### From Failure Cases ($250K wipeout)
- Unsupervised: no human oversight during trading
- Over-complex: 25 strategies, 3,000 reports
- No limits: allowed to compound errors
- Speed without brakes: 1,700 trades in 3 hours

### Our Differentiation
- Hardcoded limits (code-enforced, not prompt-dependent)
- OpenClaw's sandboxing for shell operations
- Telegram alerts keep human in the loop
- Start small ($5 → $10 → $50), prove edge, scale gradually

---

## 12. SECURITY WARNINGS

Security researchers have warned that this extensible architecture introduces supply chain risks, as compromised or poorly audited modules could enable privilege escalation or arbitrary code execution. Due to these concerns, security consultants have recommended operating OpenClaw exclusively in isolated sandbox environments and avoiding connections to production systems or accounts containing sensitive credentials.[[3]](https://en.wikipedia.org/wiki/OpenClaw)

**Mitigations implemented:**
- Command whitelist enabled
- Sandbox mode for shell operations
- API keys have minimal permissions (no withdrawal)
- Gateway bound to localhost only
- SSH key-only authentication
- UFW firewall restricting access

---

## 13. RESOURCES & REFERENCES

- **OpenClaw Docs:** https://docs.openclaw.ai
- **OpenClaw GitHub:** https://github.com/openclaw/openclaw
- **Telegram Channel Docs:** https://docs.openclaw.ai/channels/telegram
- **Resolution Source:** https://data.chain.link/streams/btc-usd
- **Target Market:** https://polymarket.com/event/btc-updown-15m-1769939100
- **AWS Free Tier:** https://aws.amazon.com/free/
- **Polymarket Docs:** https://docs.polymarket.com/

---

## 14. QUICK REFERENCE COMMANDS

```bash
# OpenClaw status
openclaw status --all
openclaw doctor

# Gateway management
openclaw gateway start
openclaw gateway restart
openclaw gateway logs

# Telegram pairing
openclaw pairing list telegram
openclaw pairing approve telegram CODE

# Configuration
openclaw configure --section telegram

# Send test message
openclaw message send --to TELEGRAM_CHAT_ID --message "Test from PolyTrader"

# View logs
tail -f ~/.openclaw/logs/gateway.log
```

---

**Document Version:** 2.0  
**Last Updated:** 2026-02-01  
**Engine:** OpenClaw (formerly ClawdBot)  
**Next Review:** After Phase 2 completion

---

*Remember: The goal is not to maximize returns, but to survive long enough for edge to compound. Conservation of capital is the first priority. OpenClaw is powerful but requires careful configuration—treat it as a loaded weapon, not a toy.*
```

---

This refined guide integrates OpenClaw as the execution engine with full Telegram notification support. The key additions include:

1. **OpenClaw architecture explanation** and why it's suited for this use case
2. **Complete Telegram setup** with pairing workflow
3. **Security hardening** based on documented vulnerabilities
4. **Trading prompt** specifically designed for OpenClaw's agent framework
5. **Notification templates** for all trade events
6. **Updated file structure** including OpenClaw skills directory
7. **Quick reference commands** for daily operations

The document maintains all the hard constraints and metrics from Kimi's original while adding the practical OpenClaw implementation details you need to get running.

---
Learn more:
1. [OpenClaw’s AI assistants are now building their own social network](https://techcrunch.com/2026/01/30/openclaws-ai-assistants-are-now-building-their-own-social-network/)
2. [Telegram - OpenClaw](https://docs.openclaw.ai/channels/telegram)
3. [Clawdbot/Moltbot/OpenClaw is cool, but it gets pricey fast - Fast Company](https://www.fastcompany.com/91484506/what-is-clawdbot-moltbot-openclaw)
4. [Getting Started with Clawdbot: The Complete Step-by-Step Guide - DEV Community](https://dev.to/ajeetraina/getting-started-with-clawdbot-the-complete-step-by-step-guide-2ffj)
5. [OpenClaw - Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
6. [Getting Started with Clawdbot](https://www.ajeetraina.com/getting-started-with-clawdbot/)
7. [OpenClaw Complete Guide 2026: The Clawdbot → Moltbot ...](https://www.nxcode.io/resources/news/openclaw-complete-guide-2026)
8. [ClawdBot: Setup Guide + How to NOT Get Hacked | by Lukas Niessen | Jan, 2026 | Medium](https://lukasniessen.medium.com/clawdbot-setup-guide-how-to-not-get-hacked-63bc951cbd90)
9. [How to Get Clawdbot/Moltbot/OpenClaw Set Up in an Afternoon](https://amankhan1.substack.com/p/how-to-get-clawdbotmoltbotopenclaw)
10. [How to Set Up Clawdbot — Step by Step guide to setup a personal bot | by Nikhil | Neural Notions | Jan, 2026 | Medium](https://medium.com/modelmind/how-to-set-up-clawdbot-step-by-step-guide-to-setup-a-personal-bot-3e7957ed2975)
11. [OpenClaw — Personal AI Assistant](https://openclaw.ai/)
12. [The Ultimate ClawdBot/Moltbot Guide: How to Safely Deploy Your First Autonomous AI Assistant | iWeaver AI](https://www.iweaver.ai/blog/clawdbot-guide-how-to-deploy-ai-assistant/)
13. [Moltbook, a social network where AI agents hang together, may be 'the most interesting place on the internet right now' | Fortune](https://fortune.com/2026/01/31/ai-agent-moltbot-clawdbot-openclaw-data-privacy-security-nightmare-moltbook-social-network/)
14. [Clawdbot: Your Personal AI Butler is Here | by David Lee | Jan, 2026 | Level Up Coding](https://levelup.gitconnected.com/clawdbot-your-personal-ai-butler-is-here-012fc4f813e5)
15. [GitHub - openclaw/openclaw: Your own personal AI assistant. Any OS. Any Platform. The lobster way. 🦞](https://github.com/clawdbot/clawdbot)
16. [ClawdBot: The Complete Guide to Everything You Can Do ...](https://peerlist.io/tanayvasishtha/articles/clawdbot-the-complete-guide-to-everything-you-can-do-withit)
17. [OpenClaw (Moltbot/Clawdbot) Use Cases and Security 2026](https://research.aimultiple.com/moltbot/)
18. [Build Your AI Assistant on Telegram with OpenClaw - MiniMax API Docs](https://platform.minimax.io/docs/solutions/moltbot)
19. [From Moltbot to OpenClaw: When the Dust Settles, the Project Survived - DEV Community](https://dev.to/sivarampg/from-moltbot-to-openclaw-when-the-dust-settles-the-project-survived-5h6o)
20. [ClawdBot Review & Setup Guide](https://uxwritinghub.com/clawdbot-review-setup-guide-the-ux-designers)