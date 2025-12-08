import asyncio
import logging

from dotenv import load_dotenv
from google.adk.runners import Runner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the main code review orchestrator agent
from agent_workspace.orchestrator_agent.agent import orchestrator_agent
# Load session service with persistence
from util.session import JSONFileSessionService
# Load artifact service for storing code, reports, and analysis outputs
from util.artifact_service import FileArtifactService
# Service registry for agent access to services
from util.service_registry import register_services

load_dotenv()
logger.info("🔧 Environment variables loaded")

# Using JSON file storage for persistent sessions
# Note: JSONFileSessionService creates a 'sessions' subdirectory inside storage_bucket
# Using ../storage_bucket to go up from agent_workspace/ to project root
logger.info("🔧 Initializing session service...")
session_service = JSONFileSessionService(uri="jsonfile://../storage_bucket")
logger.info(f"✅ Session service initialized: {session_service.base_dir}")

# Using file-based artifact storage for code inputs, reports, and sub-agent outputs
logger.info("🔧 Initializing artifact service...")
artifact_service = FileArtifactService(base_dir="../storage_bucket/artifacts")
logger.info(f"✅ Artifact service initialized: {artifact_service.base_dir}")

# Register services for agent access
logger.info("🔧 Registering services in service registry...")
register_services(artifact_service=artifact_service, session_service=session_service)
logger.info("✅ Services registered successfully")

async def main_async():
    # Setup constants
    APP_NAME = "Code Review System"
    USER_ID = "rahul_gupta_123"
    
    logger.info(f"🚀 Starting {APP_NAME} for user: {USER_ID}")

    # ===== PART 2: Session Creation with Initial State =====
    # Create a new session (initial state loaded from mock data automatically)
    logger.info("🔧 Creating new session...")
    new_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )
    SESSION_ID = new_session.id
    logger.info(f"✅ Session created: {SESSION_ID}")
    print(f"✅ Created new session: {SESSION_ID}")
    print(f"👤 User: {new_session.state.get('user_name', 'Unknown')}")
    print(f"📊 Review History: {len(new_session.state.get('review_history', []))} entries\n")

    # ===== PART 3: Agent Runner Setup =====
    # Create a runner with the main code review orchestrator
    # Now includes artifact service for storing code inputs, reports, and analysis outputs
    logger.info("🔧 Creating ADK Runner with orchestrator agent...")
    runner = Runner(
        agent=orchestrator_agent,
        app_name=APP_NAME,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    logger.info("✅ Runner initialized successfully")
    
    print(f"📁 Artifact storage: {artifact_service.base_dir}")
    print(f"💾 Session storage: ./sessions")

    # ===== PART 4: Interactive Conversation Loop =====
    print("\n🤖 Welcome to AI Code Review System!")
    print("Submit your code for analysis or ask questions about code quality.")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        # Get user input
        user_input = input("You: ")

        # Check if user wants to exit
        if user_input.lower() in ["exit", "quit"]:
            logger.info("👋 User requested exit")
            print("Ending conversation. Goodbye!")
            break

        # Process the user query through the agent
        from google.genai import types
        
        logger.info(f"📥 User input received: {user_input[:100]}{'...' if len(user_input) > 100 else ''}")
        content = types.Content(role="user", parts=[types.Part(text=user_input)])
        print(f"\n🔍 Analyzing...\n")
        
        try:
            logger.info("🤖 Starting agent runner execution...")
            async for event in runner.run_async(
                user_id=USER_ID, 
                session_id=SESSION_ID, 
                new_message=content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(f"{part.text.strip()}")
            logger.info("✅ Agent execution completed successfully")
            print()  # Add newline after response
        except Exception as e:
            logger.error(f"❌ Error during analysis: {e}", exc_info=True)
            print(f"❌ ERROR during analysis: {e}\n")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 Code Review System Starting...")
    logger.info("=" * 60)
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\n👋 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        logger.info("=" * 60)
        logger.info("🛑 Code Review System Shutdown")
        logger.info("=" * 60)

