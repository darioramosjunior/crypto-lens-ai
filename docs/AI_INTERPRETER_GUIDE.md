# AI Interpreter Module - OpenRouter Integration Guide

## Overview

The AI Interpreter module integrates **Large Language Models (LLMs)** via OpenRouter API to provide intelligent market analysis and insights. It automatically analyzes cryptocurrency market data summaries and sends AI-powered interpretations to Discord.

**Key Features:**
- 🤖 LLM-powered market analysis using OpenRouter API
- 📊 Context-aware interpretations (hourly, daily, anomalies)
- 🔄 Automatic integration with existing data pipeline
- 📢 Discord webhook integration for real-time insights
- 🛡️ Graceful error handling and fallback behavior
- 📝 Comprehensive logging for debugging

## Setup Instructions

### 1. Get OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Sign up for a free account
3. Navigate to **API Keys** section
4. Create a new API key
5. Copy the key (you'll use it in the next step)

**Note:** OpenRouter provides access to many models including:
- Meta Llama 2 70B (free/cheap)
- Mistral 7B
- Nous Hermes 2
- OpenAI GPT-3.5/GPT-4 (if you have credits)
- Anthropic Claude

### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_api_key_here

# Optional: Specify which model to use (defaults to meta-llama/llama-2-70b-chat)
OPENROUTER_MODEL=meta-llama/llama-2-70b-chat

# Discord webhook for AI insights
AI_INSIGHTS_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### 3. Update Requirements (if needed)

The AI interpreter uses only standard packages (`requests`, `pydantic`). No additional dependencies needed!

```bash
# These should already be in requirements.txt
requests
python-dotenv
pydantic
```

### 4. Test the Setup

Run the AI interpreter in standalone mode:

```bash
python ai_interpreter.py
```

You should see a test interpretation sent to your Discord channel.

## Usage Patterns

### Pattern 1: Standalone AI Interpretation

```python
from ai_interpreter import interpret_and_send

# Create market data summary
data_summary = """
BTC/USDT (1h): +2.5%, RSI: 65, Volume: +15%
ETH/USDT (1h): +1.8%, RSI: 58, Volume: stable
Market Breadth: 67% of coins trading green
"""

# Get LLM interpretation and send to Discord
success = interpret_and_send(
    data_summary=data_summary,
    context="hourly market analysis",
    title="Hourly Crypto Market AI Analysis"
)

print(f"Interpretation sent: {success}")
```

### Pattern 2: Custom Model Selection

```python
from ai_interpreter import call_openrouter_api

# Use a specific model
interpretation = call_openrouter_api(
    data_summary="BTC +2.5%, volume surge suggests accumulation",
    context="technical analysis",
    model="mistralai/mistral-7b"  # Use Mistral instead of Llama
)
```

### Pattern 3: Integration with Existing Pipeline

The AI interpreter automatically runs in the pipeline after market analysis scripts:

```bash
# Pipeline execution order:
1. coin_data_collector.py
2. hourly_fetch_and_pulse.py
3. daily_fetch_and_pulse.py
4. market_breadth.py
5. oi_change_screener.py
6. ai_interpreter.py          # <- Runs here
7. pipeline_observability.py
```

### Pattern 4: Get Interpretation Only (No Discord Send)

```python
from ai_interpreter import call_openrouter_api

# Get interpretation without sending to Discord
interpretation = call_openrouter_api(
    data_summary="BTC/USDT data here",
    context="daily analysis"
)

if interpretation:
    print(interpretation)
    # Use it for other purposes (logging, storage, etc.)
```

## Integration with Data Pipeline

### Capturing Data Summaries

To send AI interpretations of your analysis, create summaries from existing components:

#### From Hourly Analysis:
```python
# In hourly_fetch_and_pulse.py, after generating market_pulse.png
from ai_interpreter import interpret_and_send

hourly_summary = f"""
Top Gainers (1h):
{top_gainers_text}

Top Losers (1h):
{top_losers_text}

Market Sentiment: {market_sentiment}
Volume Activity: {volume_activity}
"""

interpret_and_send(
    data_summary=hourly_summary,
    context="hourly market pulse",
    title="Hourly Market AI Insights"
)
```

#### From Daily Analysis:
```python
# In daily_fetch_and_pulse.py
daily_summary = f"""
24h Market Summary:
- BTC: {btc_change}%
- ETH: {eth_change}%
- Top 5 Gainers: {top_gainers}
- Top 5 Losers: {top_losers}
- Market Cap: {market_cap_trend}
"""

interpret_and_send(
    data_summary=daily_summary,
    context="daily market analysis",
    title="Daily Market AI Analysis"
)
```

#### From Market Breadth:
```python
# In market_breadth.py
breadth_summary = f"""
Market-Wide Metrics:
- Advancing coins: {advancing_count}
- Declining coins: {declining_count}
- Breadth ratio: {breadth_ratio}
- Sentiment: {sentiment}
- Trend strength: {trend_strength}
"""

interpret_and_send(
    data_summary=breadth_summary,
    context="market breadth analysis"
)
```

#### From OI Screener:
```python
# In oi_change_screener.py
oi_summary = f"""
Open Interest Analysis:
- Top OI gainers: {top_gainers_oi}
- Top OI losers: {top_losers_oi}
- OI trend: {oi_trend}
- Notable positions: {notable_positions}
"""

interpret_and_send(
    data_summary=oi_summary,
    context="open interest anomalies",
    title="OI Change Alert - AI Insight"
)
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `meta-llama/llama-2-70b-chat` | LLM model to use |
| `AI_INSIGHTS_WEBHOOK` | (optional) | Discord webhook for insights |

### Supported Models & Pricing

**Free/Cheap Options:**
```
meta-llama/llama-2-70b-chat      # Free tier available
openrouter/auto                    # Automatically picks cheapest
```

**Mid-Range:**
```
mistralai/mistral-7b
nousresearch/nous-hermes-2-mistral-7b-dpo
```

**Premium:**
```
openai/gpt-3.5-turbo
openai/gpt-4
anthropic/claude-2
```

Check [OpenRouter Models](https://openrouter.ai/models) for current pricing.

## API Reference

### `interpret_and_send()`

Send data to LLM and post interpretation to Discord.

```python
def interpret_and_send(
    data_summary: str,              # Market data to interpret
    context: str = "",              # "hourly", "daily", "anomaly", etc.
    webhook_url: Optional[str] = None,  # Discord webhook (uses env default if None)
    title: str = "AI Market Interpretation"  # Discord message title
) -> bool:
    """
    Returns True if successful, False otherwise
    """
```

### `call_openrouter_api()`

Get LLM interpretation without Discord send.

```python
def call_openrouter_api(
    data_summary: str,              # Data to interpret
    context: str = "",              # Analysis context
    model: Optional[str] = None,    # Model to use (env default if None)
    max_tokens: int = 500           # Response length limit
) -> Optional[str]:
    """
    Returns interpretation string or None on error
    """
```

### `create_user_prompt()`

Generate user prompt for LLM.

```python
def create_user_prompt(
    data_summary: str,              # Market data summary
    context: str = ""               # Additional context
) -> str:
    """
    Returns formatted prompt string
    """
```

## Error Handling

The AI interpreter handles errors gracefully:

### Missing API Key
```
[WARNING] OPENROUTER_API_KEY not set. AI interpretation will be disabled.
[WARNING] OPENROUTER_API_KEY not configured. Skipping AI interpretation.
```

### Missing Discord Webhook
```
[WARNING] AI_INSIGHTS_WEBHOOK not set. AI interpretations will not be sent to Discord.
[WARNING] No Discord webhook URL provided for AI interpretation
```

### API Failures
- **Timeout**: Logged and skipped gracefully
- **Invalid API Key**: Returns None, continues pipeline
- **Rate Limit**: Returns None, check OpenRouter dashboard
- **Network Error**: Logged and skipped

All errors are logged to `/var/log/crypto-lens/ai_interpreter.log`

## Testing

Run tests for the AI interpreter:

```bash
# Run AI interpreter tests
pytest tests/test_ai_interpreter.py -v

# Run with coverage
pytest tests/test_ai_interpreter.py -v --cov=ai_interpreter

# Run specific test
pytest tests/test_ai_interpreter.py::TestAIInterpreterPrompts -v

# Integration tests (require live API)
pytest tests/test_ai_interpreter.py -v -m integration
```

## Example Output

### Discord Message
```
**Hourly Crypto Market AI Analysis** [2026-05-10 14:30:00]

Bitcoin is showing strength with a +2.5% hourly gain and elevated RSI at 65, 
indicating potential overbought conditions. Volume surge of 15% suggests strong 
buying pressure and accumulation phase. However, watch for profit-taking around 
resistance levels.

Ethereum follows with +1.8% gains but more stable volume, suggesting consolidation. 
With 67% of altcoins trading green, market sentiment is bullish overall.

**Recommendation:** Monitor RSI divergence for potential pullback opportunities.
```

## Troubleshooting

### "OPENROUTER_API_KEY not configured"
- **Cause:** Missing or invalid API key in .env
- **Fix:** Add valid `OPENROUTER_API_KEY` to .env and restart

### "OpenRouter API error: 401"
- **Cause:** Invalid API key
- **Fix:** Verify API key on [OpenRouter dashboard](https://openrouter.ai)

### "OpenRouter API request timed out"
- **Cause:** Network issue or server overload
- **Fix:** Check internet connection, retry later, or try different model

### "Failed to parse OpenRouter response"
- **Cause:** Unexpected API response format
- **Fix:** Check logs for details, verify model name is correct

### Discord message not received
- **Cause:** Invalid webhook URL or permission issues
- **Fix:** Verify Discord webhook URL, check channel permissions

## Advanced Configuration

### Custom System Prompt

Edit the LLM behavior by modifying `create_system_prompt()` in [ai_interpreter.py](../ai_interpreter.py):

```python
def create_system_prompt() -> str:
    """Customize LLM behavior here"""
    return """You are a conservative crypto analyst focused on risk management.
    Emphasize downside protection and volatility in your analysis..."""
```

### Custom Response Formatting

Modify Discord message format in `interpret_and_send()`:

```python
# Change formatting
discord_message = f"""
📊 **{title}** 
🕐 {timestamp_str}

{interpretation}

⚠️ *Not financial advice. DYOR.*
"""
```

### Different Models for Different Contexts

```python
# Use GPT-4 for anomalies, Llama for regular analysis
if "anomaly" in context.lower():
    model = "openai/gpt-4"
else:
    model = "meta-llama/llama-2-70b-chat"

interpretation = call_openrouter_api(
    data_summary=data_summary,
    context=context,
    model=model
)
```

## Performance & Cost

### Typical Costs (via OpenRouter)
- **Meta Llama 2 70B:** ~$0.0001 per interpretation
- **Mistral 7B:** ~$0.00007 per interpretation  
- **GPT-3.5-turbo:** ~$0.0015 per interpretation
- **GPT-4:** ~$0.03 per interpretation

### Running Every Hour
```
Meta Llama 2:    ~$0.74/month  (24 calls/day)
GPT-3.5:         ~$10.95/month
GPT-4:           ~$219/month
```

### Optimization Tips
1. Use free/cheap models for routine analysis
2. Use premium models for critical decisions
3. Adjust `max_tokens` to reduce costs
4. Cache prompts when possible

## Security Notes

1. **API Key Security:**
   - Never commit `.env` to git
   - Use `.gitignore` to exclude environment files
   - Rotate keys periodically

2. **Data Privacy:**
   - OpenRouter logs API calls
   - Don't send sensitive data in summaries
   - Review OpenRouter privacy policy

3. **Rate Limiting:**
   - Check OpenRouter dashboard for usage
   - Implement delays between high-frequency calls
   - Use cheaper models for testing

## Next Steps

1. ✅ Get OpenRouter API key
2. ✅ Add to `.env` file
3. ✅ Add Discord webhook URL
4. ✅ Test with `python ai_interpreter.py`
5. ✅ Integrate with your pipeline
6. ✅ Monitor logs and Discord for insights

## Support & Resources

- **OpenRouter Docs:** https://openrouter.ai/docs
- **Models Available:** https://openrouter.ai/models
- **Pricing:** https://openrouter.ai/pricing
- **API Status:** https://status.openrouter.ai

---

**Created:** May 2026  
**Version:** 1.0  
**Status:** Production Ready ✅
