"""
AI Interpreter Module - LLM-powered data interpretation using OpenRouter API
Analyzes cryptocurrency market data summaries and provides intelligent insights via Discord.
"""

import os
import json
import sys
import logger
import config
import requests
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv
from utils import FileUtility, DataLoaderUtility
from validations import AIInterpretationResponse
from discord_integrator import send_to_discord

try:
    import pandas as pd
except ImportError:
    pd = None

load_dotenv()
os.umask(0o022)

# Ensure log directory exists
config.ensure_log_directory()

script_path: str = os.path.dirname(os.path.abspath(__file__))
log_path: str = config.get_log_file_path("ai_interpreter")

# Create log file
FileUtility.ensure_log_file_exists(log_path)

# Configuration
OPENROUTER_API_KEY: Optional[str] = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
MODEL: str = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-2-70b-chat")  # Default model
DISCORD_AI_WEBHOOK: Optional[str] = os.environ.get("AI_INSIGHTS_WEBHOOK")

if not OPENROUTER_API_KEY:
    logger.log_event(
        log_category="WARNING",
        message="OPENROUTER_API_KEY not set. AI interpretation will be disabled.",
        path=log_path
    )

if not DISCORD_AI_WEBHOOK:
    logger.log_event(
        log_category="WARNING",
        message="AI_INSIGHTS_WEBHOOK not set. AI interpretations will not be sent to Discord.",
        path=log_path
    )


def load_market_breadth_data() -> Optional[Dict[str, Any]]:
    """
    Load the latest market breadth data from market_breadth.csv
    
    :return: Dict with market breadth metrics or None on error
    """
    try:
        market_breadth_path: str = config.get_output_file_path("market_breadth.csv")
        
        if not os.path.exists(market_breadth_path):
            logger.log_event(
                log_category="WARNING",
                message=f"market_breadth.csv not found at {market_breadth_path}",
                path=log_path
            )
            return None
        
        if pd is None:
            logger.log_event(
                log_category="WARNING",
                message="pandas not available, skipping market breadth data",
                path=log_path
            )
            return None
        
        df: Any = pd.read_csv(market_breadth_path)
        
        if df.empty:
            logger.log_event(
                log_category="WARNING",
                message="market_breadth.csv is empty",
                path=log_path
            )
            return None
        
        # Get the latest row
        latest: Any = df.iloc[-1]
        
        return {
            "timestamp": latest.get("timestamp", "N/A"),
            "market_breadth_pct": float(latest.get("market_breadth_pct", 0)),
            "positive_count": int(latest.get("positive_count", 0)),
            "negative_count": int(latest.get("total_count", 0)) - int(latest.get("positive_count", 0)),
            "total_count": int(latest.get("total_count", 0)),
            "btc_pct": float(latest.get("btc_pct", 0)) if pd.notna(latest.get("btc_pct")) else None,
            "btcd_pct": float(latest.get("btcd_pct", 0)) if pd.notna(latest.get("btcd_pct")) else None
        }
    except Exception as e:
        logger.log_event(
            log_category="ERROR",
            message=f"Failed to load market breadth data: {str(e)}",
            path=log_path
        )
        return None


