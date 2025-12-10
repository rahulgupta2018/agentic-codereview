"""
Context Engineering Module

Loads agent-specific knowledge base guidelines and injects them into agent prompts
to improve analysis accuracy and reduce false positives.

Author: AI Toolkit
Date: December 10, 2025
Version: 1.0.0
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """Load and inject domain-specific guidelines into agent prompts."""
    
    def __init__(self, kb_dir: str = None):
        """
        Initialize KnowledgeBaseLoader.
        
        Args:
            kb_dir: Directory containing knowledge base YAML files (relative to project root).
                   If None, reads from KNOWLEDGE_BASE_DIR env var or defaults to "config/knowledge_base"
        """
        # Resolve to absolute path relative to this file's location
        # This file is at: <project_root>/util/context_engineering.py
        # So project_root is one level up
        project_root = Path(__file__).parent.parent
        
        # Get KB directory from env var or use default
        if kb_dir is None:
            kb_dir = os.getenv('KNOWLEDGE_BASE_DIR')
        
        self.kb_dir = project_root / kb_dir
        self._cache = {}
        
        # Map agent types to knowledge base files
        self.kb_mapping = {
            "security_agent": ["security_guidelines.yaml"],
            "code_quality_agent": ["code_quality_guidelines.yaml"],
            "engineering_practices_agent": ["engineering_practices_guidlines.yaml"],
            "carbon_emission_agent": ["carbon_emission_guidlines.yaml"]
        }
        
        logger.info(f"✅ [KnowledgeBaseLoader] Initialized with kb_dir={self.kb_dir}")
    
    def load_guidelines(self, agent_type: str) -> Dict[str, Any]:
        """
        Load guidelines for specific agent type.
        
        Args:
            agent_type: Type of agent (security_agent, code_quality_agent, etc.)
        
        Returns:
            Dictionary containing guidelines from YAML file(s)
        """
        if agent_type in self._cache:
            logger.debug(f"[KnowledgeBaseLoader] Cache hit for {agent_type}")
            return self._cache[agent_type]
        
        kb_files = self.kb_mapping.get(agent_type, [])
        if not kb_files:
            logger.warning(f"⚠️ [KnowledgeBaseLoader] No knowledge base mapping for {agent_type}")
            return {}
        
        guidelines = {}
        for kb_file in kb_files:
            kb_path = self.kb_dir / kb_file
            
            if not kb_path.exists():
                logger.error(f"❌ [KnowledgeBaseLoader] File not found: {kb_path}")
                continue
            
            try:
                with open(kb_path, 'r') as f:
                    data = yaml.safe_load(f)
                    guidelines.update(data)
                    logger.info(f"✅ [KnowledgeBaseLoader] Loaded {kb_file} for {agent_type}")
            except yaml.YAMLError as e:
                logger.error(f"❌ [KnowledgeBaseLoader] YAML parse error in {kb_file}: {e}")
            except Exception as e:
                logger.error(f"❌ [KnowledgeBaseLoader] Error loading {kb_file}: {e}")
        
        self._cache[agent_type] = guidelines
        return guidelines
    
    def format_guidelines_for_prompt(self, guidelines: Dict[str, Any]) -> str:
        """
        Format guidelines as readable text for system prompt.
        
        Args:
            guidelines: Dictionary of guidelines from YAML
        
        Returns:
            Formatted string suitable for injection into agent prompt
        """
        sections = []
        
        # Skip metadata keys
        skip_keys = {'version', 'title', 'last_updated'}
        
        for key, value in guidelines.items():
            if key in skip_keys:
                continue
            
            # Format section header
            section_title = key.replace('_', ' ').title()
            sections.append(f"### {section_title}\n")
            
            # Format section content
            if isinstance(value, dict):
                sections.append(self._format_nested_dict(value, indent=0))
            elif isinstance(value, list):
                sections.append(self._format_list(value, indent=0))
            else:
                sections.append(f"{value}\n")
        
        return "\n".join(sections)
    
    def _format_nested_dict(self, data: Dict[str, Any], indent: int = 0) -> str:
        """
        Recursively format nested dictionary.
        
        Args:
            data: Dictionary to format
            indent: Current indentation level
        
        Returns:
            Formatted string
        """
        lines = []
        prefix = "  " * indent
        
        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()
            
            if isinstance(value, dict):
                lines.append(f"{prefix}**{formatted_key}:**")
                lines.append(self._format_nested_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}**{formatted_key}:**")
                lines.append(self._format_list(value, indent + 1))
            else:
                lines.append(f"{prefix}- **{formatted_key}:** {value}")
        
        return "\n".join(lines)
    
    def _format_list(self, items: List[Any], indent: int = 0) -> str:
        """
        Format list items.
        
        Args:
            items: List to format
            indent: Current indentation level
        
        Returns:
            Formatted string
        """
        lines = []
        prefix = "  " * indent
        
        for item in items:
            if isinstance(item, dict):
                lines.append(self._format_nested_dict(item, indent))
            else:
                lines.append(f"{prefix}- {item}")
        
        return "\n".join(lines)


def inject_knowledge_base_context(agent_type: str, base_instruction: str) -> str:
    """
    Inject knowledge base guidelines into agent instruction.
    
    Args:
        agent_type: Type of agent (security_agent, code_quality_agent, etc.)
        base_instruction: Base instruction text for the agent
    
    Returns:
        Enhanced instruction with knowledge base guidelines injected
    """
    kb_loader = KnowledgeBaseLoader()
    guidelines = kb_loader.load_guidelines(agent_type)
    
    if not guidelines:
        logger.warning(f"⚠️ [inject_knowledge_base_context] No guidelines loaded for {agent_type}")
        return base_instruction
    
    formatted_kb = kb_loader.format_guidelines_for_prompt(guidelines)
    
    enhanced_instruction = f"""{base_instruction}

