# OpenClaw Rate Limit Fix - Summary

## What Was Wrong

1. **Model**: Using `claude-opus-4-5` - **$15 per 1M tokens** (most expensive)
2. **Concurrency**: 4 main agents + 8 subagents = **12 concurrent requests**
3. **Context**: Loading large files (AGENTS.md, SOUL.md, MEMORY.md) every session
4. **Result**: Hitting 30,000 tokens/minute limit

## What I Fixed

✅ **Switched to Claude Sonnet** - `claude-3-5-sonnet-20241022` ($3/1M tokens)
   - **5x cheaper** than Opus
   - Still very capable for most tasks

✅ **Reduced concurrency** - 2 main + 2 subagents (was 4+8)
   - **75% reduction** in concurrent requests
   - Much lower token usage

## Next Steps

1. **Restart OpenClaw gateway:**
   ```bash
   openclaw gateway restart
   ```

2. **Monitor usage:**
   ```bash
   # Check logs for rate limit errors
   openclaw gateway logs | grep -i "rate\|429"
   ```

3. **If still hitting limits, further optimize:**

   **Option A: Switch to Haiku (60x cheaper)**
   ```bash
   # Edit config
   nano ~/.openclaw/openclaw.json
   # Change model to: "anthropic/claude-3-haiku-20240307"
   ```

   **Option B: Reduce to 1 agent only**
   ```bash
   openclaw config set agents.defaults.maxConcurrent 1
   openclaw config set agents.defaults.subagents.maxConcurrent 1
   ```

   **Option C: Optimize context files**
   - Shorten AGENTS.md, SOUL.md
   - Don't load MEMORY.md in subagents
   - Use shorter system prompts

## Cost Comparison

| Model | Cost per 1M tokens | Speed | Use Case |
|-------|-------------------|-------|----------|
| **Opus 4.5** (old) | $15 | Slow | Complex reasoning |
| **Sonnet 3.5** (current) | $3 | Fast | Most tasks ✅ |
| **Haiku 3** | $0.25 | Very Fast | Simple tasks |

## Expected Results

- **Token usage**: ~75% reduction (fewer concurrent agents)
- **Cost**: ~80% reduction (Sonnet vs Opus)
- **Rate limits**: Should stay under 30k/min with 2+2 agents

## If Still Rate Limited

1. Check actual token usage in response headers
2. Add delays between requests
3. Further reduce concurrent agents
4. Consider using Gemini Flash for simple queries (tiered router)

## Rollback

If you need to go back:
```bash
cp ~/.openclaw/openclaw.json.backup ~/.openclaw/openclaw.json
openclaw gateway restart
```
