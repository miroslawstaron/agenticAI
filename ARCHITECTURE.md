# AgenticAI Architecture

## System Overview

AgenticAI is a research framework for multi-agent AI conversations. The architecture follows a hierarchical design with a base agent class, specialized subclasses, and cross-cutting infrastructure for logging, ID management, and inter-agent communication.

## Agent Hierarchy

```
                          AgentAI (Base)
                       LLM conversations
                    Message history & export
                              │
                ┌─────────────┼─────────────┐
                │             │             │
           ┌────▼────┐   ┌───▼───┐   ┌────▼─────┐
           │AgentAIC │   │Agent  │   │AgentDiag │
           │(C Code) │   │AIPy   │   │ (Mermaid)│
           └────┬────┘   │Python │   └──────────┘
                │        │Code  │
                │        └──────┘
         ┌──────┴─────┐
         │            │
    ┌────▼──────┐┌───▼──────────┐
    │Compiler   ││StaticAnalyzer│
    │(Error fix)││(CPPcheck)    │
    └───────────┘└──────────────┘

        AgentH (Human-in-the-Loop)
     
    ┌─────────────────────────────┐
    │ Domain-Specific Agents      │
    ├─────────────────────────────┤
    │ • AgentReqs (3GPP Analysis) │
    │ • Agent3GPP (PDF Parsing)   │
    └─────────────────────────────┘
```

## Cross-Agent Infrastructure

```
┌─────────────────────────────────────────────┐
│          Agent Instance                     │
│  ┌─────────────────────────────────────┐   │
│  │ messages: List[Dict[role, content]] │   │
│  │ agent_id: "00", "01", etc (00-99)  │   │
│  │ server_address: LLM endpoint        │   │
│  │ model_name: "provider/model"        │   │
│  └─────────────────────────────────────┘   │
└──────────┬──────────────────────────────────┘
           │
      Uses ├─────────────────┬──────────────────┬──────────────┐
           │                 │                  │              │
      ┌────▼────┐    ┌───────▼──────┐  ┌─────▼────┐   ┌──────▼─────┐
      │Logger   │    │AgentIDManager│  │MessageQueue│  │API Server  │
      │(tracking)    │(sequential)  │  │(async)    │  │(LiteLLM)   │
      └─────────┘    │  IDs 00-99   │  │SQL-backed │  └────────────┘
                     └──────────────┘  │ broadcast │
                                       │ targeted  │
                                       │ anyone    │
                                       └──────────┘
```

## Message Format (All Agents)

Every agent maintains a consistent message structure:

```python
messages = [
    {
        "role": "system",      # "system" | "user" | "assistant"
        "content": "..."       # Prompt or response text
    },
    {
        "role": "user",        # Designer/developer input
        "content": "Write C code for..."
    },
    {
        "role": "assistant",   # Programmer/LLM output
        "content": "```c\n#include...\n```"
    }
]
```

**Role Mapping:**
- `system`: Initial role definition (setup only)
- `user`: Input prompts (designers, developers, test datasets)
- `assistant`: LLM responses (programmers, generators)

## Request-Response Pipeline

### Basic Agent (AgentAI)

```
User Input
    │
    ▼
┌─────────────────────┐
│ get_response()      │
│ 1. Log action       │
│ 2. Add user msg     │
│ 3. Call LiteLLM API │
│ 4. Handle retries   │
│ 5. Add assistant msg│
│ 6. Log response     │
└─────────────────────┘
    │
    ├─ Success ──→ Return response string
    │
    └─ Failure ──→ Return None (after 3 retries)
```

### Compilation Agent (AgentAIC)

```
Code Generation Request
    │
    ▼
