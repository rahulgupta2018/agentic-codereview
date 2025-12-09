"""
Simplified Sequential Pipeline Orchestrator

Following simplified deterministic architecture - see SIMPLIFIED_SEQUENTIAL_PIPELINE_DESIGN.md

PRIORITY: GitHub Pipeline (Production Integration)
EXECUTION: Sequential (Deterministic, Predictable)

Architecture:
-----------
✅ GitHubPRReviewPipeline (SequentialAgent) - ROOT AGENT:
  ├─ github_fetcher_agent                    (Step 1: Fetch PR data)
  ├─ AnalysisPipeline (SequentialAgent)      (Step 2: Run all analyses)
  │   ├─ security_agent                      (Always runs)
  │   ├─ code_quality_agent                  (Always runs)
  │   ├─ engineering_agent                   (Always runs)
  │   └─ carbon_agent                        (Always runs)
  ├─ report_synthesizer_agent                (Step 3: Synthesize report)
  └─ github_publisher_agent                  (Step 4: Publish to GitHub)

Design: Simple, deterministic, maintainable.
All agents run every time - no dynamic routing or planning complexity.

DISABLED Components (kept for reference):
- ❌ classifier_agent (not needed for GitHub webhooks)
- ❌ planning_agent (not needed - all agents run every time)
- ❌ dynamic_router_agent (not needed - simple sequential execution)

Key Design Principles:
- ✅ Deterministic workflows - same agents, same order, every time
- ✅ No LLM-based routing decisions
- ✅ ADK built-in artifact system
- ✅ Clear separation: Fetch → Analyze → Report → Publish
- ✅ Nested AnalysisPipeline for maintainability
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from google.adk.agents import SequentialAgent, ParallelAgent, Agent

# Setup logging
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# NOTE: Service initialization removed - ADK provides these when running via `adk api_server`
# The adk api_server command initializes session and artifact services automatically
# based on command-line arguments (--session_service_uri, etc.)
# 
# If you need to run this orchestrator standalone (without adk api_server),
# uncomment the following lines:
#
# from util.artifact_service import FileArtifactService
# from util.session import JSONFileSessionService
# from util.service_registry import register_services
# _artifact_service = FileArtifactService(base_dir="../storage_bucket/artifacts")
# _session_service = JSONFileSessionService(uri="jsonfile://../storage_bucket")
# register_services(artifact_service=_artifact_service, session_service=_session_service)
# logger.info("✅ Services initialized: FileArtifactService and JSONFileSessionService")

logger.info("ℹ️  [Orchestrator] Using ADK-provided services (session + artifact)")

# Import sub-agents for simplified sequential pipeline
from .sub_agents.github_fetcher_agent.agent import github_fetcher_agent
from .sub_agents.github_publisher_agent.agent import github_publisher_agent
from .sub_agents.github_data_adapter_agent.agent import github_data_adapter_agent
from .sub_agents.security_agent.agent import security_agent
from .sub_agents.code_quality_agent.agent import code_quality_agent
from .sub_agents.engineering_practices_agent.agent import engineering_practices_agent
from .sub_agents.carbon_emission_agent.agent import carbon_emission_agent
from .sub_agents.artifact_saver_agent.agent import artifact_saver_agent
from .sub_agents.report_saver_agent.agent import report_saver_agent
from .sub_agents.report_synthesizer_agent.agent import create_report_synthesizer_agent

# DISABLED: Simplified sequential pipeline - see SIMPLIFIED_SEQUENTIAL_PIPELINE_DESIGN.md
# These components are not needed in the deterministic pipeline:
# from .sub_agents.classifier_agent.agent import classifier_agent
# from .sub_agents.planning_agent.agent import create_planning_agent
# from .sub_agents.dynamic_router_agent.agent import DynamicRouterAgent


# =========================================================================
# CODE REVIEW ORCHESTRATOR CLASS
# =========================================================================

class CodeReviewOrchestrator:
    """
    Simplified sequential pipeline orchestrator.
    
    Architecture: Simple, deterministic, maintainable
    - All analysis agents run in sequence, every time
    - No dynamic routing or planning complexity
    - Clear flow: Fetch → Analyze → Report → Publish
    
    See: SIMPLIFIED_SEQUENTIAL_PIPELINE_DESIGN.md
    """
    
    def __init__(self):
        """Initialize orchestrator with simplified sequential pipeline."""
        
        logger.info("="*80)
        logger.info("🚀 [Orchestrator.__init__] STARTING Orchestrator Initialization")
        logger.info("="*80)
        
        # =====================================================================
        # LOAD SUB-AGENTS
        # =====================================================================
        
        # Step 1: GitHub Fetcher
        self.github_fetcher_agent = github_fetcher_agent
        logger.info("✅ [Orchestrator] GitHub fetcher loaded")
        
        # Step 2: Analysis agents (will be nested in AnalysisPipeline)
        self.github_data_adapter_agent = github_data_adapter_agent
        self.security_agent = security_agent
        self.code_quality_agent = code_quality_agent
        self.engineering_agent = engineering_practices_agent
        self.carbon_agent = carbon_emission_agent
        logger.info("✅ [Orchestrator] GitHub data adapter loaded")
        logger.info("✅ [Orchestrator] Analysis agents loaded (4 agents)")
        
        # Step 3: Artifact Saver (saves analysis results to disk)
        self.artifact_saver = artifact_saver_agent
        logger.info("✅ [Orchestrator] Artifact saver loaded")
        
        # Step 4: Report Synthesizer
        self.report_synthesizer = create_report_synthesizer_agent()
        logger.info("✅ [Orchestrator] Report synthesizer loaded")
        
        # Step 5: Report Saver (saves final report to disk)
        self.report_saver = report_saver_agent
        logger.info("✅ [Orchestrator] Report saver loaded")
        
        # Step 4: GitHub Publisher
        self.github_publisher = github_publisher_agent
        logger.info("✅ [Orchestrator] GitHub publisher loaded")
        
        # =====================================================================
        # DISABLED COMPONENTS (kept for reference)
        # =====================================================================
        # These are commented out but not deleted - see SIMPLIFIED_SEQUENTIAL_PIPELINE_DESIGN.md
        #
        # self.classifier = classifier_agent  # Not needed for GitHub webhooks
        # self.planning_agent = create_planning_agent()  # Not needed - all agents run
        # self.dynamic_router = DynamicRouterAgent(...)  # Not needed - simple sequential
        # self.analysis_agent_registry = {...}  # Not needed - no dynamic routing
        
        logger.info("ℹ️  [Orchestrator] Disabled: classifier, planning, dynamic router (see design doc)")
        
        # =====================================================================
        # BUILD SIMPLIFIED SEQUENTIAL PIPELINE
        # =====================================================================
        
        # Create nested analysis pipeline first
        self.analysis_pipeline = self._create_analysis_pipeline()
        agent_count = len(self.analysis_pipeline.sub_agents) if hasattr(self.analysis_pipeline, 'sub_agents') else 0
        logger.info(f"✅ [Orchestrator] Analysis pipeline created (nested) with {agent_count} agents")
        if agent_count > 0:
            agent_names = [a.name for a in self.analysis_pipeline.sub_agents]
            logger.info(f"   └─ Agents: {', '.join(agent_names)}")
        
        # Create main GitHub PR review pipeline
        logger.info("🔧 [Orchestrator.__init__] Creating main GitHub PR review pipeline...")
        self.root_agent = self._create_github_pr_review_pipeline()
        logger.info(f"✅ [Orchestrator.__init__] Root agent created: {self.root_agent.name}")
        logger.info("="*80)
        logger.info("✅ [Orchestrator.__init__] Initialization COMPLETE")
        logger.info("="*80)
    
    # =========================================================================
    # PIPELINE CONSTRUCTION
    # =========================================================================
    
    def _create_analysis_pipeline(self) -> SequentialAgent:
        """
        Create nested analysis pipeline.
        
        Encapsulates data adapter + all 4 analysis agents for maintainability.
        All agents run sequentially, every time (deterministic).
        
        Pipeline Flow:
        0. GitHub Data Adapter → Transform PR data for analysis tools
        1. Security Agent
        2. Code Quality Agent
        3. Engineering Practices Agent
        4. Carbon Emission Agent
        """
        logger.info("🔧 [_create_analysis_pipeline] Building nested AnalysisPipeline...")
        logger.info(f"   Agent 0: {self.github_data_adapter_agent.name}")
        logger.info(f"   Agent 1: {self.security_agent.name}")
        logger.info(f"   Agent 2: {self.code_quality_agent.name}")
        logger.info(f"   Agent 3: {self.engineering_agent.name}")
        logger.info(f"   Agent 4: {self.carbon_agent.name}")
        
        pipeline = SequentialAgent(
            name="AnalysisPipeline",
            sub_agents=[
                self.github_data_adapter_agent,  # Step 0: Prepare data
                self.security_agent,              # Step 1: Security
                self.code_quality_agent,          # Step 2: Quality
                self.engineering_agent,           # Step 3: Engineering
                self.carbon_agent,                # Step 4: Carbon
            ],
            description="Transform GitHub PR data and run all code analysis agents sequentially"
        )
        
        logger.info(f"✅ [_create_analysis_pipeline] Created AnalysisPipeline with {len(pipeline.sub_agents)} sub-agents")
        return pipeline
    
    def _create_github_pr_review_pipeline(self) -> SequentialAgent:
        """
        Create main GitHub PR review pipeline.
        
        Simple, deterministic, easy to understand.
        
        Pipeline Flow:
        1. GitHub Fetcher → Fetch PR data from GitHub API
        2. Analysis Pipeline → Run all 5 analysis agents (nested: adapter + 4 analyses)
        3. Artifact Saver → Save all analysis results to disk
        4. Report Synthesizer → Generate comprehensive markdown report
        5. GitHub Publisher → Post review to GitHub PR (DISABLED - not yet implemented)
        
        Design: All agents run every time, no dynamic routing.
        """
        logger.info("🔧 [_create_github_pr_review_pipeline] Building GitHubPRReviewPipeline...")
        logger.info(f"   Step 1: {self.github_fetcher_agent.name}")
        logger.info(f"   Step 2: {self.analysis_pipeline.name} (nested with {len(self.analysis_pipeline.sub_agents)} agents)")
        logger.info(f"   Step 3: {self.artifact_saver.name}")
        logger.info(f"   Step 4: {self.report_synthesizer.name}")
        logger.info(f"   Step 5: {self.report_saver.name}")
        logger.info("   Step 6: github_publisher (DISABLED)")
        
        pipeline = SequentialAgent(
            name="GitHubPRReviewPipeline",
            sub_agents=[
                self.github_fetcher_agent,  # Step 1: Fetch
                self.analysis_pipeline,     # Step 2: Analyze (nested!)
                self.artifact_saver,        # Step 3: Save analysis artifacts
                self.report_synthesizer,    # Step 4: Generate report
                self.report_saver,          # Step 5: Save report to disk
                # self.github_publisher,    # Step 6: Publish (DISABLED - GitHub integration not yet implemented)
            ],
            description="Complete GitHub PR review workflow - simplified sequential pipeline"
        )
        
        logger.info(f"✅ [_create_github_pr_review_pipeline] Created GitHubPRReviewPipeline with {len(pipeline.sub_agents)} top-level steps")
        return pipeline
    
    # =========================================================================
    # EXECUTION METHODS
    # =========================================================================
    
    def get_agent(self) -> Agent:
        """
        Get the root agent for ADK Runner.
        
        Returns the simplified sequential GitHub PR review pipeline.
        """
        logger.info(f"📤 [get_agent] Returning root_agent: {self.root_agent.name}")
        logger.info(f"   Root agent has {len(self.root_agent.sub_agents) if hasattr(self.root_agent, 'sub_agents') else 0} sub-agents")
        return self.root_agent
    
    def get_github_pipeline(self) -> SequentialAgent:
        """
        Get the GitHub PR review pipeline.
        
        Returns the simplified sequential pipeline (same as root).
        """
        logger.info(f"📤 [get_github_pipeline] Returning GitHub pipeline: {self.root_agent.name}")
        return self.root_agent


# =========================================================================
# MODULE-LEVEL EXPORTS
# =========================================================================

logger.info("")
logger.info("🔥 [MODULE] Creating singleton CodeReviewOrchestrator instance...")
logger.info("🔥 [MODULE] This happens when agent.py is imported by ADK")
logger.info("")

# Create singleton orchestrator instance
_orchestrator = CodeReviewOrchestrator()

# Export root_agent for backward compatibility and ADK CLI
logger.info("📤 [MODULE] Calling _orchestrator.get_agent() to export root_agent...")
root_agent = _orchestrator.get_agent()
orchestrator_agent = root_agent  # Alias for backward compatibility

# Export orchestrator for programmatic access
orchestrator = _orchestrator

logger.info("")
logger.info("🎯 [MODULE] Module-level exports complete:")
logger.info(f"   root_agent = {root_agent.name}")
logger.info(f"   orchestrator_agent = {orchestrator_agent.name}")
logger.info(f"   orchestrator = <CodeReviewOrchestrator instance>")

analysis_count = len(_orchestrator.analysis_pipeline.sub_agents) if hasattr(_orchestrator.analysis_pipeline, 'sub_agents') else 0
logger.info("")
logger.info("✅ [Orchestrator] Simplified Sequential Pipeline ready")
logger.info(f"✅ [Orchestrator] Root agent: {root_agent.name}")
logger.info(f"✅ [Orchestrator] Pipeline: Fetch → Analyze ({analysis_count} agents) → Report → Publish")
logger.info("ℹ️  [Orchestrator] All agents run deterministically - no dynamic routing")
logger.info("")
