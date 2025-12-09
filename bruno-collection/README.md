# Bruno API Collection - Agentic Code Review

This Bruno collection contains the API requests to test the complete code review pipeline.

## Setup

1. **Install Bruno**: Download from [usebruno.com](https://www.usebruno.com/)

2. **Open Collection**: 
   - Launch Bruno
   - Click "Open Collection"
   - Navigate to this folder: `/Users/rahulgupta/Documents/Coding/agentic-codereview/bruno-collection`

3. **Select Environment**:
   - In Bruno, select the "Local" environment from the dropdown (top right)

4. **Start the Server**:
   ```bash
   cd /Users/rahulgupta/Documents/Coding/agentic-codereview
   ./scripts/start_adk_api_server.sh
   ```

5. **Enable Mock GitHub Data** (for testing without real GitHub):
   ```bash
   export MOCK_GITHUB=true
   ```
   Or add `MOCK_GITHUB=true` to your `.env` file

## Usage

### Option 1: Run Requests Sequentially

Run these in order:

1. **1. Create Session** - Creates a new session with GitHub context
   - Sets `sessionId` environment variable automatically
   - Returns session ID

2. **2. Run Pipeline** - Triggers the complete code review pipeline
   - Uses `sessionId` from step 1
   - ⏱️ Takes 3-5 minutes to complete
   - Runs all 5 analysis agents + report generation

3. **3. Get Session State** - Retrieves results
   - Shows all analysis outputs
   - Displays final report preview
   - Validates all expected keys are present

### Option 2: Run Single Request

You can also run just **"3. Get Session State"** with a previous session ID:

1. In Bruno, go to Environments → Local
2. Set `sessionId` to an existing session ID (e.g., `516a9972-1c0a-41e2-aade-e47f13b92201`)
3. Run "3. Get Session State"

## Pipeline Steps

The pipeline executes these agents in sequence:

1. **GitHub Fetcher** - Fetches PR data from GitHub (or mock)
2. **Analysis Pipeline** (nested, 5 agents):
   - GitHub Data Adapter - Transforms data format
   - Security Agent - Scans vulnerabilities  
   - Code Quality Agent - Analyzes complexity
   - Engineering Practices Agent - Evaluates best practices
   - Carbon Emission Agent - Assesses environmental impact
3. **Artifact Saver** - Saves all 4 analysis JSON files to disk
4. **Report Synthesizer** - Generates comprehensive markdown report
5. **Report Saver** - Saves final report to disk

## Artifacts Location

After running the pipeline, check these locations:

- **Analysis JSON files**: `storage_bucket/artifacts/<session_id>/*.json`
- **Final Report**: `storage_bucket/artifacts/reports/<session_id>_report.md`

## Tests

Each request includes automated tests that validate:
- HTTP status codes
- Response structure
- Required fields presence
- Data completeness

View test results in Bruno's "Tests" tab after running each request.

## Troubleshooting

**"No sessionId set" error:**
- Run "1. Create Session" first
- Or manually set `sessionId` in the Local environment

**Timeout errors:**
- The pipeline can take 3-5 minutes
- Bruno's default timeout may be too short
- Check server logs: `tail -f logs/adk_api_server.log`

**Server not responding:**
- Verify server is running: `curl http://localhost:8000/docs`
- Check PID: `cat logs/adk_api_server.pid`
- Restart: `./scripts/stop_adk_api_server.sh && ./scripts/start_adk_api_server.sh`
