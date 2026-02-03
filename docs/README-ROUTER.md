# OpenClaw Tiered Model Router

A cost-efficient multi-model routing system for OpenClaw that automatically selects the right AI model for each task.

## Architecture

Similar to Cursor's auto mode, this router implements a tiered strategy:

1. **Gemini Flash (Default)** - Fast, cheap model for 80% of interactions
   - Simple queries, greetings, basic responses
   - Cost: ~$0.000075 per 1K tokens
   - Speed: Very fast response times

2. **Claude Opus (Escalation)** - Reserved for complex tasks
   - Coding, debugging, complex analysis
   - Trading decisions, risk assessment
   - Cost: ~$0.003 per 1K tokens
   - Used only when complexity is detected

## Features

- **Automatic routing** based on message content and complexity
- **Cost tracking** - Monitor spending across both models
- **Rate limit handling** - Prevents API exhaustion
- **Fallback logic** - If one model fails, tries the other
- **Usage statistics** - Track calls, escalations, costs

## Setup

1. **Install dependencies:**
   ```bash
   # Router uses Node.js built-in modules (https, http)
   # No additional npm packages required
   ```

2. **Set API keys:**
   ```bash
   export GEMINI_API_KEY='your-gemini-api-key'
   export ANTHROPIC_API_KEY='your-anthropic-api-key'
   ```

3. **Run setup script:**
   ```bash
   ./openclaw-router-setup.sh
   ```

## Usage

### Basic Usage

```javascript
const TieredModelRouter = require('./openclaw-model-router');

const router = new TieredModelRouter({
  geminiApiKey: process.env.GEMINI_API_KEY,
  claudeApiKey: process.env.ANTHROPIC_API_KEY
});

// Simple query (uses Gemini)
const result1 = await router.route('Hello, how are you?');
console.log(result1.text); // Response from Gemini Flash

// Complex query (uses Claude)
const result2 = await router.route('Can you help me debug this trading bot code?');
console.log(result2.text); // Response from Claude

// Get statistics
const stats = router.getStats();
console.log(stats);
// {
//   geminiCalls: 1,
//   claudeCalls: 1,
//   escalations: 1,
//   fallbacks: 0,
//   costs: { gemini: 0.0001, claude: 0.05, total: 0.0501 }
// }
```

### Integration with OpenClaw

The router can be integrated into OpenClaw's agent system by:

1. **Creating a custom skill** that uses the router
2. **Modifying agent prompts** to route through the router
3. **Using as a middleware** in OpenClaw's message processing

Example OpenClaw skill integration:

```javascript
// ~/.openclaw/workspace/skills/model-router-skill.js
const TieredModelRouter = require('./model-router/openclaw-model-router');

const router = new TieredModelRouter();

module.exports = {
  name: 'model-router',
  description: 'Routes messages to appropriate AI model',
  
  async execute(message, context) {
    const result = await router.route(message, context.systemPrompt, context);
    return {
      text: result.text,
      model: result.model,
      tokens: result.tokens
    };
  }
};
```

## Routing Logic

The router automatically selects models based on:

1. **Explicit requests** - `@claude` or `@gemini` in message
2. **Keywords** - Coding, trading, complex analysis terms
3. **Message length** - Long messages (>500 chars) escalate to Claude
4. **Task type** - Code tasks, trading decisions → Claude

### Escalation Triggers

Messages escalate to Claude if they contain:
- Coding keywords: `code`, `debug`, `fix`, `error`, `bug`, `implement`
- Trading keywords: `trade`, `signal`, `position`, `risk`, `drawdown`
- Complexity indicators: Long messages, analysis requests

## Cost Optimization

- **Default to Gemini** - 80% of queries use cheap Gemini Flash
- **Reserve Claude** - Only for tasks that need deep reasoning
- **Track spending** - Monitor costs in real-time
- **Rate limiting** - Prevent API exhaustion

## Rate Limits

- **Gemini Flash**: 100 calls per minute
- **Claude Opus**: 50 calls per hour

If rate limits are hit, the router automatically falls back to the other model.

## Statistics

Track usage with `router.getStats()`:

```javascript
{
  geminiCalls: 45,
  claudeCalls: 5,
  escalations: 5,
  fallbacks: 2,
  costs: {
    gemini: 0.001,
    claude: 0.15,
    total: 0.151
  },
  rateLimits: {
    gemini: { calls: 45, limit: 100 },
    claude: { calls: 5, limit: 50 }
  }
}
```

## Configuration

Edit `openclaw-router-config.json` to customize:

- Model selection
- Escalation keywords
- Rate limits
- Cost budgets

## Troubleshooting

**Router not selecting Claude:**
- Check that keywords are in the message
- Verify message length exceeds threshold
- Try explicit `@claude` request

**API errors:**
- Verify API keys are set correctly
- Check rate limits haven't been exceeded
- Ensure network connectivity

**High costs:**
- Review escalation logic
- Adjust keyword lists
- Increase complexity thresholds

## Example: Trading Bot Integration

For the Polymarket trading bot, the router would:

- **Gemini Flash**: Handle routine price checks, simple status updates
- **Claude Opus**: Make trading decisions, analyze risk, debug issues

```javascript
// Trading decision (escalates to Claude)
const signal = await router.route(
  'Analyze current BTC price momentum and RSI. Should I enter a position?',
  'You are a trading bot assistant...'
);

// Simple status (uses Gemini)
const status = await router.route('What is the current BTC price?');
```

## License

Part of the Polymarket Trading Bot project.
