

# GitHub Integration Architecture

## System Architecture Diagram

```mermaid
graph LR
    subgraph External["🌐 External"]
        GH["<b>GitHub</b><br/>Pull Requests"]
        ENG["<b>Engineers</b><br/>Development"]
        style GH fill:#24292e,stroke:#ffffff,stroke-width:2px,color:#ffffff
        style ENG fill:#2ea44f,stroke:#1b7f37,stroke-width:2px,color:#ffffff
    end

    subgraph Entry["🚪 Entry - GCP"]
        LB["<b>Load Balancer</b><br/>HTTPS/SSL"]
        WH["<b>Webhook</b><br/>Cloud Run"]
        style WH fill:#ff6f00,stroke:#e65100,stroke-width:2px,color:#ffffff
        style LB fill:#ff8f00,stroke:#e65100,stroke-width:2px,color:#ffffff
    end

    subgraph Queue["📬 Queue"]
        PS["<b>Pub/Sub</b><br/>Async"]
        style PS fill:#7b1fa2,stroke:#4a148c,stroke-width:2px,color:#ffffff
    end

    subgraph Processing["⚙️ Processing"]
        WK["<b>Worker</b><br/>Cloud Run/GKE"]
        API["<b>ADK API</b><br/>Agent Runtime"]
        style WK fill:#43a047,stroke:#2e7d32,stroke-width:2px,color:#ffffff
        style API fill:#fbc02d,stroke:#f57f17,stroke-width:2px,color:#000000
    end

    subgraph Agents["🤖 Multi-Agent System"]
        ORC["<b>Orchestrator</b><br/>Flow Control"]
        CLS["<b>Classifier</b><br/>Type Detection"]
        CQ["<b>Quality</b><br/>Complexity"]
        SEC["<b>Security</b><br/>Vulnerabilities"]
        EP["<b>Engineering</b><br/>SOLID/Patterns"]
        CAR["<b>Carbon</b><br/>Efficiency"]
        GHA["<b>GitHub Agent</b><br/>API Client"]
        RPT["<b>Synthesizer</b><br/>Reports"]
        style ORC fill:#00897b,stroke:#004d40,stroke-width:2px,color:#ffffff
        style CLS fill:#26a69a,stroke:#00695c,stroke-width:2px,color:#ffffff
        style CQ fill:#c2185b,stroke:#880e4f,stroke-width:2px,color:#ffffff
        style SEC fill:#d81b60,stroke:#880e4f,stroke-width:2px,color:#ffffff
        style EP fill:#e91e63,stroke:#880e4f,stroke-width:2px,color:#ffffff
        style CAR fill:#ec407a,stroke:#ad1457,stroke-width:2px,color:#ffffff
        style GHA fill:#3f51b5,stroke:#1a237e,stroke-width:2px,color:#ffffff
        style RPT fill:#5c6bc0,stroke:#283593,stroke-width:2px,color:#ffffff
    end

    subgraph Backend["💾 Backend - GCP"]
        LLM["<b>LLM</b><br/>Gemini/Ollama"]
        DB["<b>Cloud SQL</b><br/>PostgreSQL"]
        ART["<b>GCS</b><br/>Artifacts"]
        CACHE["<b>Redis</b><br/>Cache"]
        style LLM fill:#ff7043,stroke:#bf360c,stroke-width:2px,color:#ffffff
        style DB fill:#1976d2,stroke:#0d47a1,stroke-width:2px,color:#ffffff
        style ART fill:#1e88e5,stroke:#1565c0,stroke-width:2px,color:#ffffff
        style CACHE fill:#2196f3,stroke:#1565c0,stroke-width:2px,color:#ffffff
    end

    subgraph Monitor["📊 Observability"]
        MON["<b>Monitoring</b><br/>Metrics"]
        LOG["<b>Logging</b><br/>Analysis"]
        style MON fill:#d32f2f,stroke:#b71c1c,stroke-width:2px,color:#ffffff
        style LOG fill:#e53935,stroke:#c62828,stroke-width:2px,color:#ffffff
    end

    %% Main Flow (Left to Right)
    ENG -->|1| GH
    GH -->|2| LB --> WH
    WH -->|3| PS
    PS -->|4| WK
    WK -->|5| API --> ORC
    ORC --> CLS
    ORC --> GHA
    GHA <-->|6| GH
    
    %% Agent Orchestration
    ORC --> CQ & SEC & EP & CAR
    CQ & SEC & EP & CAR --> RPT
    RPT --> ORC
    
    %% AI Integration
    CLS -.-> LLM
    CQ & SEC & EP & CAR -.-> LLM
    RPT -.-> LLM
    
    %% Storage
    CQ & SEC & EP & CAR --> DB
    RPT --> DB & ART
    ORC -.-> CACHE
    
    %% Return Path
    ORC --> API --> WK --> GHA
    GHA -->|7| GH -->|8| ENG
    
    %% Monitoring
    WH & WK & API -.-> LOG & MON
```

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant SE as Engineer
    participant GH as GitHub Organization
    participant WH as Webhook Service
    participant PS as Cloud Pub/Sub
    participant WK as Worker Service
    participant API as Agent (ADK) API Server
    participant ORC as Orchestrator Agent 
    participant CLS as Classifier Agent
    participant CQ as Code Quality Agent
    participant SEC as Security Agent
    participant EP as Engineering Practices Agent
    participant CAR as Carbon Footprint Agent
    participant GHA as GitHub Agent
    participant RPT as Report Synthesizer Agent
    participant DB as Database Service

    Note over SE,GH: Engineering Activity 
    SE->>GH: Create/Update Pull Request
    activate GH

    Note over GH,WH: Github Webhook Event
    GH->>WH: POST /webhook/github<br/>(PR Event Payload)
    activate GH

    Note over WH,PS: Publish to Queue
    WH->>PS: Publish Message<br/>(PR Event Payload)
    activate PS

    Note over PS,WK: Async Processing Starts
    PS->>WK: Push Message<br/>(PR Review Request)
    activate WK

    Note over WK, API: Call Agent (ADK) API
    WK->>API: POST /run<br/>(app_name, user_id, session_id, PR Review Request details) 
    activate API

    Note over API,ORC: Start Orcestration
    API->>ORC: Initialize Context<br/>(IvocationContext)
    activate ORC

   Note over ORC,DB: Initialize Session
   ORC->>DB: Create/Load Session
   activate DB
   DB-->>ORC: Session Data
   deactivate DB

   Note over ORC,CLS: Step 1 Classification 
   ORC->>CLS: Classify Request Type
   activate CLS
   CLS->>CLS: Analyze Input<br/>(LLM: granite4/ gemini-2.5-flash)
   CLS-->>ORC: Classification Result<br/>(type: code_review_full)
   deactivate CLS

   Note over ORC,GHA: Step 2: Fetch PR Files
   ORC->>GHA: Fetch PR Files<br/>(repo, pr_number)
   activate GHA
   GHA->>GH: GitHub API:<br/>GET /repos/{owner}/pulls/{pr_number}/files
   activate GH
   GH-->>GHA: Changed Files + Patches
   deactivate GH
   GHA-->>ORC: File List With Content
   deactivate GHA

   Note over ORC: Step 3: Select Agents
   ORC->>ORC: Determine Requested Agents<br/>(based on classification)

   Note over ORC,CAR: Step 4: Parallel Agent Execution
   par Code Quality Analysis
        ORC->>CQ: Analyze Code Quality
        activate CQ
        CQ->>CQ: Calculate Complexity<br/>Check Maintainability
        CQ->>DB: Save Analysis Results
        activate DB
        DB-->>CQ: Saved
        deactivate DB
        CQ-->>ORC: Quality Report
        deactivate CQ
   and  Security Analysis
        ORC->>SEC: Analyze Security
        activate SEC
        SEC->>SEC: Check Security Issues<br/>Find Secrets, Vulnerabilities
        SEC->>DB: Save Analysis Results
        activate DB
        DB-->>SEC: Saved
        deactivate DB
        SEC-->>ORC: Security Report
        deactivate SEC
    and Engineering Practices Analysis
        ORC->>EP: Analyze Engineering Practices
        activate EP
        EP->>EP: Check SOLID Principles<br/>Design Patterns
        EP->>DB: Save Analysis Results
        activate DB
        DB-->>EP: Saved
        deactivate DB
        EP-->>ORC: Engineering Practices Report
        deactivate EP
    and Carbon Footprint Analysis
        ORC->>CAR: Analyze Carbon Footprint
        activate CAR
        CAR->>CAR: Analyze Efficiency<br/>Estimate Emissions
        CAR->>DB: Save Analysis Results
        activate DB
        DB-->>CAR: Saved
        deactivate DB
        CAR-->>ORC: Carbon Footprint Report
        deactivate CAR
    end

    Note over ORC,RPT: Step 5: Synthesize Report
    ORC->>RPT: Generate Report
    activate RPT
    RPT->>DB: Read All Analysis Results
    activate DB
    DB-->>RPT: Consolidate Reporting Data
    deactivate DB
    RPT-->>RPT: Generate Markdown Report<br/>(LLM: granite4/ gemini-2.5-flash)
    RPT->>DB: Save Final Report
    activate DB
    DB-->>RPT: Saved
    deactivate DB
    RPT-->>ORC: Final Report (Markdown)
    deactivate RPT
    
    Note over ORC,API:Return Results
    ORC-->>API: Execution Complete<br/>(final_report in session state)
    deactivate ORC
    API-->>WK: Response<br/>(200 OK + Report)
    deactivate API

    Note over WK,GH: Step 6: Post Results to GitHub
    WK->>GHA: Create PR Review
    activate GHA
    GHA->>GH: GitHub API:<br/>POST /repos/{owner}/{repo}/pulls/{pr_number}/reviews
    activate GH 
    GH-->>GHA: Review Created
    deactivate GH
    GHA-->>WK: Success
    deactivate GHA
    
    Note over WK,PS: Complete Processing
    WK->>PS: ACK Message<br/>(Remove from Queue)
    deactivate PS
    WK-->>SE: (Notification via GitHub)
    deactivate WK

    Note over SE,GH: Engineer Sees Results
    SE->>GH: View PR Page
    activate GH
    GH-->>SE: Display Review Comments<br/>& Analysis Report
    deactivate GH

    Note over SE,DB: Optional: View Analytics
    SE->>DB: Query Historical Data<br/>(via Dashboard)
    activate DB
    DB-->>SE: Trends & Metrics
    deactivate DB
