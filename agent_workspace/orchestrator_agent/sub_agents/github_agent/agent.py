"""GitHub Integration Agent 

Handling GitHub PR Interactions and posting review results back to GitHub. 
Acts as a bridge between GitHub API and the code review system, facilitating seamless integration for review requests.
"""

import sys
import logging
import os

from pathlib import Path
from typing import Dict, Any, List, Optional
from google.adk.agents import LlmAgent, Agent 
from google.genai import types
from google.adk.tools import FunctionTool

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))  

gh = Github(os.getenv("GITHUB_TOKEN"))
from util.llm_model import get_sub_agent_model

