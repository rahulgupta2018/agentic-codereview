"""
Deterministic Workflow Orchestrator

Following Google ADK best practices with SequentialAgent and PlanReActPlanner.

PRIORITY: GitHub Pipeline (Production Integration)
EXECUTION: Sequential (Accuracy over Speed)

Architecture:
-----------
✅ GitHubPipeline (SequentialAgent) - ROOT AGENT:
  ├─ github_fetcher_agent
  ├─ planning_agent
  ├─ dynamic_router_agent (SequentialAgent - runs agents one-by-one)
  │   ├─ security_agent          (1st - completes fully)
  │   ├─ code_quality_agent      (2nd - completes fully)
  │   ├─ engineering_agent       (3rd - completes fully)
  │   └─ carbon_agent            (4th - completes fully)
  ├─ report_synthesizer_agent
  └─ github_publisher_agent

Design: Sequential execution prioritizes accuracy over speed.
Each agent completes before the next starts - perfect for async PR reviews.

⏸️  WebPipeline - DEFERRED (ADK single-parent constraint):
  Note: Cannot create both pipelines simultaneously.
  Future: Implement agent cloning pattern.

Key Design Principles:
- ✅ Deterministic workflows using SequentialAgent
- ✅ PlanReActPlanner for intelligent agent selection
- ✅ DynamicRouterAgent for runtime agent selection
- ✅ No custom orchestration logic
- ✅ Pure ADK patterns throughout
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

# Initialize services
from util.artifact_service import FileArtifactService
from util.session import JSONFileSessionService
from util.service_registry import register_services

# Using ../storage_bucket to go up from agent_workspace/ to project root
_artifact_service = FileArtifactService(base_dir="../storage_bucket/artifacts")
# Note: JSONFileSessionService creates a 'sessions' subdirectory inside storage_bucket
_session_service = JSONFileSessionService(uri="jsonfile://../storage_bucket")
register_services(artifact_service=_artifact_service, session_service=_session_service)
logger.info("✅ Services initialized: FileArtifactService and JSONFileSessionService")

# Import all sub-agents
from .sub_agents.github_fetcher_agent.agent import github_fetcher_agent
from .sub_agents.github_publisher_agent.agent import github_publisher_agent
from .sub_agents.classifier_agent.agent import classifier_agent
from .sub_agents.planning_agent.agent import create_planning_agent
from .sub_agents.security_agent.agent import security_agent
from .sub_agents.code_quality_agent.agent import code_quality_agent
from .sub_agents.engineering_practices_agent.agent import engineering_practices_agent
from .sub_agents.carbon_emission_agent.agent import carbon_emission_agent
from .sub_agents.report_synthesizer_agent.agent import create_report_synthesizer_agent
from .sub_agents.dynamic_router_agent.agent import DynamicRouterAgent


# =========================================================================
# CODE REVIEW ORCHESTRATOR CLASS
# =========================================================================

class CodeReviewOrchestrator:
    """
    Deterministic workflow orchestrator using Google ADK patterns.
    
    This orchestrator uses ADK best practices:
    - Uses SequentialAgent for deterministic workflow execution
    - Dynamic routing based on source detection (GitHub vs Web UI)
    - PlanningAgent uses PlanReActPlanner for intelligent agent selection
    - ExecutionPipeline created dynamically based on planning output
    """
    
    def __init__(self):
        """Initialize orchestrator with all sub-agents and workflows."""
        
        logger.info("🚀 [Orchestrator] Initializing Deterministic Workflow Orchestrator")
        
        # =====================================================================
        # PIPELINE-SPECIFIC SUB-AGENTS
        # =====================================================================
        
        # GitHub-specific agents
        self.github_fetcher = github_fetcher_agent
        self.github_publisher = github_publisher_agent
        logger.info("✅ [Orchestrator] GitHub agents loaded")
        
        # Web UI-specific agents
        self.classifier = classifier_agent
        logger.info("✅ [Orchestrator] Classifier agent loaded")
        
        # =====================================================================
        # LEVEL 3: SHARED SUB-AGENTS (used by both pipelines)
        # =====================================================================
        
        # Create separate instances for each pipeline to avoid parent conflicts
        # GitHub planning agent reads from github_pr_data (not request_classification)
        from .sub_agents.planning_agent.agent import planning_agent_github
        self.planning_agent_github = planning_agent_github
        self.planning_agent_web = create_planning_agent("web")
        self.report_synthesizer_github = create_report_synthesizer_agent()
        self.report_synthesizer_web = create_report_synthesizer_agent()
        logger.info("✅ [Orchestrator] Planning and report synthesizer agents loaded")
        
        # =====================================================================
        # LEVEL 4: ANALYSIS SUB-AGENTS (selected dynamically by PlanningAgent)
        # =====================================================================
        
        self.security_agent = security_agent
        self.code_quality_agent = code_quality_agent
        self.engineering_agent = engineering_practices_agent
        self.carbon_agent = carbon_emission_agent
        logger.info("✅ [Orchestrator] Analysis agents loaded")
        
        # =====================================================================
        # AGENT REGISTRY FOR DYNAMIC ROUTING
        # =====================================================================
        
        logger.info("🔧 [Orchestrator] Creating agent registry for dynamic routing...")
        
        self.analysis_agent_registry = {
            "security": self.security_agent,
            "code_quality": self.code_quality_agent,
            "engineering": self.engineering_agent,
            "carbon": self.carbon_agent,
        }
        
        logger.info(f"✅ [Orchestrator] Agent registry created with {len(self.analysis_agent_registry)} agents")
        
        # =====================================================================
        # DYNAMIC ROUTER AGENTS
        # =====================================================================
        
        logger.info("🔧 [Orchestrator] Creating dynamic router agent...")
        
        # Single router instance used in both pipelines
        # All analysis agents run in parallel via ParallelAgent
        self.dynamic_router = DynamicRouterAgent(
            agent_registry=self.analysis_agent_registry
        )
        
        logger.info("✅ [Orchestrator] Dynamic router agent created")
        
        # =====================================================================
        # BUILD WORKFLOW HIERARCHY
        # =====================================================================
        
        # GitHub Pipeline is root for production integration
        # Web Pipeline deferred due to ADK single-parent constraint
        self.root_agent = self._create_github_pipeline()
        logger.info("✅ [Orchestrator] Root agent: GitHubPipeline (production priority)")
        logger.info("⏸️  [Orchestrator] Web pipeline: Deferred (ADK single-parent constraint)")
    
    # =========================================================================
    # WORKFLOW CONSTRUCTION
    # =========================================================================
    
    def _create_github_pipeline(self) -> SequentialAgent:
        """
        Create GitHub webhook processing pipeline.
        
        Pipeline Flow:
        1. GitHubFetcher → Fetch PR data from GitHub
        2. PlanningAgent → Decide which analysis agents to run
        3. DynamicRouterAgent → Read plan, dynamically execute selected agents
        4. ReportSynthesizer → Consolidate results and generate markdown report
        
        NOTE: GitHub Publisher disabled (no GitHub integration configured)
        """
        return SequentialAgent(
            name="GitHubPipeline",
            sub_agents=[
                self.github_fetcher,
                self.planning_agent_github,
                self.dynamic_router,
                self.report_synthesizer_github
                # self.github_publisher  # DISABLED - no GitHub integration
            ],
            description="GitHub webhook processing pipeline with report generation"
        )
    
    def _create_web_pipeline(self) -> SequentialAgent:
        """
        Create Web UI request processing pipeline.
        
        STATUS: DEFERRED - Cannot create due to ADK single-parent constraint.
        GitHub pipeline has priority for production integration.
        
        Pipeline Flow (Future):
        1. Classifier → Classify user intent and code presence
        2. PlanningAgent → Decide which analysis agents to run
        3. DynamicRouterAgent → Execute all agents in parallel
        4. ReportSynthesizer → Consolidate results into markdown report
        
        TODO: Implement agent cloning pattern to support multiple pipelines.
        """
        raise NotImplementedError(
            "Web pipeline deferred due to ADK single-parent constraint. "
            "GitHub pipeline has priority. Use GitHub pipeline with mock data for testing, "
            "or implement agent cloning pattern to support both pipelines."
        )
    
    # =========================================================================
    # EXECUTION METHODS
    # =========================================================================
    
    def get_agent(self) -> Agent:
        """
        Get the root agent for ADK Runner.
        
        This is the entry point for `adk web` and returns WebPipeline.
        """
        return self.root_agent
    
    def get_github_pipeline(self) -> SequentialAgent:
        """
        Get the GitHub pipeline for webhook processing.
        
        This returns the root agent (GitHub pipeline).
        """
        return self.root_agent
    
    def get_web_pipeline(self) -> SequentialAgent:
        """
        Get the Web UI pipeline.
        
        STATUS: Not available due to ADK single-parent constraint.
        """
        raise NotImplementedError(
            "Web pipeline not available. GitHub pipeline is the root agent."
        )


# =========================================================================
# MODULE-LEVEL EXPORTS
# =========================================================================

# Create singleton orchestrator instance
_orchestrator = CodeReviewOrchestrator()

# Export root_agent for backward compatibility and ADK CLI (Web UI)
root_agent = _orchestrator.get_agent()
orchestrator_agent = root_agent  # Alias for backward compatibility

# Export orchestrator for accessing other pipelines programmatically
orchestrator = _orchestrator

# Note: Don't create github_pipeline_agent at module level because
# agents can only have one parent. Call orchestrator.get_github_pipeline()
# when needed in API endpoints.

# Export orchestrator instance for advanced usage
orchestrator = _orchestrator

logger.info("✅ [Orchestrator] Deterministic Workflow Orchestrator ready")
logger.info(f"✅ [Orchestrator] Root agent: {root_agent.name} (GitHub integration)")
logger.info("⏸️  [Orchestrator] Web pipeline: Deferred (ADK single-parent constraint)")
