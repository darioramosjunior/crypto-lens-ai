"""
AI Interpreter Module - LLM-powered data interpretation using OpenRouter API
Analyzes cryptocurrency market data summaries and provides intelligent insights via Discord.
"""

import os
import json
import logger
import config
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from utils import FileUtility
from validations import AIInterpretationResponse
from discord_integrator import send_to_discord

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


def create_system_prompt() -> str:
    """
    Create a system prompt for the LLM to act as a crypto market analyst.
    
    :return: str - System prompt for LLM
    """
    return """You are an expert cryptocurrency market analyst with deep knowledge of blockchain technology, 
technical analysis, and market dynamics. You analyze market data summaries and provide concise, 
actionable insights for traders. Your analysis should be:
- Factual and based on provided data
- Concise (under 300 tokens)
- Focused on key market movements and implications
- Include specific coins/percentages when relevant
- Suggest potential actions or caution areas
- Professional and data-driven tone

Format your response as a clear, structured analysis."""


def create_user_prompt(data_summary: str, context: str = "") -> str:
    """
    Create a user prompt with the data summary to analyze.
    
    :param data_summary: str - Market data summary to interpret
    :param context: str - Additional context (e.g., "hourly analysis", "daily sentiment")
    :return: str - User prompt for LLM
    """
    prompt = f"""Analyze the following cryptocurrency market data {context}:

{data_summary}

Please provide:
1. Key observations from the data
2. Market sentiment assessment
3. Notable patterns or anomalies
4. Potential implications for traders
5. Risk areas to watch"""
    
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
    """Main function for testing/standalone AI interpretation."""
    logger.log_event(
        log_category="INFO",
        message="Running AI interpreter script",
        path=log_path
    )
    
    # Test data summary
    test_summary: str = """
    BTC/USDT (1h): +2.5%, RSI: 65 (overbought), Volume up 15%
    ETH/USDT (1h): +1.8%, RSI: 58, Volume stable
    Market Breadth: 67% of coins trading green
    """
    
    success: bool = interpret_and_send(
        data_summary=test_summary,
        context="hourly market analysis",
        title="Hourly Crypto Market AI Analysis"
    )
    
    if success:
        logger.log_event(
            log_category="INFO",
            message="AI interpretation completed successfully",
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
