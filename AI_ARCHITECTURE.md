# AI Interpreter Architecture & Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CRYPTO-LENS AI PLATFORM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Data Collection Layer                                            │
│  ├─ coin_data_collector.py      (CoinMarketCap, Binance APIs)   │
│  └─ Hourly/Daily OHLCV fetchers (Binance Futures APIs)          │
│                  ↓                                                │
│  Analysis Layer                                                   │
│  ├─ hourly_fetch_and_pulse.py   (1h RSI, sentiment)             │
│  ├─ daily_fetch_and_pulse.py    (24h price action)              │
│  ├─ market_breadth.py           (Market-wide metrics)           │
│  └─ oi_change_screener.py       (Futures anomalies)             │
│                  ↓                                                │
│  🆕 AI INTERPRETATION LAYER                                      │
│  └─ ai_interpreter.py  ┐                                         │
│      ├─ Summarize      ├─→ OpenRouter API ─→ LLM Models        │
│      ├─ Send to LLM    │   (Llama, Mistral, GPT-4, Claude)      │
│      └─ Format for     ┴─→ Discord Webhook → Discord Channel    │
│          Discord                                                  │
│                  ↓                                                │
│  Observability Layer                                              │
│  └─ pipeline_observability.py   (Log monitoring)                │
│                  ↓                                                │
│  Data Storage                                                     │
│  ├─ Local: CSV files                                             │
│  ├─ Cloud: AWS S3                                                │
│  └─ Visualization: Grafana Dashboards                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Market Analysis → AI Insights → Discord

```
Market Data                  Analysis Results              AI Interpretation
  │                            │                                  │
  ├─ OHLCV Candles            │                                  │
  ├─ Volume Data        ──────┤                                  │
  ├─ Price Changes             ├─ Generate Summary ────────────┤
  ├─ RSI/Indicators            │                   │              │
  ├─ Market Breadth      ─────→│  (Text format)   │              │
  └─ OI Changes                │                   │              │
                               └──────────────────┤              │
                                                  ↓              │
                                          interpret_and_send()   │
                                                  │              │
                                ┌─────────────────┘              │
                                │                                │
                    ┌───────────┴──────────┐                     │
                    ↓                      ↓                     ↓
              Call LLM           Get Interpretation      Format Discord
              via OpenRouter     (300-500 chars)        Message
                │                │                       │
                ├─ System Prompt │                       ├─ Title
                ├─ User Prompt  →│                       ├─ Timestamp
                ├─ Model        └→ Interpretation       ├─ AI Response
                └─ Max Tokens                            └─ Action Items
                                                         │
                                                         ↓
                                                  Send to Discord
                                                    Webhook URL
                                                         │
                                                         ↓
                                            📢 Discord Channel
                                         (Real-time alerts)
```

## Component Interaction Diagram

```
pipeline/main.py
    │
    ├─→ coin_data_collector.py
    │       ↓ coin_data.csv
    │
    ├─→ hourly_fetch_and_pulse.py
    │       ├─ prices_1h.csv
    │       ├─ market_pulse.png
    │       └─ Discord alert ┐
    │                        │
    ├─→ daily_fetch_and_pulse.py
    │       ├─ prices_1d.csv ┐
    │       ├─ daily_chart   │
    │       └─ Discord alert │
    │                        │
    ├─→ market_breadth.py───┐
    │       └─ Discord alert │
    │                        │
    ├─→ oi_change_screener.py
    │       └─ Discord alert │
    │                        │
    ├─→ 🆕 ai_interpreter.py 
    │       │
    │       ├─ Read summaries from logs/CSVs (or accept direct input)
    │       │
    │       ├─ call_openrouter_api()
    │       │   ├─ Prepare system/user prompts
    │       │   ├─ Send to OpenRouter
    │       │   ├─ Receive LLM interpretation
    │       │   └─ Validate response
    │       │
    │       ├─ interpret_and_send()
    │       │   ├─ Format Discord message
    │       │   ├─ Add title & timestamp
    │       │   └─ Send via webhook
    │       │
    │       └─ Discord webhook
    │           ├─ AI_INSIGHTS_WEBHOOK (default)
    │           └─ Custom webhook (optional)
    │                        │
    └─→ pipeline_observability.py
            └─ Log monitoring
```

## OpenRouter Integration

```
ai_interpreter.py
    │
    ├─ Environment Setup
    │   ├─ Load .env file
    │   ├─ Get OPENROUTER_API_KEY
    │   ├─ Get OPENROUTER_MODEL (default: Llama 2 70B)
    │   └─ Get AI_INSIGHTS_WEBHOOK
    │
    ├─ Request Building
    │   ├─ System Prompt
    │   │   └─ "You are a crypto market analyst..."
    │   ├─ User Prompt
    │   │   ├─ Market data summary
    │   │   ├─ Analysis context
    │   │   └─ Specific questions
    │   └─ Parameters
    │       ├─ Model selection
    │       ├─ Max tokens: 500
    │       ├─ Temperature: 0.7
    │       └─ Top P: 0.9
    │
    ├─ OpenRouter API Call
    │   ├─ Endpoint: https://openrouter.io/api/v1/chat/completions
    │   ├─ Auth: Bearer {OPENROUTER_API_KEY}
    │   ├─ Headers: 
    │   │   ├─ Content-Type: application/json
    │   │   ├─ HTTP-Referer: https://crypto-lens.ai
    │   │   └─ X-Title: Crypto-Lens AI
    │   └─ Timeout: 30 seconds
    │
    ├─ Response Handling
    │   ├─ Success (200)
    │   │   ├─ Parse JSON
    │   │   ├─ Extract interpretation
    │   │   └─ Validate format
    │   └─ Error (non-200)
    │       ├─ Log error with status code
    │       ├─ Return None
    │       └─ Continue pipeline
    │
    └─ Discord Webhook
        ├─ Build message
        │   ├─ Title
        │   ├─ Timestamp
        │   ├─ Interpretation content
        │   └─ Optional metadata
        ├─ Send to webhook
        │   ├─ URL from environment
        │   ├─ POST with message
        │   └─ Handle response
        └─ Result
            ├─ Success: Log confirmation
            └─ Failure: Log error, continue
```

