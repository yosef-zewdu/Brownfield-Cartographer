"""Context window budget manager for tracking LLM token usage and costs."""

import logging
from typing import Dict, Literal, Optional
import tiktoken

logger = logging.getLogger(__name__)


class ContextWindowBudget:
    """Tracks token usage and costs for LLM API calls."""
    
    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        "gemini-flash": {
            "input": 0.075,   # $0.075 per 1M input tokens
            "output": 0.30,   # $0.30 per 1M output tokens
        },
        "gpt-4": {
            "input": 30.0,    # $30 per 1M input tokens
            "output": 60.0,   # $60 per 1M output tokens
        },
        "claude-3-sonnet": {
            "input": 3.0,     # $3 per 1M input tokens
            "output": 15.0,   # $15 per 1M output tokens
        },
    }
    
    def __init__(self):
        """Initialize budget tracker."""
        self.usage: Dict[str, Dict[str, int]] = {}
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using tiktoken.
        
        Args:
            text: Input text to estimate
        
        Returns:
            Estimated token count
        """
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Failed to estimate tokens: {e}, using character-based estimate")
            # Fallback: rough estimate of 4 characters per token
            return len(text) // 4
    
    def track_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> None:
        """
        Track token usage for a model.
        
        Args:
            model: Model name (e.g., "gemini-flash", "gpt-4")
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
        """
        if model not in self.usage:
            self.usage[model] = {
                "input_tokens": 0,
                "output_tokens": 0,
            }
        
        self.usage[model]["input_tokens"] += input_tokens
        self.usage[model]["output_tokens"] += output_tokens
        
        logger.debug(
            f"Tracked usage for {model}: "
            f"+{input_tokens} input, +{output_tokens} output tokens"
        )
    
    def get_cumulative_cost(self, model: Optional[str] = None) -> float:
        """
        Calculate cumulative cost with pricing for different models.
        
        Args:
            model: Optional model name to get cost for specific model.
                   If None, returns total cost across all models.
        
        Returns:
            Total cost in USD
        """
        if model:
            if model not in self.usage:
                return 0.0
            
            if model not in self.PRICING:
                logger.warning(f"No pricing data for model {model}")
                return 0.0
            
            usage = self.usage[model]
            pricing = self.PRICING[model]
            
            input_cost = (usage["input_tokens"] / 1_000_000) * pricing["input"]
            output_cost = (usage["output_tokens"] / 1_000_000) * pricing["output"]
            
            return input_cost + output_cost
        
        # Calculate total cost across all models
        total_cost = 0.0
        for model_name in self.usage:
            total_cost += self.get_cumulative_cost(model_name)
        
        return total_cost
    
    def select_model(
        self,
        task_type: Literal["bulk", "synthesis"]
    ) -> str:
        """
        Select appropriate model based on task type.
        
        Args:
            task_type: Type of task - "bulk" for high-volume simple tasks,
                      "synthesis" for complex reasoning tasks
        
        Returns:
            Model name to use
        """
        if task_type == "bulk":
            # Use fast, cheap model for bulk processing
            return "gemini-flash"
        elif task_type == "synthesis":
            # Use capable model for complex synthesis
            # Prefer Claude for better reasoning, fallback to GPT-4
            return "claude-3-sonnet"
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    def get_usage_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Get summary of usage and costs.
        
        Returns:
            Dictionary with usage statistics and costs per model
        """
        summary = {}
        
        for model, usage in self.usage.items():
            cost = self.get_cumulative_cost(model)
            summary[model] = {
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["input_tokens"] + usage["output_tokens"],
                "cost_usd": round(cost, 4),
            }
        
        # Add total
        summary["total"] = {
            "input_tokens": sum(u["input_tokens"] for u in self.usage.values()),
            "output_tokens": sum(u["output_tokens"] for u in self.usage.values()),
            "total_tokens": sum(
                u["input_tokens"] + u["output_tokens"] for u in self.usage.values()
            ),
            "cost_usd": round(self.get_cumulative_cost(), 4),
        }
        
        return summary
