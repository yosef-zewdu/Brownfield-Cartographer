"""CartographyTraceLogger for provenance tracking and audit trail."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ActionLogEntry(BaseModel):
    """Log entry for agent actions with provenance tracking."""
    
    entry_type: Literal["action"] = "action"
    timestamp: str
    agent: Literal["surveyor", "hydrologist", "semanticist", "archivist"]
    action: str
    evidence_source: str
    evidence_type: Literal["tree_sitter", "sqlglot", "yaml_parse", "heuristic", "llm"]
    confidence: float = Field(ge=0.0, le=1.0)
    resolution_status: Literal["resolved", "partial", "dynamic", "inferred"]
    details: Optional[Dict[str, Any]] = None


class ErrorLogEntry(BaseModel):
    """Log entry for errors and warnings with provenance context."""
    
    entry_type: Literal["error"] = "error"
    timestamp: str
    agent: Literal["surveyor", "hydrologist", "semanticist", "archivist"]
    severity: Literal["error", "warning"]
    message: str
    evidence_source: Optional[str] = None
    evidence_type: Optional[Literal["tree_sitter", "sqlglot", "yaml_parse", "heuristic", "llm"]] = None
    context: Optional[Dict[str, Any]] = None


class LLMCallLogEntry(BaseModel):
    """Log entry for LLM API calls with usage tracking."""
    
    entry_type: Literal["llm_call"] = "llm_call"
    timestamp: str
    agent: Literal["surveyor", "hydrologist", "semanticist", "archivist"]
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    confidence: float = Field(ge=0.0, le=1.0)
    purpose: str
    result_summary: Optional[str] = None


class CartographyTraceLogger:
    """
    Provides complete audit trail of all analysis actions with full provenance tracking.
    
    Logs:
    - Actions taken by each agent (Surveyor, Hydrologist, Semanticist, Archivist)
    - Evidence sources and types (tree_sitter, sqlglot, yaml_parse, heuristic, llm)
    - Confidence scores for all conclusions
    - Resolution status (resolved, partial, dynamic, inferred)
    - LLM API calls with usage tracking
    - Errors and warnings with context
    
    The trace log is written as JSONL (JSON Lines) format to cartography_trace.jsonl.
    """
    
    def __init__(self):
        """Initialize CartographyTraceLogger with a unique run ID."""
        self.run_id: str = str(uuid.uuid4())
        self.started_at: str = datetime.now().isoformat()
        self.log_entries: List[Any] = []
    
    def log_action(
        self,
        agent: Literal["surveyor", "hydrologist", "semanticist", "archivist"],
        action: str,
        evidence_source: str,
        evidence_type: Literal["tree_sitter", "sqlglot", "yaml_parse", "heuristic", "llm"],
        confidence: float,
        resolution_status: Literal["resolved", "partial", "dynamic", "inferred"],
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an agent action with full provenance tracking.
        
        Args:
            agent: Agent performing the action
            action: Description of the action taken
            evidence_source: Source file or component providing evidence
            evidence_type: Type of evidence (static analysis vs inference)
            confidence: Confidence score (0.0 to 1.0)
            resolution_status: Status of the resolution
            details: Optional additional details
        """
        entry = ActionLogEntry(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            action=action,
            evidence_source=evidence_source,
            evidence_type=evidence_type,
            confidence=confidence,
            resolution_status=resolution_status,
            details=details
        )
        
        self.log_entries.append(entry)
        logger.debug(f"[{agent}] {action} - {evidence_type} ({confidence:.2f})")
    
    def log_error(
        self,
        agent: Literal["surveyor", "hydrologist", "semanticist", "archivist"],
        severity: Literal["error", "warning"],
        message: str,
        evidence_source: Optional[str] = None,
        evidence_type: Optional[Literal["tree_sitter", "sqlglot", "yaml_parse", "heuristic", "llm"]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error or warning with provenance context.
        
        Args:
            agent: Agent encountering the error
            severity: Severity level (error or warning)
            message: Error message
            evidence_source: Optional source file or component
            evidence_type: Optional type of evidence being processed
            context: Optional additional context
        """
        entry = ErrorLogEntry(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            severity=severity,
            message=message,
            evidence_source=evidence_source,
            evidence_type=evidence_type,
            context=context
        )
        
        self.log_entries.append(entry)
        
        if severity == "error":
            logger.error(f"[{agent}] {message}")
        else:
            logger.warning(f"[{agent}] {message}")
    
    def log_llm_call(
        self,
        agent: Literal["surveyor", "hydrologist", "semanticist", "archivist"],
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        confidence: float,
        purpose: str,
        result_summary: Optional[str] = None
    ) -> None:
        """
        Log an LLM API call with usage tracking and confidence score.
        
        Args:
            agent: Agent making the LLM call
            model: Model identifier (e.g., "gpt-4", "gemini-pro")
            prompt_tokens: Number of tokens in prompt
            completion_tokens: Number of tokens in completion
            confidence: Confidence score for the LLM result (0.0 to 1.0)
            purpose: Purpose of the LLM call
            result_summary: Optional summary of the result
        """
        entry = LLMCallLogEntry(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            confidence=confidence,
            purpose=purpose,
            result_summary=result_summary
        )
        
        self.log_entries.append(entry)
        logger.debug(
            f"[{agent}] LLM call: {model} - {purpose} "
            f"({prompt_tokens + completion_tokens} tokens, confidence: {confidence:.2f})"
        )
    
    def flush(self, output_path: Path) -> None:
        """
        Append accumulated log entries to JSONL file, preceded by a run-start header.

        Args:
            output_path: Path to write/append cartography_trace.jsonl

        Raises:
            IOError: If file writing fails
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'a', encoding='utf-8') as f:
                # Run-start header so readers can identify run boundaries
                header = {
                    "entry_type": "run_start",
                    "run_id": self.run_id,
                    "started_at": self.started_at,
                    "flushed_at": datetime.now().isoformat(),
                    "entry_count": len(self.log_entries),
                }
                f.write(json.dumps(header) + '\n')

                for entry in self.log_entries:
                    # Inject run_id into every entry for easy filtering
                    data = json.loads(entry.model_dump_json())
                    data["run_id"] = self.run_id
                    f.write(json.dumps(data) + '\n')

            logger.info(
                f"Trace log appended to {output_path} "
                f"(run={self.run_id}, {len(self.log_entries)} entries)"
            )

        except IOError as e:
            logger.error(f"Failed to write trace log to {output_path}: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about logged entries.
        
        Returns:
            Dictionary with statistics about log entries
        """
        stats = {
            'total_entries': len(self.log_entries),
            'by_type': {},
            'by_agent': {},
            'by_evidence_type': {},
            'total_llm_tokens': 0,
            'average_confidence': 0.0
        }
        
        confidences = []
        
        for entry in self.log_entries:
            # Count by entry type
            entry_type = entry.entry_type
            stats['by_type'][entry_type] = stats['by_type'].get(entry_type, 0) + 1
            
            # Count by agent
            agent = entry.agent
            stats['by_agent'][agent] = stats['by_agent'].get(agent, 0) + 1
            
            # Count by evidence type (for action entries)
            if hasattr(entry, 'evidence_type') and entry.evidence_type:
                ev_type = entry.evidence_type
                stats['by_evidence_type'][ev_type] = stats['by_evidence_type'].get(ev_type, 0) + 1
            
            # Accumulate LLM tokens
            if entry_type == 'llm_call':
                stats['total_llm_tokens'] += entry.total_tokens
            
            # Collect confidence scores
            if hasattr(entry, 'confidence'):
                confidences.append(entry.confidence)
        
        # Calculate average confidence
        if confidences:
            stats['average_confidence'] = sum(confidences) / len(confidences)
        
        return stats
    
    def clear(self) -> None:
        """Clear all accumulated log entries."""
        self.log_entries.clear()
        logger.debug("Trace log cleared")