## Error Handling Flow

```
interpret_and_send(data_summary, context, webhook_url, title)
    │
    ├─ Check API Key
    │   ├─ Present? → Continue
    │   └─ Missing? → Log WARNING, Return False
    │
    ├─ Call OpenRouter
    │   ├─ Success? → Got interpretation
    │   ├─ Timeout? → Log ERROR, Return False
    │   ├─ Auth Error (401)? → Log ERROR, Return False
    │   ├─ Network Error? → Log ERROR, Return False
    │   └─ Parse Error? → Log ERROR, Return False
    │
    ├─ Validate Interpretation
    │   ├─ Valid? → Pydantic model passes
    │   └─ Invalid? → Log ERROR, Return False
    │
    ├─ Check Discord Webhook
    │   ├─ Present? → Continue
    │   └─ Missing? → Log WARNING, Return False
    │
    ├─ Send to Discord
    │   ├─ Success (200)? → Log INFO, Return True
    │   └─ Error? → Log ERROR, Return False
    │
    └─ Catch All Exceptions
        ├─ Log the exception
        └─ Return False
```

## Pipeline Execution Timeline

```
Time │ Script                    │ Status            │ Outputs
─────┼───────────────────────────┼──────────────────┼────────────────────
0:00 │ coin_data_collector       │ Running...       │ coin_data.csv
0:10 │ hourly_fetch_and_pulse    │ Running...       │ prices_1h.csv
0:15 │ └─ Generates summary      │                  │ market_pulse.png
0:20 │ daily_fetch_and_pulse     │ Running...       │ prices_1d.csv
0:25 │ market_breadth            │ Running...       │ breadth metrics
0:30 │ oi_change_screener        │ Running...       │ OI changes
0:35 │ 🆕 ai_interpreter         │ Running...       │ 💬 Discord Message
0:40 │ └─ call_openrouter_api()  │ Awaiting LLM...  │ (OpenRouter)
0:45 │ └─ interpret_and_send()   │ Sending...       │ Discord Webhook
0:50 │ pipeline_observability    │ Running...       │ Log summary
1:00 │ Complete                  │ ✓ All Done       │ Ready for next run
```

## Message Format Example

```
Discord Message:
┌─────────────────────────────────────────────────────────┐
│ 📊 Hourly Crypto Market AI Analysis [2026-05-10 14:30]  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ Bitcoin is showing strength with a +2.5% hourly gain    │
│ and elevated RSI at 65, indicating potential overbought  │
│ conditions. Volume surge of 15% suggests strong buying   │
│ pressure and accumulation phase.                         │
│                                                           │
│ Ethereum follows with +1.8% gains but more stable        │
│ volume, suggesting consolidation. With 67% of altcoins  │
│ trading green, market sentiment is bullish overall.      │
│                                                           │
│ **Recommendation:** Monitor RSI divergence for potential │
│ pullback opportunities. Strong volume supports upside.   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Configuration Hierarchy

```
Environment Variables (.env)
    │
    ├─ OPENROUTER_API_KEY ──────┐
    │                           ├─→ call_openrouter_api()
    ├─ OPENROUTER_MODEL ────────┤   (LLM parameters)
    │                           │
    ├─ AI_INSIGHTS_WEBHOOK ─────┼─→ interpret_and_send()
    │                           │   (Discord integration)
    └─ (existing webhooks) ─────┘
        ├─ MARKET_PULSE_WEBHOOK
        ├─ DAY_CHANGE_WEBHOOK
        ├─ OI_ALERT_WEBHOOK
        └─ etc.

Function Defaults
    │
    ├─ Model: OPENROUTER_MODEL or meta-llama/llama-2-70b-chat
    ├─ Max tokens: 500
    ├─ Temperature: 0.7
    ├─ Top P: 0.9
    └─ Webhook: AI_INSIGHTS_WEBHOOK or custom parameter
```

## State & Caching

```
Per Execution:
┌──────────────────────────────────┐
│ interpret_and_send()             │
├──────────────────────────────────┤
│ Input:                           │
│  ├─ data_summary (required)      │
│  ├─ context (optional)           │
│  ├─ webhook_url (optional)       │
│  └─ title (optional)             │
│                                  │
│ Processing:                      │
│  ├─ Load env vars (once)         │
│  ├─ Validate inputs              │
│  ├─ Call LLM (OpenRouter)        │
│  ├─ Format response              │
│  └─ Send to Discord              │
│                                  │
│ Output:                          │
│  ├─ True (success)               │
│  └─ False (any error)            │
└──────────────────────────────────┘

No Caching:
- Each call is fresh
- New LLM call each time
- Fresh Discord message
- Good for real-time updates
```

---

**Architecture designed for:**
- ✅ Modularity - Loosely coupled components
- ✅ Scalability - Easy to add more models
- ✅ Reliability - Graceful error handling
- ✅ Performance - Async-ready design
- ✅ Security - API keys in .env
- ✅ Monitoring - Comprehensive logging
