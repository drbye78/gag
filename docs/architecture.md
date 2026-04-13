# SAP BTP Engineering Intelligence System - Architecture Design

## 1. High-Level Architecture Diagram

```mermaid
flowchart TB
    subgraph "Client Layer"
        UI[Web UI / Client]
        MCP[MCP Clients]
        VLM[Vision Input]
    end

    subgraph "API Layer"
        HTTP[FastAPI / HTTP]
        WS[WebSocket]
        MCP_API[MCP Server]
    end

    subgraph "Agent System"
        PM[Planning Agent]
        RA[Retrieval Agent]
        REA[Reasoning Agent]
        TOOL[Tool Executor]
    end

    subgraph "Retrieval Layer"
        RO[Retrieval Orchestrator]
        DOCS[Docs Retriever]
        CODE[Code Retriever]
        GRAPH[Graph Retriever]
        TICKET[Ticket Retriever]
        TELE[Telemetry Retriever]
    end

    subgraph "Multimodal Pipeline"
        VLM_PROC[VLM Processor]
        IR[IR Builder]
    end

    subgraph "Graph Layer"
        FALK[FalkorDB Interface]
        QUERY[Query Abstraction]
    end

    subgraph "Vector Layer"
        QDR[Qdrant / Vector DB]
        EMB[Embedding Service]
    end

    subgraph "LLM Layer"
        ROUTER[LLM Router]
        QWEN[Qwen]
        GLM[GLM]
    end

    subgraph "MCP Interface"
        MCP_TOOLS[MCP Tools]
        CONTRACTS[Contract Handlers]
    end

    subgraph "Data Layer"
        DOC_DB[Documents]
        CODE_STORE[Code Chunks]
        TICKET_STORE[Tickets]
        TELE_STORE[Telemetry]
    end

    UI --> HTTP
    MCP --> MCP_API
    VLM --> VLM_PROC
    
    HTTP --> PM
    MCP_API --> PM
    
    PM --> RA
    PM --> TOOL
    RA --> RO
    RO --> DOCS
    RO --> CODE
    RO --> GRAPH
    RO --> TICKET
    RO --> TELE
    
    DOCS --> QDR
    CODE --> QDR
    CODE --> FALK
    TICKET --> QDR
    TELE --> TELE_STORE
    
    VLM_PROC --> IR
    IR --> EMB
    EMB --> QDR
    
    REA --> ROUTER
    TOOL --> ROUTER
    
    MCP_API --> MCP_TOOLS
    MCP_TOOLS --> CONTRACTS
```

## 2. Core Components

### 2.1 API Layer

| Component | Responsibility | Interface |
|-----------|--------------|-----------|
| FastAPI Server | HTTP endpoints, request/response handling | POST /query, GET /health, MCP endpoints |
| WebSocket | Real-time streaming | /ws stream |
| MCP Server | MCP protocol compliance | JSON-RPC 2.0 |

### 2.2 Agent System

| Agent | Input | Output | Description |
|-------|-------|--------|-------------|
| Planning Agent | User query + IR | Execution plan with steps + tools | Decomposes query into retrieval/execution plan |
| Retrieval Agent | Plan | Retrieved data from multiple sources | Executes retrieval plan against all sources |
| Reasoning Agent | IR + retrieved data + tools | Final answer | Synthesizes answer from retrieved context |
| Tool Executor | Tool calls | Tool results | Executes specific tools |

### 2.3 Retrieval Layer

| Retriever | Data Source | Search Type |
|----------|------------|------------|
| Docs Retriever | Qdrant | Semantic (embeddings) |
| Code Retriever | Qdrant + FalkorDB | Semantic + graph relationships |
| Graph Retriever | FalkorDB | Cypher queries |
| Ticket Retriever | Ticket DB | Keyword + semantic |
| Telemetry Retriever | Logs/Metrics | Filtering + semantic |

### 2.3.1 Entity Graph Cache
- LRU cache (capacity: 500, TTL: 1 hour)
- Populated on cache miss from FalkorDB via graph retriever
- Integrated into EnhancedHybridRetriever and EntitySearchTool
- Exposed via REST: GET /entity/cache/stats, POST /entity/cache/invalidate

### 2.3.2 Lazy Retriever Initialization
HybridRetriever uses @property-based lazy initialization for all retrievers.
Only the retrievers needed for the classified strategy are instantiated, reducing startup time and memory.

### 2.4 Graph Layer

| Component | Technology | Purpose |
|-----------|------------|---------|
| FalkorDB Interface | FalkorDB | Graph operations |
| Query Abstraction | Cypher | Simplified query API |

### 2.5 Multimodal Pipeline

| Stage | Input | Output |
|-------|-------|-------|
| VLM Processor | Images/Diagrams | Extracted text/metadata |
| IR Builder | Multimodal outputs | Normalized IR (deduplicated, validated) |

### 2.6 MCP Interface

| Component | Function |
|-----------|----------|
| Tool Definitions | JSON schema for all tools |
| Request Router | Routes MCP requests to appropriate handlers |
| Contract Validators | Request/response schema validation |