┌──────────────────────────────┐
│ get_response()               │
├──────────────────────────────┤
│ 1. Call LLM for code         │
│ 2. Extract from markdown     │
│ 3. Write to ./temp/code.c    │
│ 4. Compile with gcc -w -lm   │
│                              │
│ ┌─ Compilation Success ──→ Return response
│ │
│ └─ Compilation Error:       │
│    - Parse stderr for "error"
│    - Retry with fix prompt  │
│    - Max 3 trials          │
└──────────────────────────────┘
    │
    ├─ Final Success ──→ Return response
    │
    └─ Final Failure ──→ Return None
```

### Error Handling & Retries

```
LiteLLM API Call
    │
    ├─ SUCCESS ──→ Extract response
    │              Add to messages
    │              Return response string
    │
    └─ EXCEPTION ──→ Classify error
                     ├─ Timeout/Connection (retryable)
                     │   └─ Retry (if attempts < 3)
                     │
                     └─ Other (non-retryable)
                         └─ Log & return None
```

## Configuration Flow

All agents reference `config.py` for constants:

```
config.py
├─ LLM Settings
│  ├─ LLM_TEMPERATURE_GENERATION = 0.5
│  ├─ LLM_TEMPERATURE_FIXING = 0.3
│  ├─ LLM_MAX_TOKENS = 16000
│  ├─ LLM_RETRY_ATTEMPTS = 3
│  └─ LLM_TIMEOUT_SECONDS = 300
│
├─ Compilation
│  ├─ COMPILER_FLAGS = ["-w", "-lm"]
│  ├─ COMPILER_MAX_TRIALS = 3
│  └─ COMPILER_SOURCE_FILE = "./temp/code_temp.c"
│
├─ Agents
│  ├─ AGENT_ID_MAX = 99
│  └─ AGENT_DEFAULT_SERVER = "localhost:11434"
│
└─ Files
   ├─ RESULTS_DIR = "./results/"
   ├─ TEMP_DIR = "./temp/"
   └─ LOG_FILE = "execution.log"
```

## Inter-Agent Communication (MessageQueue)

```
┌───────────────────────────┐
│   MessageQueue (Singleton)│
│   SQLite-backed           │
│   Thread-safe             │
│                           │
│  ┌─────────────────────┐  │
│  │ Targeted Messages   │  │
│  │ sender → recipient  │  │
│  └─────────────────────┘  │
│                           │
│  ┌─────────────────────┐  │
│  │ Broadcast Messages  │  │
│  │ sender → all agents │  │
│  └─────────────────────┘  │
│                           │
│  ┌─────────────────────┐  │
│  │ Anonymous Messages  │  │
│  │ sender → first agent│  │
│  │ that retrieves      │  │
│  └─────────────────────┘  │
└───────────────────────────┘
```

**Usage Pattern:**

```python
mq = MessageQueue()  # Singleton

# Agent A sends to Agent B
mq.send_message(sender="agent_a", recipient="agent_b", payload={...})

# Agent B retrieves
messages = mq.get_messages(agent_id="agent_b")

# Broadcast to all
mq.send_message(sender="agent_a", recipient="broadcast", payload={...})

# Close (cleanup)
mq.close()
```

## Data Export Pipeline

```
Agent.messages (conversation history)
    │
    ├─ save_to_csv() ──→ role$content format
    │
    ├─ save_to_excel() ──→ DataFrame export
    │
    └─ to_html() ──→ Side-by-side designer/programmer table
                     with markdown-to-HTML conversion
```

## Logging Architecture

```
All Agent Methods
    │
    ├─ __init__ ──→ logger.log_agent_init()
    │              (logs agent ID, role, class name)
    │
    ├─ get_response() ──→ logger.log_agent_action()
    │                     (prompt sent, response received)
    │
    ├─ Exception handling ──→ logger.log_exception()
    │                         (error type, context, traceback)
    │
    └─ Operations (compile, analyze, save)
                  └─ logger.log_agent_action()
                     (operational metrics)
