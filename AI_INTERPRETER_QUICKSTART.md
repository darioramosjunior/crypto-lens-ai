# AI Interpreter - Quick Start (5 Minutes)

Get LLM-powered market analysis integrated with your pipeline in 5 steps.

## 1️⃣ Get OpenRouter API Key (2 min)

```bash
# Visit: https://openrouter.ai
# 1. Sign up (free)
# 2. Go to API Keys
# 3. Create key
# 4. Copy the key
```

## 2️⃣ Update .env File (1 min)

Add these lines to your `.env` file:

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx

# Optional - Discord webhook for AI insights
AI_INSIGHTS_WEBHOOK=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN

# Optional - Choose your model (defaults to Llama 2 70B)
OPENROUTER_MODEL=meta-llama/llama-2-70b-chat
```

## 3️⃣ Test the Setup (1 min)

```bash
# Run standalone test
python ai_interpreter.py

# Should output:
# [INFO] Running AI interpreter script
# [INFO] Successfully received AI interpretation
# [INFO] Successfully sent AI interpretation to Discord
```

## 4️⃣ Integrate with Your Pipeline (1 min)

The AI interpreter is **already integrated** into [main.py](main.py)! It runs automatically after market analysis:

```bash
python main.py
# Pipeline sequence:
# 1. coin_data_collector.py
# 2. hourly_fetch_and_pulse.py
# 3. daily_fetch_and_pulse.py
# 4. market_breadth.py
# 5. oi_change_screener.py
# 6. ai_interpreter.py        ← Runs here!
# 7. pipeline_observability.py
```

## 5️⃣ Use AI Interpretation in Your Code (optional)

Capture data summaries and send them to LLM:

```python
from ai_interpreter import interpret_and_send

# Example from hourly_fetch_and_pulse.py
market_summary = f"""
BTC/USDT (1h): +2.5%, RSI: 65, Volume: +15%
ETH/USDT (1h): +1.8%, RSI: 58
Market Breadth: 67% green
"""

# Get AI interpretation and send to Discord
interpret_and_send(
    data_summary=market_summary,
    context="hourly market analysis",
    title="🚀 Hourly Crypto Insights"
)
```

## ✅ Verification Checklist

- [ ] OpenRouter API key obtained
- [ ] `.env` file updated with `OPENROUTER_API_KEY`
- [ ] Discord webhook added to `.env` (optional but recommended)
- [ ] Standalone test passes: `python ai_interpreter.py`
- [ ] Check Discord channel for test message
- [ ] Pipeline runs: `python main.py`

## 📊 Common Use Cases

### Case 1: Get Insights Without Discord
```python
from ai_interpreter import call_openrouter_api

interpretation = call_openrouter_api(
    data_summary="BTC data here",
    context="technical analysis"
)
print(interpretation)  # Use it anywhere
```

### Case 2: Use Different Model
```python
interpret_and_send(
    data_summary="Market data",
    context="hourly"
    # Automatically uses OPENROUTER_MODEL from .env
    # Or specify: model="mistralai/mistral-7b"
)
```

### Case 3: Send to Different Discord Channel
```python
interpret_and_send(
    data_summary="Market data",
    webhook_url="https://discord.com/api/webhooks/DIFFERENT_ID/TOKEN",
    title="Special Analysis"
)
```

## 🔍 Troubleshooting

### "OPENROUTER_API_KEY not set"
```bash
# Check .env file has correct key
cat .env | grep OPENROUTER

# Reload environment
source .env  # Linux/Mac
.env         # Windows (not needed if using python-dotenv)
```

### "OpenRouter API error: 401"
```bash
# Verify API key is correct
# Visit: https://openrouter.ai/account/api-keys
# Copy the correct key and update .env
```

### Discord message not received
```bash
# Check webhook URL is correct
# Verify Discord channel has message history enabled
# Check bot permissions in Discord
```

## 📚 More Information

- **Full Guide:** [docs/AI_INTERPRETER_GUIDE.md](../docs/AI_INTERPRETER_GUIDE.md)
- **API Reference:** See docstrings in [ai_interpreter.py](../ai_interpreter.py)
- **Tests:** [tests/test_ai_interpreter.py](../tests/test_ai_interpreter.py)
- **AGENTS.md:** Project conventions and patterns

## 💡 Pro Tips

1. **Free models are fast:** Llama 2 70B is free on OpenRouter
2. **Test different models:** Try Mistral, Nous Hermes for different costs/speeds
3. **Monitor costs:** Check OpenRouter dashboard for usage
4. **Custom prompts:** Edit `create_system_prompt()` to change LLM behavior
5. **Integrate early:** Add AI interpretation to existing analysis scripts

## 🚀 Next Steps

1. ✅ Complete the 5-minute setup above
2. 📖 Read [AI_INTERPRETER_GUIDE.md](../docs/AI_INTERPRETER_GUIDE.md) for advanced usage
3. 🔧 Customize the system prompt for your use case
4. 📊 Add data summaries from your pipeline scripts
5. 🎯 Experiment with different models and contexts

---

**Setup time:** ~5 minutes | **Cost:** ~$0.01/month (Llama 2) to $0.03/month (GPT-4)