def load_trend_data(filename: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """
    Load the last N rows of trend data from coin_trend_1h.csv or coin_trend_1d.csv
    
    :param filename: "coin_trend_1h.csv" or "coin_trend_1d.csv"
    :param limit: Number of recent rows to load
    :return: Dict with trend data or None on error
    """
    try:
        trend_path: str = config.get_output_file_path(filename)
        
        if not os.path.exists(trend_path):
            logger.log_event(
                log_category="WARNING",
                message=f"{filename} not found at {trend_path}",
                path=log_path
            )
            return None
        
        if pd is None:
            logger.log_event(
                log_category="WARNING",
                message="pandas not available, skipping trend data",
                path=log_path
            )
            return None
        
        df: Any = pd.read_csv(trend_path)
        
        if df.empty:
            logger.log_event(
                log_category="WARNING",
                message=f"{filename} is empty",
                path=log_path
            )
            return None
        
        # Get the last 'limit' rows
        recent_rows: Any = df.tail(limit)
        
        # Format trend data
        trends_list: list = []
        for idx, row in recent_rows.iterrows():
            trend_entry: Dict[str, Any] = {
                "timestamp": row.get("timestamp", "N/A")
            }
            # Add all trend categories
            for col in recent_rows.columns:
                if col != "timestamp":
                    trend_entry[col] = int(row[col])
            trends_list.append(trend_entry)
        
        return {
            "filename": filename,
            "last_rows": trends_list
        }
    except Exception as e:
        logger.log_event(
            log_category="ERROR",
            message=f"Failed to load {filename}: {str(e)}",
            path=log_path
        )
        return None


def aggregate_market_data() -> str:
    """
    Aggregate all market data from pipeline CSVs into a formatted summary.
    
    :return: str - Formatted market data summary
    """
    summary_lines: list = []
    
    # Load market breadth data
    breadth_data: Optional[Dict[str, Any]] = load_market_breadth_data()
    if breadth_data:
        summary_lines.append("=== MARKET BREADTH ===")
        summary_lines.append(f"Timestamp: {breadth_data['timestamp']}")
        summary_lines.append(f"Market Breadth: {breadth_data['market_breadth_pct']}% ({breadth_data['positive_count']}/{breadth_data['total_count']} coins positive)")
        summary_lines.append(f"Positive Coins: {breadth_data['positive_count']}")
        summary_lines.append(f"Negative Coins: {breadth_data['negative_count']}")
        if breadth_data['btc_pct'] is not None:
            summary_lines.append(f"BTC Change: {breadth_data['btc_pct']}%")
        if breadth_data['btcd_pct'] is not None:
            summary_lines.append(f"BTC Dominance Change: {breadth_data['btcd_pct']}%")
    
    # Load 1-hour trend data
    summary_lines.append("\n=== 1-HOUR TRENDS (Last 5 Candles) ===")
    trend_1h: Optional[Dict[str, Any]] = load_trend_data("coin_trend_1h.csv", limit=5)
    if trend_1h:
        for trend_row in trend_1h["last_rows"]:
            summary_lines.append(f"[{trend_row['timestamp']}] " +
                               f"Uptrend: {trend_row.get('uptrend', 0)}, " +
                               f"Pullback: {trend_row.get('pullback', 0)}, " +
                               f"Downtrend: {trend_row.get('downtrend', 0)}, " +
                               f"Rev-Up: {trend_row.get('reversal-up', 0)}, " +
                               f"Rev-Down: {trend_row.get('reversal-down', 0)}")
    else:
        summary_lines.append("No 1-hour trend data available")
    
    # Load 1-day trend data
    summary_lines.append("\n=== 1-DAY TRENDS (Last 5 Candles) ===")
    trend_1d: Optional[Dict[str, Any]] = load_trend_data("coin_trend_1d.csv", limit=5)
    if trend_1d:
        for trend_row in trend_1d["last_rows"]:
            summary_lines.append(f"[{trend_row['timestamp']}] " +
                               f"Uptrend: {trend_row.get('uptrend', 0)}, " +
                               f"Pullback: {trend_row.get('pullback', 0)}, " +
                               f"Downtrend: {trend_row.get('downtrend', 0)}, " +
                               f"Rev-Up: {trend_row.get('reversal-up', 0)}, " +
                               f"Rev-Down: {trend_row.get('reversal-down', 0)}")
    else:
        summary_lines.append("No 1-day trend data available")
    
    return "\n".join(summary_lines)



def create_system_prompt() -> str:
    """
    Create a system prompt for the LLM to act as a crypto market analyst.
    Your primary role is to identify the likely overall direction of the majority of the market.
    
    :return: str - System prompt for LLM
    """
    return """You are an expert cryptocurrency market analyst with deep knowledge of blockchain technology, 
technical analysis, and market dynamics. Your PRIMARY ROLE is to identify the likely overall direction of 
the majority of the market for the next hours or days based on the provided data.

Analyze market data summaries and provide concise, actionable insights for traders. Your analysis should be:
- Factual and based on provided data
- Concise (under 400 tokens)
- Focused on identifying the likely market direction (bullish, bearish, sideways, or mixed)
- Include specific trend percentages and counts when relevant
- Assess the strength of the current market direction based on breadth and trend data
- Suggest potential price movements or consolidation patterns
- Highlight risk areas and potential reversals
- Professional and data-driven tone

Format your response as:
1. Market Direction Assessment (next hours/days)
2. Supporting Evidence (from breadth & trends)
3. Key Metrics Indicating Direction
4. Risk Factors to Watch
5. Trader Action Items"""


def create_user_prompt(data_summary: str, context: str = "") -> str:
    """
    Create a user prompt with the data summary to analyze market direction.
    
    :param data_summary: str - Market data summary to interpret
    :param context: str - Additional context (e.g., "hourly analysis", "daily sentiment")
    :return: str - User prompt for LLM
    """
    prompt = f"""Based on the following cryptocurrency market data, predict the likely overall market direction 
for the majority of coins over the next hours or days. Focus on identifying whether the market is 
likely to move UP (bullish), DOWN (bearish), SIDEWAYS (consolidating), or MIXED.

MARKET DATA:
{data_summary}

ANALYSIS QUESTIONS:
1. What is the primary market direction indicated by the breadth percentage and trend distribution?
2. Is the market showing strength (high uptrend %) or weakness (high downtrend %)?
3. Are reversals happening at key levels, and what do they suggest?
4. How does BTC and BTC Dominance movement influence the broader market direction?
5. Based on both 1-hour and 1-day trends, what is the consensus direction?

Please provide your analysis with specific numbers and percentages."""
    
    return prompt


def call_openrouter_api(
    data_summary: str,
    context: str = "",
    model: Optional[str] = None,
    max_tokens: int = 500
) -> Optional[str]:
    """
    Call OpenRouter API to get LLM interpretation of data.
    
    :param data_summary: str - Market data summary
    :param context: str - Additional context
    :param model: str - Model to use (defaults to OPENROUTER_MODEL)
    :param max_tokens: int - Maximum tokens in response
    :return: Optional[str] - LLM interpretation or None on error
    """
    if not OPENROUTER_API_KEY:
        logger.log_event(
            log_category="WARNING",
            message="OPENROUTER_API_KEY not configured. Skipping AI interpretation.",
            path=log_path
        )
        return None
    
    if model is None:
        model = MODEL
    
    try:
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://crypto-lens.ai",  # Optional but recommended
            "X-Title": "Crypto-Lens AI"
        }
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": create_system_prompt()
                },
                {
                    "role": "user",
                    "content": create_user_prompt(data_summary, context)
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        logger.log_event(
            log_category="INFO",
            message=f"Calling OpenRouter API with model: {model}",
            path=log_path
        )
        
        response: requests.Response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result: Dict[str, Any] = response.json()
            interpretation: str = result["choices"][0]["message"]["content"]
            
            logger.log_event(
                log_category="INFO",
                message=f"Successfully received AI interpretation ({len(interpretation)} chars)",
                path=log_path
            )
            
            return interpretation
        else:
            error_msg: str = f"OpenRouter API error: {response.status_code} - {response.text}"
            logger.log_event(
                log_category="ERROR",
                message=error_msg,
                path=log_path
            )
            return None
    
    except requests.exceptions.Timeout:
        logger.log_event(
            log_category="ERROR",
            message="OpenRouter API request timed out (30s)",
            path=log_path
        )
        return None
    except requests.exceptions.RequestException as e:
        logger.log_event(
            log_category="ERROR",
            message=f"Failed to call OpenRouter API: {str(e)}",
            path=log_path
        )
        return None
    except (KeyError, json.JSONDecodeError) as e:
        logger.log_event(
            log_category="ERROR",
            message=f"Failed to parse OpenRouter response: {str(e)}",
            path=log_path
        )
        return None


def interpret_and_send(
    data_summary: str,
    context: str = "",
    webhook_url: Optional[str] = None,
    title: str = "AI Market Interpretation"
) -> bool:
    """
    Interpret data with LLM and send insights to Discord.
    
    :param data_summary: str - Market data summary to interpret
    :param context: str - Additional context
    :param webhook_url: str - Discord webhook URL (uses default if None)
    :param title: str - Title for Discord message
    :return: bool - True if successful, False otherwise
    """
    try:
        # Get LLM interpretation
        interpretation: Optional[str] = call_openrouter_api(data_summary, context)
        
        if not interpretation:
            logger.log_event(
                log_category="WARNING",
                message="Failed to get AI interpretation, skipping Discord send",
                path=log_path
            )
            return False
        
        # Validate interpretation response
        ai_response: AIInterpretationResponse = AIInterpretationResponse(
            timestamp=datetime.now(),
            context=context,
            data_summary=data_summary[:200] + "..." if len(data_summary) > 200 else data_summary,
            interpretation=interpretation,
            model_used=MODEL
        )
        
        # Prepare Discord message
        webhook_to_use: Optional[str] = webhook_url or DISCORD_AI_WEBHOOK
        if not webhook_to_use:
            logger.log_event(
                log_category="WARNING",
                message="No Discord webhook URL provided for AI interpretation",
                path=log_path
            )
            return False
        
        # Format message with title and interpretation
        timestamp_str: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        discord_message: str = f"**{title}** [{timestamp_str}]\n\n{interpretation}"
        
        # Send to Discord
        send_to_discord(webhook_to_use, discord_message)
        
        logger.log_event(
            log_category="INFO",
            message=f"Successfully sent AI interpretation to Discord ({len(discord_message)} chars)",
            path=log_path
        )
        
        return True
    
    except Exception as e:
        logger.log_event(
            log_category="ERROR",
            message=f"Failed to interpret and send AI insights: {str(e)}",
            path=log_path
        )
        return False


def main() -> None:
    """Main function that aggregates pipeline data and generates AI interpretation."""
    logger.log_event(
        log_category="INFO",
        message="Running AI interpreter script with pipeline data aggregation",
        path=log_path
    )
    
    # Aggregate market data from all pipeline sources
    market_data_summary: str = aggregate_market_data()
    
    if not market_data_summary:
        logger.log_event(
            log_category="ERROR",
            message="Failed to aggregate market data",
            path=log_path
        )
        return
    
    # Log the aggregated data
    logger.log_event(
        log_category="INFO",
        message=f"Aggregated market data (length: {len(market_data_summary)} chars)",
        path=log_path
    )
    
    # Interpret and send to Discord
    success: bool = interpret_and_send(
        data_summary=market_data_summary,
        context="real-time market analysis from pipeline data",
        title="🤖 Market Direction Analysis"
    )
    
    if success:
        logger.log_event(
            log_category="INFO",
            message="AI interpretation completed successfully with pipeline data",
            path=log_path
        )
    else:
        logger.log_event(
            log_category="ERROR",
            message="AI interpretation failed",
            path=log_path
        )


if __name__ == "__main__":
    main()