```

**Output:**
- `execution.log` (if enabled): All agent activities with timestamps
- 2-digit agent IDs (00-99): Sequential tracking

## Example: Complete Conversation Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Script: main_agentc.py                                      │
└─────────────────────────────────────────────────────────────┘
    │
    ├─ Create AgentAIC
    │  └─ __init__() → AgentIDManager.get_next_id() → "00"
    │  └─ logger.log_agent_init()
    │
    ├─ Loop (MAX_ITERATIONS times)
    │  │
    │  ├─ Designer sends prompt
    │  │  └─ agentProgrammer.get_response(prompt)
    │  │     ├─ Call LiteLLM
    │  │     ├─ Parse code from markdown
    │  │     └─ Try to compile
    │  │        ├─ Success → Add to messages
    │  │        └─ Error → Retry with fix prompt
    │  │
    │  └─ Save & log results
    │     ├─ logger.log_agent_action()
    │     └─ Append to messages
    │
    ├─ Save results
    │  └─ save_to_excel("results/conversation_...xlsx")
    │
    └─ Close resources
       └─ mq.close() [if using MessageQueue]
```

## Design Patterns Used

1. **Singleton Pattern** (Logger, MessageQueue, AgentIDManager)
   - Ensures single instance across application
   - Thread-safe with locks

2. **Inheritance** (Base AgentAI → Specialized subclasses)
   - Code reuse, consistent interface
   - Easy to add new agent types

3. **Composition** (AgentAIC uses AgentCompiler)
   - Separation of concerns
   - Pluggable components

4. **Message-based Communication** (MessageQueue)
   - Loose coupling between agents
   - Asynchronous, decoupled workflows

5. **Strategy Pattern** (Different LLM backends via LiteLLM)
   - Unified API for multiple providers
   - Easy to swap models/servers

## Key Directories

```
agenticAI/
├─ agent.py                    # Base agent
├─ agentC.py, agentPy.py      # Specialized agents
├─ agentCompiler.py           # Compilation support
├─ agentH.py                  # Human-in-the-loop
├─ logger.py                  # Logging singleton
├─ agent_id_manager.py        # ID management
├─ messagequeue.py            # Inter-agent communication
├─ config.py                  # Centralized configuration
│
├─ examples/
│  ├─ fibonacci_with_compiler.py
│  └─ message_queue_simple.py
│
├─ results/                   # Exported conversations (.xlsx, .csv, .html)
├─ temp/                      # Temporary files (code_temp.c, a.out)
└─ test/                      # Unit tests with mocking
```

## State Transitions (AgentAIC)

```
[INITIAL]
    │
    ├─ __init__() called
    │
[REQUEST]
    │
    ├─ get_response() called
    ├─ Prompt appended to messages
    │
[GENERATE]
    │
    ├─ LiteLLM completion API
    ├─ Response received
    │
[COMPILE]
    │
    ├─ Extract code from markdown
    ├─ Write to ./temp/code_temp.c
    ├─ gcc compilation
    │
    ├─ Success ──┐
    │            ├─ [SUCCESS]
    │            └─ Response added to messages
    │
    └─ Error ───┬─ Retry < 3? ──→ [ERROR → FIX → COMPILE]
               │
               └─ Retry >= 3 ──→ [FAILED]
                                 Return None
```

## Error Recovery Mechanisms

```
LiteLLM API Call
    │
    ├─ Timeout
    │  └─ Retry with increased timeout
    │     (configurable via LLM_RETRY_TIMEOUT_MULTIPLIER)
    │
    ├─ Connection Error
    │  └─ Retry with exponential backoff
    │
    ├─ Compilation Error (AgentAIC)
    │  └─ Parse stderr
    │     └─ Generate fix prompt
    │        └─ Retry code generation
    │           (up to COMPILER_MAX_TRIALS)
    │
    └─ Unrecoverable Error
       └─ Log & return None
```

This architecture supports:
- **Scalability**: Easy to add new agent types
- **Testability**: Modular design with clear interfaces
- **Observability**: Comprehensive logging with agent IDs
- **Resilience**: Multiple retry mechanisms and error handling
- **Flexibility**: Configuration-driven, pluggable components
