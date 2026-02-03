# How to Switch Models in OpenClaw

## Current Setup

Your OpenClaw is currently configured with:
- **Provider**: Anthropic (Claude)
- **Profile**: `anthropic:default`
- **Model**: Not explicitly set (uses default)

## Available Models

### Claude Models (Anthropic)
- `claude-3-5-sonnet-20241022` - Latest Claude (recommended)
- `claude-3-opus-20240229` - Claude Opus
- `claude-3-sonnet-20240229` - Claude Sonnet
- `claude-3-haiku-20240307` - Claude Haiku (fastest, cheapest)

### OpenAI Models (if configured)
- `gpt-4-turbo-preview` - GPT-4 Turbo
- `gpt-4` - GPT-4
- `gpt-3.5-turbo` - GPT-3.5 Turbo

**Note**: GPT-5.2 doesn't exist yet. Latest is GPT-4. If you meant Claude 3.5 Sonnet, that's the latest Claude model.

## Method 1: Using OpenClaw Configure Wizard

```bash
# Run the configure wizard
openclaw configure

# Select "model" section when prompted
# Follow the prompts to set your model
```

## Method 2: Direct Config Edit

Edit `~/.openclaw/openclaw.json` and add model configuration:

```json
{
  "agents": {
    "defaults": {
      "workspace": "/home/ubuntu/.openclaw/workspace",
      "maxConcurrent": 4,
      "model": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022"
      }
    }
  }
}
```

## Method 3: Using Config Command

```bash
# Set model for default agent
openclaw config set agents.defaults.model.provider "anthropic"
openclaw config set agents.defaults.model.model "claude-3-5-sonnet-20241022"
```

## Method 4: Per-Agent Configuration

If you have a specific agent, you can set the model in the agent's config file:

```bash
# Edit agent config
nano ~/.openclaw/agents/main/agent/config.json
```

Add:
```json
{
  "model": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022"
  }
}
```

## Switching to Claude 3.5 Sonnet (Latest)

```bash
# Quick method - edit config directly
nano ~/.openclaw/openclaw.json
```

Add or update the agents section:
```json
"agents": {
  "defaults": {
    "workspace": "/home/ubuntu/.openclaw/workspace",
    "maxConcurrent": 4,
    "model": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    }
  }
}
```

Then restart:
```bash
openclaw gateway restart
```

## Switching to OpenAI (if you have API key)

1. Add OpenAI API key:
```bash
openclaw configure --section auth
# Select OpenAI, enter your API key
```

2. Set model:
```bash
openclaw config set agents.defaults.model.provider "openai"
openclaw config set agents.defaults.model.model "gpt-4-turbo-preview"
```

3. Restart:
```bash
openclaw gateway restart
```

## Verify Model

```bash
# Check current config
openclaw config get agents.defaults.model

# Check status
openclaw status
```

## Troubleshooting

**Model not found:**
- Verify API key is set correctly
- Check model name spelling
- Ensure provider matches (anthropic vs openai)

**Changes not taking effect:**
- Restart gateway: `openclaw gateway restart`
- Check logs: `openclaw gateway logs`

**Want to use a different model per conversation:**
- Set model in agent's system prompt
- Or use model selection in message (if supported)
