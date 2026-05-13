"""
Unit tests for the AI Interpreter module
Tests LLM integration, OpenRouter API calls, and Discord messaging
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from ai_interpreter import (
    call_openrouter_api,
    create_system_prompt,
    create_user_prompt,
    interpret_and_send
)
from validations import AIInterpretationResponse, AIInterpretationRequest


@pytest.mark.unit
class TestAIInterpreterPrompts:
    """Test prompt generation for LLM"""
    
    def test_system_prompt_generation(self):
        """Test that system prompt is generated correctly"""
        prompt = create_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "market analyst" in prompt.lower()
        assert "cryptocurrency" in prompt.lower()
    
    def test_user_prompt_generation(self):
        """Test user prompt creation with data summary"""
        data_summary = "BTC +2.5%, ETH +1.8%"
        context = "hourly analysis"
        
        prompt = create_user_prompt(data_summary, context)
        assert isinstance(prompt, str)
        assert data_summary in prompt
        assert context in prompt
        assert "Key observations" in prompt
    
    def test_user_prompt_without_context(self):
        """Test user prompt generation without context"""
        data_summary = "Market data here"
        prompt = create_user_prompt(data_summary)
        
        assert isinstance(prompt, str)
        assert data_summary in prompt


@pytest.mark.unit
class TestAIInterpretationValidation:
    """Test validation models for AI responses"""
    
    def test_valid_ai_interpretation_response(self):
        """Test creating valid AI interpretation response"""
        response = AIInterpretationResponse(
            timestamp=datetime.now(),
            context="hourly",
            data_summary="BTC: +2.5%, volume up",
            interpretation="Bitcoin showing strength with volume confirmation",
            model_used="meta-llama/llama-2-70b-chat"
        )
        
        assert response.context == "hourly"
        assert len(response.interpretation) > 0
        assert response.model_used is not None
    
    def test_ai_interpretation_response_missing_field(self):
        """Test validation fails with missing required field"""
        with pytest.raises(Exception):  # ValidationError
            AIInterpretationResponse(
                timestamp=datetime.now(),
                context="hourly",
                data_summary="BTC data",
                # Missing interpretation field
                model_used="model"
            )
    
    def test_ai_interpretation_request_validation(self):
        """Test AI interpretation request validation"""
        request = AIInterpretationRequest(
            data_summary="Market summary data",
            context="daily",
            model="gpt-4",
            title="Market Analysis"
        )
        
        assert request.data_summary == "Market summary data"
        assert request.context == "daily"
        assert request.model == "gpt-4"


@pytest.mark.unit
@patch('ai_interpreter.requests.post')
def test_openrouter_api_call_success(mock_post):
    """Test successful OpenRouter API call"""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Bitcoin is showing bullish signals with RSI at 65, indicating overbought conditions. Volume surge suggests accumulation phase."
                }
            }
        ]
    }
    mock_post.return_value = mock_response
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}):
        result = call_openrouter_api(
            data_summary="BTC RSI: 65, Volume +15%",
            context="technical analysis"
        )
    
    assert result is not None
    assert "bullish" in result.lower() or "Bitcoin" in result
    mock_post.assert_called_once()


@pytest.mark.unit
@patch('ai_interpreter.requests.post')
def test_openrouter_api_call_failure(mock_post):
    """Test OpenRouter API call failure handling"""
    # Mock error response
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Invalid API key"
    mock_post.return_value = mock_response
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "invalid_key"}):
        result = call_openrouter_api(
            data_summary="BTC data",
            context="test"
        )
    
    assert result is None


@pytest.mark.unit
@patch('ai_interpreter.requests.post')
def test_openrouter_api_timeout(mock_post):
    """Test OpenRouter API timeout handling"""
    import requests
    mock_post.side_effect = requests.exceptions.Timeout()
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}):
        result = call_openrouter_api(
            data_summary="BTC data",
            context="test"
        )
    
    assert result is None


@pytest.mark.unit
def test_no_api_key_configured():
    """Test behavior when API key is not configured"""
    with patch.dict(os.environ, {}, clear=True):
        result = call_openrouter_api(
            data_summary="BTC data",
            context="test"
        )
    
    assert result is None


@pytest.mark.unit
@patch('ai_interpreter.send_to_discord')
@patch('ai_interpreter.call_openrouter_api')
def test_interpret_and_send_success(mock_api, mock_discord):
    """Test successful interpretation and Discord send"""
    mock_api.return_value = "Market analysis here"
    mock_discord.return_value = None
    
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test_key",
        "AI_INSIGHTS_WEBHOOK": "https://discord.webhook"
    }):
        result = interpret_and_send(
            data_summary="BTC: +2.5%",
            context="hourly",
            title="Hourly Analysis"
        )
    
    assert result is True
    mock_api.assert_called_once()
    mock_discord.assert_called_once()


@pytest.mark.unit
@patch('ai_interpreter.call_openrouter_api')
def test_interpret_and_send_no_interpretation(mock_api):
    """Test interpret_and_send when LLM returns None"""
    mock_api.return_value = None
    
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test_key",
        "AI_INSIGHTS_WEBHOOK": "https://discord.webhook"
    }):
        result = interpret_and_send(
            data_summary="BTC: +2.5%",
            context="hourly"
        )
    
    assert result is False


@pytest.mark.unit
@patch('ai_interpreter.call_openrouter_api')
def test_interpret_and_send_no_webhook(mock_api):
    """Test interpret_and_send without webhook configured"""
    mock_api.return_value = "Market analysis"
    
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test_key"
    }, clear=True):
        result = interpret_and_send(
            data_summary="BTC: +2.5%",
            context="hourly"
        )
    
    # Should fail gracefully without webhook
    assert result is False


@pytest.mark.integration
@patch('ai_interpreter.send_to_discord')
@patch('ai_interpreter.requests.post')
def test_full_interpretation_workflow(mock_post, mock_discord):
    """Test complete interpretation workflow from data to Discord"""
    # Mock API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Bitcoin showing mixed signals. RSI elevated but volume supports price action. Watch for breakout."
                }
            }
        ]
    }
    mock_post.return_value = mock_response
    mock_discord.return_value = None
    
    data_summary = "BTC/USDT (1h): +2.5%, RSI: 65, Volume: +15%"
    
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test_key",
        "AI_INSIGHTS_WEBHOOK": "https://discord.webhook",
        "OPENROUTER_MODEL": "meta-llama/llama-2-70b-chat"
    }):
        result = interpret_and_send(
            data_summary=data_summary,
            context="hourly technical analysis",
            title="Hourly BTC Analysis"
        )
    
    assert result is True
    mock_post.assert_called_once()
    mock_discord.assert_called_once()
    
    # Verify Discord message contains interpretation
    call_args = mock_discord.call_args
    discord_message = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('message')
    assert "Hourly BTC Analysis" in discord_message
