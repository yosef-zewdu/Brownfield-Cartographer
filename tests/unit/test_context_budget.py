"""Unit tests for ContextWindowBudget."""

import pytest
from agents.context_budget import ContextWindowBudget


def test_initialization():
    """Test ContextWindowBudget initialization."""
    budget = ContextWindowBudget()
    
    assert budget.usage == {}
    assert budget.encoding is not None


def test_estimate_tokens():
    """Test token estimation."""
    budget = ContextWindowBudget()
    
    text = "This is a test sentence with some words."
    tokens = budget.estimate_tokens(text)
    
    assert tokens > 0
    assert isinstance(tokens, int)
    # Should be roughly 8-10 tokens for this sentence
    assert 5 < tokens < 15


def test_estimate_tokens_empty():
    """Test token estimation with empty string."""
    budget = ContextWindowBudget()
    
    tokens = budget.estimate_tokens("")
    assert tokens == 0


def test_track_usage():
    """Test usage tracking."""
    budget = ContextWindowBudget()
    
    budget.track_usage("gemini-flash", 100, 50)
    
    assert "gemini-flash" in budget.usage
    assert budget.usage["gemini-flash"]["input_tokens"] == 100
    assert budget.usage["gemini-flash"]["output_tokens"] == 50


def test_track_usage_accumulation():
    """Test that usage accumulates across multiple calls."""
    budget = ContextWindowBudget()
    
    budget.track_usage("gemini-flash", 100, 50)
    budget.track_usage("gemini-flash", 200, 100)
    
    assert budget.usage["gemini-flash"]["input_tokens"] == 300
    assert budget.usage["gemini-flash"]["output_tokens"] == 150


def test_track_usage_multiple_models():
    """Test tracking usage for multiple models."""
    budget = ContextWindowBudget()
    
    budget.track_usage("gemini-flash", 100, 50)
    budget.track_usage("gpt-4", 200, 100)
    
    assert "gemini-flash" in budget.usage
    assert "gpt-4" in budget.usage
    assert budget.usage["gemini-flash"]["input_tokens"] == 100
    assert budget.usage["gpt-4"]["input_tokens"] == 200


def test_get_cumulative_cost_single_model():
    """Test cost calculation for a single model."""
    budget = ContextWindowBudget()
    
    # Track 1M input tokens and 500K output tokens for gemini-flash
    budget.track_usage("gemini-flash", 1_000_000, 500_000)
    
    cost = budget.get_cumulative_cost("gemini-flash")
    
    # Cost should be: (1M / 1M) * 0.075 + (0.5M / 1M) * 0.30 = 0.075 + 0.15 = 0.225
    assert cost == pytest.approx(0.225, rel=0.01)


def test_get_cumulative_cost_total():
    """Test total cost calculation across all models."""
    budget = ContextWindowBudget()
    
    budget.track_usage("gemini-flash", 1_000_000, 500_000)
    budget.track_usage("gpt-4", 100_000, 50_000)
    
    total_cost = budget.get_cumulative_cost()
    
    # gemini-flash: 0.225
    # gpt-4: (0.1M / 1M) * 30 + (0.05M / 1M) * 60 = 3.0 + 3.0 = 6.0
    # Total: 6.225
    assert total_cost == pytest.approx(6.225, rel=0.01)


def test_get_cumulative_cost_unknown_model():
    """Test cost calculation for unknown model."""
    budget = ContextWindowBudget()
    
    cost = budget.get_cumulative_cost("unknown-model")
    assert cost == 0.0


def test_get_cumulative_cost_no_pricing():
    """Test cost calculation for model without pricing data."""
    budget = ContextWindowBudget()
    
    budget.track_usage("custom-model", 1000, 500)
    
    cost = budget.get_cumulative_cost("custom-model")
    assert cost == 0.0


def test_select_model_bulk():
    """Test model selection for bulk tasks."""
    budget = ContextWindowBudget()
    
    model = budget.select_model("bulk")
    assert model == "gemini-flash"


def test_select_model_synthesis():
    """Test model selection for synthesis tasks."""
    budget = ContextWindowBudget()
    
    model = budget.select_model("synthesis")
    assert model == "claude-3-sonnet"


def test_select_model_invalid():
    """Test model selection with invalid task type."""
    budget = ContextWindowBudget()
    
    with pytest.raises(ValueError, match="Unknown task type"):
        budget.select_model("invalid")


def test_get_usage_summary():
    """Test usage summary generation."""
    budget = ContextWindowBudget()
    
    budget.track_usage("gemini-flash", 1000, 500)
    budget.track_usage("gpt-4", 2000, 1000)
    
    summary = budget.get_usage_summary()
    
    assert "gemini-flash" in summary
    assert "gpt-4" in summary
    assert "total" in summary
    
    assert summary["gemini-flash"]["input_tokens"] == 1000
    assert summary["gemini-flash"]["output_tokens"] == 500
    assert summary["gemini-flash"]["total_tokens"] == 1500
    
    assert summary["total"]["input_tokens"] == 3000
    assert summary["total"]["output_tokens"] == 1500
    assert summary["total"]["total_tokens"] == 4500


def test_get_usage_summary_empty():
    """Test usage summary with no usage."""
    budget = ContextWindowBudget()
    
    summary = budget.get_usage_summary()
    
    assert "total" in summary
    assert summary["total"]["input_tokens"] == 0
    assert summary["total"]["output_tokens"] == 0
    assert summary["total"]["total_tokens"] == 0
    assert summary["total"]["cost_usd"] == 0.0


def test_pricing_data_exists():
    """Test that pricing data is defined for expected models."""
    assert "gemini-flash" in ContextWindowBudget.PRICING
    assert "gpt-4" in ContextWindowBudget.PRICING
    assert "claude-3-sonnet" in ContextWindowBudget.PRICING
    
    # Check structure
    for model, pricing in ContextWindowBudget.PRICING.items():
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] > 0
        assert pricing["output"] > 0