```


## End-to-End Workflow

### STEP 1: GITHUB WEBHOOK INTEGRATION

**1. Engineer → GitHub**
   - Creates or updates Pull Request
   - Triggers: opened, synchronize, reopened events

**2. GitHub → Webhook Service (Cloud Run)**
   - POST /webhook/github
   - Payload: PR event data (repo, pr_number, action, sender)

**3. Webhook Service (Cloud Run)**
   - Validates HMAC signature (security)
   - Filters event type (only PR events)
   - Extracts PR metadata
   - Transforms to internal format

**4. Webhook Service → Cloud Pub/Sub**
   - Publishes message to "pr-review-requests" topic
   - Message: {repo, owner, pr_number, pr_title, author, head_sha, action}
   - Returns 200 OK to GitHub (webhook acknowledged)

---

### STEP 2: ASYNC PROCESSING TRIGGER

**5. Cloud Pub/Sub → Worker Service (Cloud Run)**
   - Pushes message from subscription
   - Worker receives: PR review request
   - Retries on failure (exponential backoff)

**6. Worker Service → Agent (ADK) API Server (Cloud Run)**
   - POST /api/v1/run
   - Headers: {Authorization: Bearer <token>}
   - Body: 
     ```json
     {
       "app_name": "orchestrator_agent",
       "user_id": "repo_owner",
       "session_id": "pr_<repo>_<pr_number>",
       "user_message": "Review PR #<number>: <title>",
       "context": {
         "repo": "<owner>/<repo>",
         "pr_number": <number>,
         "head_sha": "<sha>",
         "author": "<username>"
       }
     }
     ```

---

### STEP 3: CODE REVIEW ORCHESTRATION STARTS

**7. Agent API → Orchestrator Agent**
   - Initializes InvocationContext
   - Creates parent agent instance
   - Sets up execution environment

**8. Orchestrator → Session Service**
   - Creates or loads session: "pr_<repo>_<pr_number>"
   - Session stores: {state, history, metadata}
   - Returns: Session data with analysis_history[]

**9. Orchestrator → Cache Service (Redis/Memorystore)**
   - Checks if PR already analyzed (cache key: SHA256 of file contents)
   - If cache HIT: Returns cached report (skip to Step 16)
   - If cache MISS: Proceeds with analysis

---

### STEP 4: CLASSIFICATION & CODE RETRIEVAL

**10. Orchestrator → Classifier Agent**
   - Analyzes request intent: "Review PR_#001: Add payment feature"
   - Classifier → LLM Service (Gemini 2.5 Flash / Ollama Granite4)
   - Returns: {"type": "code_review_full", "has_code": true, "focus_areas": ["security", "quality", "engineering_practices"]}
     

**11. Orchestrator → GitHub Agent**
   - Request: Fetch PR files {repo: "owner/repo", pr_number: 123}
   
**12. GitHub Agent → GitHub API**
   - GET /repos/{owner}/{repo}/pulls/{pr_number}/files
   - Headers: {Authorization: token <github_token>}
   - Returns: Array of changed files with patches

**13. GitHub Agent → Orchestrator**
   - Returns: List of files with content, diffs, status (added/modified/deleted)
   
**14. Orchestrator → Code Optimizer**
   - Strips comments/docstrings from large files (>2000 chars)
   - Reduces token usage by ~20-30%

**15. Orchestrator → Artifact Service (GCS)**
   - Saves code input to: artifacts/orchestrator_agent/{user_id}/inputs/
   - File: code_input_analysis_{timestamp}.{ext}
   - Metadata: code_input_analysis_{timestamp}.{ext}.meta.json

---

### STEP 5: SEQUENTIAL AGENT EXECUTION
> ⚠️ **Sequential (not parallel)** to prevent API rate limiting
> 2-second delays between agents to stay under 15 RPM (Gemini free tier)
> Agents selection informed by Classifier Agent

**16. Orchestrator → Code Quality Agent** (Agent 1/4)
   - Analyzes: Complexity, maintainability, code smells
   - Code Quality Agent → LLM Service
   - Code Quality Agent → Tools: 
     - analyze_code_complexity()
     - analyze_static_code()
     - parse_code_ast()
   - Code Quality Agent → Database (Cloud SQL)
     - Saves analysis to: analysis_results table
   - Code Quality Agent → Artifact Service (GCS)
     - Saves: artifacts/.../sub_agent_outputs/analysis_..._code_quality_agent.json
   - Returns: Quality report to Orchestrator
   - ⏱️ Delay: 2 seconds

**17. Orchestrator → Security Agent** (Agent 2/4)
   - Analyzes: Vulnerabilities, secrets, injection risks
   - Security Agent → LLM Service
   - Security Agent → Tools:
     - scan_security_vulnerabilities()
   - Security Agent → Database (Cloud SQL)
   - Security Agent → Artifact Service (GCS)
   - Returns: Security report to Orchestrator
   - ⏱️ Delay: 2 seconds

**18. Orchestrator → Engineering Practices Agent** (Agent 3/4)
   - Analyzes: SOLID principles, design patterns, best practices
   - Engineering Agent → LLM Service
   - Engineering Agent → Tools:
     - evaluate_engineering_practices()
   - Engineering Agent → Database (Cloud SQL)
   - Engineering Agent → Artifact Service (GCS)
   - Returns: Engineering report to Orchestrator
   - ⏱️ Delay: 2 seconds

**19. Orchestrator → Carbon Footprint Agent** (Agent 4/4)
   - Analyzes: Code efficiency, energy consumption, emissions
   - Carbon Agent → LLM Service
   - Carbon Agent → Tools:
     - analyze_carbon_footprint()
   - Carbon Agent → Database (Cloud SQL)
   - Carbon Agent → Artifact Service (GCS)
   - Returns: Carbon report to Orchestrator

---

### STEP 6: REPORT SYNTHESIS

**20. Orchestrator → Report Synthesizer Agent**
   - Instruction: "Consolidate all analysis results into comprehensive report"

**21. Report Synthesizer → Session Service**
   - Reads all agent outputs from session state:
     - code_quality_analysis
     - security_analysis
     - engineering_practices_analysis
     - carbon_emission_analysis

**22. Report Synthesizer → LLM Service**
   - Generates comprehensive markdown report
   - Formats: Executive summary, detailed findings, recommendations
   - Token limit: 2048 output tokens

**23. Report Synthesizer → Artifact Service (GCS)**
   - Saves: artifacts/.../reports/report_analysis_{timestamp}.md
   - Metadata: report_analysis_{timestamp}.md.meta.json

**24. Report Synthesizer → Database (Cloud SQL)**
   - Saves final report metadata
   - Updates session with report reference

**25. Report Synthesizer → Cache Service (Redis)**
   - Caches result (key: SHA256, TTL: 1 hour)
   
**26. Report Synthesizer → Orchestrator**
   - Returns: Final markdown report

**27. Orchestrator → Session Service**
   - Updates analysis_history:
     ```json
     {
       "analysis_id": "analysis_20251127_143022",
       "timestamp": "2025-11-27T14:30:22Z",
       "status": "completed",
       "agents_executed": ["classifier", "code_quality", "security", "engineering", "carbon"],
       "artifacts": {
         "input_code": "artifacts/.../inputs/code_input_...",
         "final_report": "artifacts/.../reports/report_...",
         "agent_outputs": ["artifacts/.../sub_agent_outputs/..."]
       }
     }
     ```

---

### STEP 7: RESULTS DELIVERY

**28. Orchestrator → Agent API**
   - Returns: Execution complete with report in session state

**29. Agent API → Worker Service**
   - Response: 200 OK
   - Body: 
     ```json
     {
       "status": "success",
       "report": "<markdown content>",
       "analysis_id": "analysis_20251127_143022",
       "metrics": {
         "duration_ms": 45000,
         "agents_executed": 6,
         "total_issues": 12
       }
     }
     ```

**30. Worker Service → GitHub Agent**
   - Calls: create_pr_review(repo, pr_number, report, event="COMMENT")

**31. GitHub Agent → GitHub API**
   - POST /repos/{owner}/{repo}/pulls/{pr_number}/reviews
   - Headers: {Authorization: token <github_token>}
   - Body:
     ```json
     {
       "body": "<markdown report>",
       "event": "COMMENT",
       "comments": []
     }
     ```
   - Returns: Review created (review_id)

**32. Worker Service → Cloud Pub/Sub**
   - ACK message (removes from queue)
   - Logs: Success, duration, analysis_id

**33. Worker Service → Monitoring (Cloud Logging)**
   - Logs: Completion metrics, agent execution times, error rates

---

### STEP 8: ENGINEER FEEDBACK LOOP

**34. GitHub → Engineer**
   - Notification: "New review comment on PR #123"
   - Email/Web/Mobile notification

**35. Engineer → GitHub**
   - Views PR page
   - Sees: Review comment with comprehensive analysis

**36. Engineer**
   - Reviews findings:
     - ✅ Accepts recommendations
     - 💬 Discusses specific points
     - 🔧 Commits fixes
     - 🔄 Triggers new review cycle

---

### KEY COMPONENTS SUMMARY

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Webhook Service** | Cloud Run | Receive GitHub webhooks |
| **Cloud Pub/Sub** | GCP Pub/Sub | Async message queue |
| **Worker Service** | Cloud Run/GKE | Orchestrate API calls |
| **Agent API** | Cloud Run/GKE | ADK runtime server |
| **Orchestrator Agent** | Google ADK | Multi-agent coordination |
| **6 Sub-Agents** | Google ADK | Specialized analysis |
| **LLM Service** | Gemini/Ollama | AI inference |
| **Database** | Cloud SQL (PostgreSQL) | Persistent storage |
| **Artifact Service** | Cloud Storage (GCS) | File artifacts |
| **Cache** | Memorystore (Redis) | Result caching |
| **Session Service** | JSONFile/Cloud SQL | State management |
| **Monitoring** | Cloud Logging/Monitoring | Observability |

---

### PERFORMANCE CHARACTERISTICS

- **Webhook Response**: <100ms (immediate ACK)
- **Queue Latency**: <1 second
- **Full Analysis**: 30-60 seconds
  - Classifier: ~2s
  - Code fetch: ~3s
  - 4 agents × (5s + 2s delay) = ~28s
  - Report synthesis: ~5s
  - GitHub post: ~2s
- **Rate Limit**: 15 RPM (Gemini free), 30 RPM (Ollama)
- **Cache Hit**: <1 second (instant return)
- **Concurrent PRs**: Limited by Cloud Run scaling (up to 100 instances)



















   





