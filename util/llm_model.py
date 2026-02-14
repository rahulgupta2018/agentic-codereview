"""
Centralized LLM Model Configuration
This module provides a single place to configure the LLM model for all agents.

New models to try
- qwen3-coder-next
ollama pull qwen3-coder-next
ollama launch claude --model qwen3-coder-next
"""

import os
from google.adk.models.lite_llm import LiteLlm
from google.adk.models import Gemini
from google.genai.types import HttpRetryOptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Model configuration
GEMINI_MODEL = os.environ.get("GEMINI_MODEL")
OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE")
OLLAMA_ENDPOINT = f"{OLLAMA_API_BASE}/api/generate"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")
OLLAMA_SUBAGENT_MODEL = os.environ.get("OLLAMA_SUBAGENT_MODEL")

# Create the model instance that all agents will use
"""
agent_model = LiteLlm(
    model=OLLAMA_MODEL, 
    endpoint=OLLAMA_ENDPOINT,
    temperature=0.4,        # More creative but still focused
    top_p=0.9,
    top_k=40,
    repeat_penalty=1.15,
    max_tokens=2048,
    stream=True
    )

sub_agent_model = LiteLlm(
    model=OLLAMA_SUBAGENT_MODEL, 
    endpoint=OLLAMA_ENDPOINT,
    temperature=0.2,        # Sweet spot for quality + speed
    top_p=0.85,
    top_k=30,
    repeat_penalty=1.15,
    max_tokens=2048,
    stream=False
    )
"""
# Gemini models - ADK will use these with default settings
# Note: Google ADK's Gemini class handles generation_config at the agent level,
# not at model instantiation. Parameters are controlled via agent configuration.
# Configure retry logic for handling 503 (overloaded) and 429 (rate limit) errors
retry_config = HttpRetryOptions(
    attempts=6,                    # Try up to 6 times total (1 initial + 5 retries)
    initial_delay=2.0,             # Start with 2 second delay
    max_delay=60.0,                # Cap at 60 seconds
    exp_base=2.0,                  # Exponential backoff: 2s, 4s, 8s, 16s, 32s, 60s
    jitter=0.2,                    # Add 20% random jitter to avoid thundering herd
    http_status_codes=[503, 429]   # Retry on overloaded (503) and rate limit (429)
)

agent_model = Gemini(
    model=GEMINI_MODEL,
    retry_options=retry_config
)
sub_agent_model = Gemini(
    model=GEMINI_MODEL,
    retry_options=retry_config
)
# Generation config dictionaries for reference and potential runtime use
# These define optimal parameters discovered through testing

ORCHESTRATOR_GENERATION_CONFIG = {
    "temperature": 0.4,        # Balanced for routing decisions
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 2048,
}

SUBAGENT_GENERATION_CONFIG = {
    "temperature": 0.2,        # Low temperature for precise code analysis
    "top_p": 0.85,
    "top_k": 30,
    "max_output_tokens": 2048,
}


def get_agent_model():
    """
    Returns the configured LLM model instance for agents.
    
    Returns:
        LiteLlm: Configured model instance
    """
    return agent_model

def get_sub_agent_model():
    """
    Returns the configured LLM model instance for sub-agents.
    
    Returns:
        LiteLlm: Configured sub-agent model instance
    """
    return sub_agent_model

def get_orchestrator_config():
    """Returns optimal generation config for orchestrator agents."""
    return ORCHESTRATOR_GENERATION_CONFIG

def get_subagent_config():
    """Returns optimal generation config for sub-agents."""
    return SUBAGENT_GENERATION_CONFIG
