"""Onboarding Brief Generator for creating Day-One question summaries."""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class OnboardingBriefGenerator:
    """
    Generates onboarding_brief.md with answers to the Five FDE Day-One Questions.
    
    The brief provides new developers with critical context about:
    1. Where data comes from (Ingestion Path)
    2. What are the critical outputs (Critical Outputs)
    3. What happens if X breaks (Blast Radius)
    4. Where does business logic Y live (Logic Distribution)
    5. What changes most often (Change Velocity)
    """
    
    def __init__(self):
        """Initialize Onboarding Brief Generator."""
        pass
    
    def generate(
        self,
        day_one_answers: Dict[str, Dict[str, Any]],
        analysis_metadata: Dict[str, Any]
    ) -> str:
        """
        Generate complete onboarding_brief.md document.
        
        Args:
            day_one_answers: Dictionary with answers to all five Day-One questions
                Expected keys: 'ingestion_path', 'critical_outputs', 'blast_radius',
                               'logic_distribution', 'change_velocity'
                Each value should have: 'answer', 'evidence', 'provenance'
            analysis_metadata: Metadata about the analysis run
                Expected keys: 'timestamp', 'repository_path', 'total_modules',
                              'total_datasets', 'total_transformations', 'analysis_duration'
        
        Returns:
            Complete onboarding_brief.md content as string
        """
        logger.info("Generating onboarding_brief.md")
        
        sections = []
        
        # Header
        sections.append("# Onboarding Brief - Day-One Questions")
        sections.append("")
        sections.append("This document answers the Five FDE Day-One Questions to help new developers ")
        sections.append("quickly understand the codebase architecture and critical components.")
        sections.append("")
        
        # Metadata
        sections.append(self._write_metadata(analysis_metadata))
        sections.append("")
        
        # Question 1: Where does data come from?
        if 'ingestion_path' in day_one_answers:
            sections.append(self._write_question_section(
                question_number=1,
                question_title="Where does data come from?",
                answer_data=day_one_answers['ingestion_path']
            ))
            sections.append("")
        
        # Question 2: What are the critical outputs?
        if 'critical_outputs' in day_one_answers:
            sections.append(self._write_question_section(
                question_number=2,
                question_title="What are the critical outputs?",
                answer_data=day_one_answers['critical_outputs']
            ))
            sections.append("")
        
        # Question 3: What happens if X breaks?
        if 'blast_radius' in day_one_answers:
            sections.append(self._write_question_section(
                question_number=3,
                question_title="What happens if critical components break?",
                answer_data=day_one_answers['blast_radius']
            ))
            sections.append("")
        
        # Question 4: Where does business logic Y live?
        if 'logic_distribution' in day_one_answers:
            sections.append(self._write_question_section(
                question_number=4,
                question_title="Where does business logic live?",
                answer_data=day_one_answers['logic_distribution']
            ))
            sections.append("")
        
        # Question 5: What changes most often?
        if 'change_velocity' in day_one_answers:
            sections.append(self._write_question_section(
                question_number=5,
                question_title="What changes most often?",
                answer_data=day_one_answers['change_velocity']
            ))
            sections.append("")
        
        # Coverage Summary
        sections.append(self._write_coverage_summary(day_one_answers, analysis_metadata))
        
        content = "\n".join(sections)
        logger.info("onboarding_brief.md generation complete")
        
        return content
    
    def _write_metadata(self, analysis_metadata: Dict[str, Any]) -> str:
        """
        Write analysis metadata section.
        
        Args:
            analysis_metadata: Metadata about the analysis run
        
        Returns:
            Metadata section as string
        """
        section = "## Analysis Metadata\n\n"
        
        # Timestamp
        timestamp = analysis_metadata.get('timestamp')
        if timestamp:
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_str = str(timestamp)
            section += f"- **Generated:** {timestamp_str}\n"
        
        # Repository path
        repo_path = analysis_metadata.get('repository_path')
        if repo_path:
            section += f"- **Repository:** `{repo_path}`\n"
        
        # Coverage statistics
        total_modules = analysis_metadata.get('total_modules', 0)
        total_datasets = analysis_metadata.get('total_datasets', 0)
        total_transformations = analysis_metadata.get('total_transformations', 0)
        
        section += f"- **Modules Analyzed:** {total_modules}\n"
        section += f"- **Datasets Identified:** {total_datasets}\n"
        section += f"- **Transformations Tracked:** {total_transformations}\n"
        
        # Analysis duration
        duration = analysis_metadata.get('analysis_duration')
        if duration:
            section += f"- **Analysis Duration:** {duration}\n"
        
        return section
    
    def _write_question_section(
        self,
        question_number: int,
        question_title: str,
        answer_data: Dict[str, Any]
    ) -> str:
        """
        Write a single Day-One question section.
        
        Args:
            question_number: Question number (1-5)
            question_title: Title of the question
            answer_data: Dictionary with 'answer', 'evidence', 'provenance'
        
        Returns:
            Question section as string
        """
        section = f"## Question {question_number}: {question_title}\n\n"
        
        # Answer
        answer = answer_data.get('answer', 'No answer available.')
        section += f"### Answer\n\n{answer}\n\n"
        
        # Evidence with citations
        evidence = answer_data.get('evidence', [])
        if evidence:
            section += "### Evidence\n\n"
            section += self.format_evidence_citations(evidence)
            section += "\n"
        
        # Provenance metadata
        provenance = answer_data.get('provenance')
        if provenance:
            section += "### Confidence\n\n"
            # Handle both dict and ProvenanceMetadata objects
            if isinstance(provenance, dict):
                section += f"- **Evidence Type:** {provenance.get('evidence_type', 'unknown')}\n"
                section += f"- **Confidence Score:** {provenance.get('confidence', 0.0):.2f}\n"
                section += f"- **Resolution Status:** {provenance.get('resolution_status', 'unknown')}\n"
            else:
                section += f"- **Evidence Type:** {provenance.evidence_type}\n"
                section += f"- **Confidence Score:** {provenance.confidence:.2f}\n"
                section += f"- **Resolution Status:** {provenance.resolution_status}\n"
        
        return section
    
    def format_evidence_citations(self, evidence: List[Dict[str, Any]]) -> str:
        """
        Format evidence citations with file:line references.
        
        Args:
            evidence: List of evidence dictionaries with file and line_range information
        
        Returns:
            Formatted evidence citations as string
        """
        if not evidence:
            return "No evidence available.\n"
        
        citations = []
        
        for i, ev in enumerate(evidence, 1):
            citation = f"{i}. "
            
            # Format based on evidence type
            ev_type = ev.get('type', 'unknown')
            
            if ev_type == 'data_source':
                citation += f"**Data Source:** `{ev['name']}` ({ev.get('storage_type', 'unknown')})\n"
                citation += f"   - Location: `{ev['file']}`"
                if ev.get('line_range'):
                    citation += f":{ev['line_range'][0]}-{ev['line_range'][1]}"
                citation += "\n"
                citation += f"   - Confidence: {ev.get('confidence', 0.0):.2f}\n"
            
            elif ev_type == 'ingestion_transformation':
                citation += f"**Ingestion:** {ev.get('transformation_type', 'unknown')} transformation\n"
                citation += f"   - Location: `{ev['file']}`:{ev['line_range'][0]}-{ev['line_range'][1]}\n"
                citation += f"   - Sources: {', '.join(ev.get('sources', []))}\n"
                citation += f"   - Confidence: {ev.get('confidence', 0.0):.2f}\n"
            
            elif ev_type == 'critical_output_dataset':
                citation += f"**Critical Output:** `{ev['name']}` ({ev.get('storage_type', 'unknown')})\n"
                citation += f"   - Location: `{ev['file']}`"
                if ev.get('line_range'):
                    citation += f":{ev['line_range'][0]}-{ev['line_range'][1]}"
                citation += "\n"
                citation += f"   - Confidence: {ev.get('confidence', 0.0):.2f}\n"
            
            elif ev_type == 'critical_module':
                citation += f"**Critical Module:** `{ev['path']}`\n"
                citation += f"   - PageRank Score: {ev.get('pagerank', 0.0):.4f}\n"
                if ev.get('exports'):
                    citation += f"   - Key Exports: {', '.join(ev['exports'][:5])}\n"
                citation += f"   - Location: `{ev['file']}`"
                if ev.get('line_range'):
                    citation += f":{ev['line_range'][0]}-{ev['line_range'][1]}"
                citation += "\n"
            
            elif ev_type in ['module_blast_radius', 'lineage_blast_radius']:
                citation += f"**Blast Radius:** `{ev['node']}`\n"
                affected = ev.get('affected_count', ev.get('affected_modules', 0))
                citation += f"   - Affected Components: {affected}\n"
                if ev.get('affected_list'):
                    citation += f"   - Examples: {', '.join(ev['affected_list'][:5])}\n"
                citation += f"   - Location: `{ev['file']}`\n"
            
            elif ev_type == 'matching_module':
                citation += f"**Matching Module:** `{ev['path']}`\n"
                citation += f"   - Purpose: {ev.get('purpose', 'N/A')}\n"
                citation += f"   - Domain: {ev.get('domain_cluster', 'Unknown')}\n"
                citation += f"   - Location: `{ev['file']}`"
                if ev.get('line_range'):
                    citation += f":{ev['line_range'][0]}-{ev['line_range'][1]}"
                citation += "\n"
            
            elif ev_type == 'matching_export':
                citation += f"**Matching Export:** `{ev.get('export', 'unknown')}` in `{ev['path']}`\n"
                citation += f"   - Domain: {ev.get('domain_cluster', 'Unknown')}\n"
                citation += f"   - Location: `{ev['file']}`"
                if ev.get('line_range'):
                    citation += f":{ev['line_range'][0]}-{ev['line_range'][1]}"
                citation += "\n"
            
            elif ev_type == 'domain_cluster':
                citation += f"**Domain:** {ev['domain']}\n"
                citation += f"   - Module Count: {ev.get('module_count', 0)}\n"
                if ev.get('representative_modules'):
                    citation += "   - Representative Modules:\n"
                    for mod in ev['representative_modules'][:3]:
                        citation += f"     - `{mod['path']}`: {mod.get('purpose', 'N/A')}\n"
            
            elif ev_type == 'high_velocity_module':
                citation += f"**High-Change File:** `{ev['path']}`\n"
                citation += f"   - Commit Count: {ev.get('change_velocity', 0)}\n"
                if ev.get('purpose'):
                    citation += f"   - Purpose: {ev['purpose']}\n"
                citation += f"   - Location: `{ev['file']}`"
                if ev.get('line_range'):
                    citation += f":{ev['line_range'][0]}-{ev['line_range'][1]}"
                citation += "\n"
            
            elif ev_type == 'pareto_analysis':
                citation += "**Pareto Analysis:**\n"
                citation += f"   - {ev.get('pareto_percentage', 0):.1f}% of files account for 80% of changes\n"
                if ev.get('pareto_files'):
                    citation += f"   - High-change files: {', '.join([f'`{f}`' for f in ev['pareto_files'][:5]])}\n"
            
            else:
                # Generic evidence formatting
                citation += f"**{ev_type}:** "
                if 'file' in ev:
                    citation += f"`{ev['file']}`"
                    if ev.get('line_range'):
                        citation += f":{ev['line_range'][0]}-{ev['line_range'][1]}"
                citation += "\n"
            
            citations.append(citation)
        
        return "\n".join(citations)
    
    def _write_coverage_summary(
        self,
        day_one_answers: Dict[str, Dict[str, Any]],
        analysis_metadata: Dict[str, Any]
    ) -> str:
        """
        Write coverage summary section.
        
        Args:
            day_one_answers: All Day-One question answers
            analysis_metadata: Analysis metadata
        
        Returns:
            Coverage summary section as string
        """
        section = "## Coverage Summary\n\n"
        
        # Count answered questions
        total_questions = 5
        answered_questions = len([
            q for q in ['ingestion_path', 'critical_outputs', 'blast_radius', 
                       'logic_distribution', 'change_velocity']
            if q in day_one_answers and day_one_answers[q].get('answer')
        ])
        
        section += f"- **Questions Answered:** {answered_questions}/{total_questions}\n"
        
        # Count total evidence pieces
        total_evidence = sum(
            len(answer.get('evidence', []))
            for answer in day_one_answers.values()
        )
        section += f"- **Total Evidence Citations:** {total_evidence}\n"
        
        # Average confidence — handle both dict (JSON round-trip) and ProvenanceMetadata objects
        confidences = []
        for answer in day_one_answers.values():
            provenance = answer.get('provenance')
            if not provenance:
                continue
            if isinstance(provenance, dict):
                c = provenance.get('confidence')
            else:
                c = getattr(provenance, 'confidence', None)
            if c is not None:
                confidences.append(c)
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            section += f"- **Average Confidence:** {avg_confidence:.2f}\n"
        
        # Analysis completeness
        total_modules = analysis_metadata.get('total_modules', 0)
        if total_modules > 0:
            section += f"\n**Analysis Completeness:** This brief covers {total_modules} modules "
            section += f"across the entire codebase.\n"
        
        return section
