# OpenClaw Cost & Rate Limit Optimization

## Current Issues

1. **Using Claude Opus 4.5** - Most expensive model ($15 per 1M input tokens)
2. **8 concurrent subagents** - Each sends full context
3. **Large context files** - Loading multiple files every session
4. **No rate limiting** - Hitting 30k tokens/min limit

## Solutions

### 1. Switch to Cheaper Model (IMMEDIATE FIX)

**Current:** `claude-opus-4-5` ($15/1M tokens)
**Switch to:** `claude-3-5-sonnet-20241022` ($3/1M tokens) - **5x cheaper**

Or even cheaper: `claude-3-haiku-20240307` ($0.25/1M tokens) - **60x cheaper**

### 2. Reduce Concurrent Agents

**Current:** 4 main + 8 subagents = up to 12 concurrent requests
**Recommended:** 2 main + 2 subagents = max 4 concurrent

### 3. Optimize Context Loading

Reduce what gets loaded every session:
- Don't load MEMORY.md in every subagent
- Only load essential files
- Use shorter system prompts

### 4. Add Rate Limiting

Implement delays between requests to stay under 30k tokens/min.