---

## 📚 DOMAIN KNOWLEDGE BASE

You MUST follow these industry-standard guidelines when analyzing code:

{formatted_kb}

---

**CRITICAL INSTRUCTIONS:**

1. **Identify Issues** - Check code against these guidelines
2. **Avoid False Positives** - Recognize secure/compliant patterns (e.g., parameterized queries, shell=False)
3. **Provide Context** - Reference specific guidelines in findings
4. **Assign Confidence** - Higher confidence when guideline is clearly violated

**CONFIDENCE SCORING (REQUIRED):**

For EVERY finding, you MUST include:
- `confidence_score` (float 0.0-1.0)
- `confidence_reasoning` (string explaining score)

**Confidence Calculation Guidelines:**

HIGH (0.90-1.00):
- Clear violation of knowledge base guideline
- Strong evidence (line number + code snippet + metric)
- Static analyzer tool confirms issue
- Pattern matches known vulnerability/anti-pattern

MEDIUM (0.70-0.89):
- Likely issue based on guidelines
- Moderate evidence (line number + description)
- Context may affect severity
- Pattern is concerning but not definitive

LOW (0.50-0.69):
- Potential issue requiring review
- Weak evidence (general observation)
- Highly context-dependent
- Pattern could be intentional design choice

VERY LOW (0.00-0.49):
- Uncertain or likely false positive
- Insufficient evidence
- May be secure pattern misidentified
- Needs human expert validation

"""
    
    logger.info(f"✅ [inject_knowledge_base_context] Enhanced {agent_type} instruction with KB context")
    return enhanced_instruction


# Module-level singleton for caching
_kb_loader_instance = None


def get_kb_loader() -> KnowledgeBaseLoader:
    """Get or create singleton KnowledgeBaseLoader instance."""
    global _kb_loader_instance
    if _kb_loader_instance is None:
        _kb_loader_instance = KnowledgeBaseLoader()
    return _kb_loader_instance
