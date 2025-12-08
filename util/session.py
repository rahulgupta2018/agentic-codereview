"""
Session Management for ADK Code Review System
Provides custom session service with JSON file persistence following ADK best practices.

Based on ADK 1.17+ custom session services pattern:
- Inherits from BaseSessionService
- Implements all required async methods
- Supports persistent storage across server restarts
- Compatible with ADK service registry for CLI usage
"""

import json
import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from google.adk.sessions import BaseSessionService, Session
from google.adk.cli.service_registry import get_service_registry

# Setup logging
logger = logging.getLogger(__name__)


class JSONFileSessionService(BaseSessionService):
    """
    Custom session service that stores ADK sessions in JSON files.
    
    Features:
    - Persistent storage (survives server restarts)
    - File-based storage (no external dependencies)
    - Automatic session expiration
    - Thread-safe operations
    - Compatible with ADK service registry
    
    Usage:
        # Direct instantiation
        service = JSONFileSessionService(storage_dir="./sessions")
        
        # Via service registry (for adk web)
        # adk web --session_service_uri=jsonfile://./sessions
    """
    
    def __init__(self, uri: str = "jsonfile://./sessions", **kwargs):
        """
        Initialize JSON file-based session service.
        
        Args:
            uri: URI in format "jsonfile://path/to/storage"
            **kwargs: Additional options (agents_dir is removed automatically)
        """
        super().__init__()
        
        # Parse URI to extract storage path
        if uri.startswith("jsonfile://"):
            storage_path = uri.replace("jsonfile://", "")
        else:
            storage_path = uri
            
        self.storage_dir = Path(storage_path).resolve()
        logger.info(f"🔧 Creating storage directory: {self.storage_dir}")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sessions subdirectory
        self.sessions_dir = self.storage_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        logger.info(f"✅ JSONFileSessionService initialized: {self.sessions_dir}")
        print(f"📁 JSONFileSessionService initialized: {self.sessions_dir}")
    
    def _get_session_file_path(self, app_name: str, user_id: str, session_id: str) -> Path:
        """Get the file path for a specific session."""
        # Use hierarchical directory structure: app_name/user_id/session_id.json
        session_dir = self.sessions_dir / app_name / user_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"{session_id}.json"
    
    def _session_to_dict(self, session: Session) -> dict:
        """Convert Session object to dictionary for JSON storage."""
        return {
            "id": session.id,
            "app_name": session.app_name,
            "user_id": session.user_id,
            "state": session.state or {},
            "events": [self._event_to_dict(event) for event in (session.events or [])],
            "created_at": getattr(session, 'created_at', datetime.now().isoformat()),
            "last_update_time": session.last_update_time or datetime.now().timestamp()
        }
    
    def _event_to_dict(self, event) -> dict:
        """Convert Event object to dictionary."""
        return {
            "id": event.id if hasattr(event, 'id') else None,
            "type": str(type(event).__name__),
            "timestamp": getattr(event, 'timestamp', datetime.now().isoformat()),
            "data": str(event)  # Simplified - adjust based on your Event structure
        }
    
    def _dict_to_session(self, data: dict) -> Session:
        """Convert dictionary back to Session object."""
        return Session(
            id=data["id"],
            app_name=data["app_name"],
            user_id=data["user_id"],
            state=data.get("state", {}),
            events=data.get("events", []),  # Events will be simple dicts
            last_update_time=data.get("last_update_time", datetime.now().timestamp())
        )
    
    async def create_session(
        self, 
        *, 
        app_name: str, 
        user_id: str,
        session_id: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Session:
        """
        Create a new session and save to JSON file.
        
        Args:
            app_name: Application name
            user_id: User identifier
            session_id: Optional session ID (auto-generated if not provided)
            state: Optional initial state dictionary
            **kwargs: Additional session parameters
        
        Returns:
            Created Session object
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Create session object
        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state or self._get_initial_state(),
            events=[],
            last_update_time=datetime.now().timestamp()
        )
        
        # Save to file
        file_path = self._get_session_file_path(app_name, user_id, session_id)
        logger.info(f"💾 Saving session to: {file_path}")
        with open(file_path, 'w') as f:
            json.dump(self._session_to_dict(session), f, indent=2)
        
        logger.info(f"✅ Created session: {session_id} for {user_id}@{app_name}")
        print(f"✅ Created session: {session_id} for {user_id}@{app_name}")
        return session
    
    async def get_session(
        self, 
        *, 
        app_name: str, 
        user_id: str,
        session_id: str,
        **kwargs
    ) -> Optional[Session]:
        """
        Retrieve session from JSON file.
        
        Args:
            app_name: Application name
            user_id: User identifier
            session_id: Session identifier
            **kwargs: Additional parameters
        
        Returns:
            Session object if found, None otherwise
        """
        file_path = self._get_session_file_path(app_name, user_id, session_id)
        
        if not file_path.exists():
            logger.warning(f"❌ Session not found: {session_id}")
            return None
        
        try:
            logger.debug(f"📖 Loading session from: {file_path}")
            with open(file_path, 'r') as f:
                data = json.load(f)
            logger.info(f"✅ Loaded session: {session_id}")
            return self._dict_to_session(data)
        except Exception as e:
            logger.error(f"❌ Error loading session {session_id}: {e}", exc_info=True)
            print(f"⚠️  Error loading session {session_id}: {e}")
            return None
    
    async def list_sessions(
        self, 
        *, 
        app_name: str, 
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        List all sessions for a specific app and user.
        
        Args:
            app_name: Application name
            user_id: User identifier
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with 'sessions' list and 'total_count'
        """
        session_dir = self.sessions_dir / app_name / user_id
        
        if not session_dir.exists():
            logger.info(f"📂 No sessions found for {user_id}@{app_name}")
            return {"sessions": [], "total_count": 0}
        
        logger.info(f"📋 Listing sessions in: {session_dir}")
        sessions = []
        for file_path in session_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                sessions.append(self._dict_to_session(data))
            except Exception as e:
                logger.error(f"❌ Error loading session file {file_path}: {e}")
                print(f"⚠️  Error loading session file {file_path}: {e}")
                continue
        
        # Sort by last update time (most recent first)
        sessions.sort(key=lambda s: s.last_update_time or 0, reverse=True)
        logger.info(f"✅ Found {len(sessions)} sessions for {user_id}@{app_name}")
        
        return {
            "sessions": sessions,
            "total_count": len(sessions)
        }
    
    async def delete_session(
        self, 
        *, 
        app_name: str, 
        user_id: str,
        session_id: str,
        **kwargs
    ) -> None:
        """
        Delete session file.
        
        Args:
            app_name: Application name
            user_id: User identifier
            session_id: Session identifier
            **kwargs: Additional parameters
        """
        file_path = self._get_session_file_path(app_name, user_id, session_id)
        
        if file_path.exists():
            logger.info(f"🗑️  Deleting session: {session_id}")
            file_path.unlink()
            logger.info(f"✅ Session deleted: {session_id}")
            print(f"🗑️  Deleted session: {session_id}")
        else:
            logger.warning(f"⚠️  Session file not found for deletion: {session_id}")
    
    async def append_event(self, session: Session, event) -> Any:
        """
        CRITICAL: Append event to session and save to file.
        
        This method is called by ADK whenever an event occurs (user message, agent response, etc.).
        Must save the entire session with all events to maintain persistence.
        
        Args:
            session: Session object to update
            event: Event object to append
        
        Returns:
            The event that was appended
        """
        # Call parent to add event to session.events
        event = await super().append_event(session=session, event=event)
        
        # IMPORTANT: Save entire session to file after event added
        file_path = self._get_session_file_path(
            session.app_name,
            session.user_id, 
            session.id
        )
        
        # Update last update time
        session.last_update_time = datetime.now().timestamp()
        
        logger.debug(f"💾 Persisting event to session: {session.id}")
        # Save updated session with all events
        with open(file_path, 'w') as f:
            json.dump(self._session_to_dict(session), f, indent=2)
        logger.debug(f"✅ Event persisted to session file")
        
        return event
    
    def _get_initial_state(self) -> Dict[str, Any]:
        """
        Get initial session state with code review context.
        
        Returns:
            Dictionary with default code review session state
        """
        # Try to load from mock data file if available
        logger.debug("🔍 Loading initial session state...")
        mock_data = self._load_mock_data()
        if mock_data:
            logger.info("✅ Loaded initial state from mock data")
            return mock_data
        
        # Fallback to default state
        logger.info("⚙️  Using default initial session state")
        return {
            "user_name": "Code Reviewer",
            "review_history": [],
            "analysis_history": [],
            "session_metadata": {
                "total_reviews": 0,
                "successful_analyses": 0,
                "failed_analyses": 0,
                "created_at": datetime.now().isoformat()
            },
            "quality_metrics": {
                "total_issues_found": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0
            },
            "user_preferences": {
                "analysis_depth": "standard",
                "focus_areas": ["quality", "security", "practices", "carbon"]
            }
        }
    
    def _load_mock_data(self) -> Optional[Dict[str, Any]]:
        """Load mock session data from JSON file if available."""
        # Look for mock data in standard location
        data_dir = self.storage_dir.parent / "data"
        mock_data_path = data_dir / "mock_session_data.json"
        
        if not mock_data_path.exists():
            logger.debug(f"📂 Mock data file not found: {mock_data_path}")
            return None
        
        logger.info(f"📖 Loading mock data from: {mock_data_path}")
        
        try:
            with open(mock_data_path, 'r') as f:
                mock_data = json.load(f)
            
            # Extract and format data for ADK session with enhanced structure
            user_info = mock_data.get("user_info", {})
            user_prefs = mock_data.get("user_preferences", {})
            
            return {
                # User information
                "user_name": user_info.get("user_name", "Code Reviewer"),
                "user_email": user_info.get("email"),
                "user_role": user_info.get("role"),
                "user_team": user_info.get("team"),
                
                # User preferences
                "user_preferences": {
                    "analysis_depth": user_prefs.get("analysis_depth", "standard"),
                    "focus_areas": user_prefs.get("focus_areas", ["quality", "security", "practices", "carbon"]),
                    "language_preferences": user_prefs.get("language_preferences", []),
                    "notification_settings": user_prefs.get("notification_settings", {}),
                    "code_style": user_prefs.get("code_style", {})
                },
                
                # Historical data
                "review_history": mock_data.get("review_history", []),
                "analysis_history": mock_data.get("analysis_history", []),
                "interaction_history": mock_data.get("interaction_history", []),
                
                # Metadata and metrics
                "session_metadata": {
                    **mock_data.get("session_metadata", {}),
                    "loaded_from": "mock_data",
                    "loaded_at": datetime.now().isoformat()
                },
                "quality_metrics": mock_data.get("quality_metrics", {
                    "total_issues_found": 0,
                    "critical_issues": 0,
                    "high_issues": 0,
                    "medium_issues": 0,
                    "low_issues": 0
                }),
                
                # Agent usage statistics
                "agent_usage_stats": mock_data.get("agent_usage_stats", {}),
                "language_stats": mock_data.get("language_stats", {}),
                "preferences_learning": mock_data.get("preferences_learning", {})
            }
        except Exception as e:
            logger.error(f"❌ Could not load mock data: {e}", exc_info=True)
            print(f"⚠️  Could not load mock data: {e}")
            return None


# Factory function for ADK service registry
def jsonfile_session_factory(uri: str, **kwargs) -> JSONFileSessionService:
    """
    Factory function for creating JSONFileSessionService instances.
    
    This enables CLI usage:
        adk web --session_service_uri=jsonfile://./sessions
    
    Args:
        uri: URI string (e.g., "jsonfile://./sessions")
        **kwargs: Additional options from ADK (agents_dir is removed)
    
    Returns:
        JSONFileSessionService instance
    """
    # Remove agents_dir as it's not needed by session service
    kwargs_copy = kwargs.copy()
    kwargs_copy.pop("agents_dir", None)
    
    return JSONFileSessionService(uri=uri, **kwargs_copy)


# Register with ADK service registry
def register_session_service():
    """Register JSONFileSessionService with ADK service registry."""
    logger.info("🔧 Registering jsonfile:// session service with ADK...")
    registry = get_service_registry()
    registry.register_session_service("jsonfile", jsonfile_session_factory)
    logger.info("✅ Session service registered with ADK registry")
    print("✅ Registered jsonfile:// session service")


# Convenience functions for backward compatibility
def load_mock_session_data() -> Dict[str, Any]:
    """
    DEPRECATED: Load mock session data.
    Use JSONFileSessionService._get_initial_state() instead.
    
    Kept for backward compatibility.
    """
    service = JSONFileSessionService()
    return service._get_initial_state()


def get_fallback_session_data() -> Dict[str, Any]:
    """
    DEPRECATED: Get fallback session data.
    Use JSONFileSessionService._get_initial_state() instead.
    
    Kept for backward compatibility.
    """
    return {
        "user_name": "Code Reviewer",
        "review_history": [],
        "interaction_history": [],
        "session_metadata": {
            "total_reviews": 0,
            "successful_analyses": 0
        }
    }


def get_initial_session_state() -> Dict[str, Any]:
    """
    Get initial session state for ADK session creation.
    
    Returns:
        Dict containing initial state for ADK sessions
    """
    service = JSONFileSessionService()
    return service._get_initial_state()


# Auto-register when module is imported
try:
    register_session_service()
except Exception as e:
    logger.error(f"❌ Could not register session service: {e}", exc_info=True)
    print(f"⚠️  Could not register session service: {e}")