## 3. Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant PA as Planner Agent
    participant RA as Retrieval Agent
    participant RO as Retrieval Orchestrator
    participant REA as Reasoning Agent
    participant LLM as LLM Router

    U->>API: User Query
    API->>PA: query + context
    PA->>PA: Analyze query + IR
    PA->>RA: Execution Plan
    
    rect rgb(240, 248, 255)
        note right of RA: Parallel retrieval
        RA->>RO: Retrieve docs
        RA->>RO: Retrieve code  
        RA->>RO: Retrieve graph
        RA->>RO: Retrieve tickets
        RA->>RO: Retrieve telemetry
        RO-->>RA: Combined results
    end
    
    RA->>REA: retrieved_data
    REA->>LLM: Generate answer
    LLM-->>REA: Generated response
    REA->>U: Final Answer
```

## 4. Agent Interaction Flow

```mermaid
stateDiagram-v2
    [*] --> Planning
    Planning --> Retrieval: Plan ready
    Retrieval --> ToolExecution: Need tools
    ToolExecution --> Retrieval: Tool result
    Retrieval --> Reasoning: Data retrieved
    Reasoning --> Finalize: Answer ready
    Finalize --> [*]
    
    Reasoning --> Planning: Re-plan needed
```

## 5. Knowledge Flow

```mermaid
flowchart LR
    subgraph "Ingestion"
        RAW[Raw Data]
        VLM[VLM]
        IRB[IR Builder]
        EMB[Embeddings]
    end

    subgraph "Storage"
        QDR[Qdrant]
        FALK[FalkorDB]
    end

    subgraph "Retrieval"
        QUERY[Query]
        RERANK[Rerank]
    end

    RAW --> VLM
    VLM --> IRB
    IRB --> EMB
    EMB --> QDR
    IRB --> FALK
    
    QUERY --> EMB
    EMB --> RERANK
    RERANK --> QUERY
```

## 6. Deployment Architecture

```mermaid
flowchart TB
    subgraph "Container Orchestration"
        K8S[K8s / Docker Compose]
    end

    subgraph "Services"
        API[API Service<br/>x2+ replicas]
        AGENT[Agent Service<br/>x2+ replicas]
        RETRIEVAL[Retrieval Service<br/>stateless]
    end

    subgraph "Data Layer"
        QDRANT[Qdrant Cluster]
        FALKORDB[FalkorDB Cluster]
        REDIS[Redis Cache]
    end

    subgraph "External"
        LLM[LLM Provider<br/>Qwen/GLM]
        VLM_LLM[VLM Provider]
    end

    K8S --> API
    K8S --> AGENT
    K8S --> RETRIEVAL
    
    API --> QDRANT
    API --> FALKORDB
    API --> REDIS
    
    AGENT --> LLM
    RETRIEVAL --> VLM_LLM
```

### 6.1 Docker Compose Topology

```yaml
# docker-compose.yml overview
services:
  api:
    image: engineering-intelligence-api
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - FALKORDB_HOST=falkordb
      - LLM_ROUTER_URL=llm-router
  
  agent:
    image: engineering-intelligence-agent
    environment:
      - LLM_ROUTER_URL=llm-router
  
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
  
  falkordb:
    image: falkordb/falkordb
    ports:
      - "6379:6379"
```

## 7. System Constraints Compliance

| Requirement | Implementation |
|-------------|----------------|
| Multi-RAG | 5 retrieval sources (docs, code, graph, tickets, telemetry) |
| Multimodal Input | VLM pipeline + image processing |
| MCP Integration | MCP server + tool definitions + JSON-RPC 2.0 |

## 8. Module Organization

```
engineering_intelligence/
├── api/                    # API layer (FastAPI)
│   ├── main.py            # Application entry
│   ├── routes.py          # HTTP routes
│   ├── mcp.py             # MCP server
│   └── schemas.py         # Request/response models
├── agents/                 # Agent system
│   ├── planner.py         # Planning agent
│   ├── retrieval.py       # Retrieval agent  
│   ├── reasoning.py       # Reasoning agent
│   ├── executor.py        # Tool executor
│   └── orchestration.py   # Orchestration engine
├── retrieval/             # Retrieval layer
│   ├── orchestrator.py    # Retrieval orchestrator
│   ├── docs.py           # Docs retriever
│   ├── code.py           # Code retriever
│   ├── graph.py          # Graph retriever
│   ├── ticket.py         # Ticket retriever
│   └── telemetry.py      # Telemetry retriever
├── graph/                 # Graph layer
│   ├── client.py         # FalkorDB client
│   └── queries.py       # Query abstractions
├── multimodal/           # Multimodal pipeline
│   ├── vlm.py           # VLM processor
│   └── ir_builder.py    # IR builder
├── llm/                  # LLM layer
│   └── router.py        # LLM router client
├── tools/                 # Tool system
│   ├── base.py          # Tool interface
│   ├── architecture.py # Architecture evaluator
│   ├── security.py     # Security validator
│   └── cost.py         # Cost estimator
├── models/               # Data models
│   ├── ir.py           # IR schema
│   ├── graph.py        # Graph schema
│   ├── retrieval.py    # Retrieval schemas
│   └── mcp.py         # MCP contracts
├── evaluation/         # Evaluation framework
│   └── test_cases.py   # Test cases + scoring
└── docker-compose.yml   # Deployment config
```

---

**Document Version**: 2.4  
**Status**: Architecture Design Complete  
**Next Phase**: Core Data Models (PHASE 3)