# Logging Feature for AgenticAI

## Overview

This logging system provides a thread-safe Singleton logger that tracks all agent activities, exceptions, and system events. The logger is designed to be fast, efficient, and easy to use across the entire AgenticAI codebase.

## Features

- **Singleton Pattern**: Only one logger instance exists throughout the application
- **Thread-Safe**: Can be safely used in multi-threaded environments
- **Fast Logging**: Optimized for minimal performance impact using Python's built-in logging module
- **Timestamped Entries**: All log entries include timestamps (YYYY-MM-DD HH:MM:SS format)
- **Multiple Log Levels**: Supports DEBUG, INFO, WARNING, ERROR, and CRITICAL levels
- **Agent Tracking**: Each agent gets a unique UUID for tracking throughout its lifecycle
- **System Prompt Logging**: Captures agent initialization with system prompts
- **Exception Handling**: Automatically logs all exceptions with context

## Usage

### Enabling Logging

To enable logging, use the `--log` command-line argument when running any main script:

```bash
# Basic usage with logging
python main.py --prompt "Your task here" --log

# AgentC with logging
python main_agentc.py --prompt "Write a C program" --log

# Human-in-the-loop with logging
python main_human.py --prompt "Review this code" --log
```

### Log File Location

All logs are written to `execution.log` in the current directory.

### Programmatic Usage

```python
from logger import get_logger

# Get the singleton logger instance
logger = get_logger()

# Enable logging (if not already enabled via command-line)
logger.enable("execution.log")

# Log at different levels
logger.info("Information message")
logger.debug("Debug message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# Log agent initialization (done automatically in AgentAI.__init__)
logger.log_agent_init(agent_id, agent_class_name, system_prompt)

# Log agent actions (done automatically in agent methods)
logger.log_agent_action(agent_id, "Action description", "Optional details")

# Log exceptions (done automatically in exception handlers)
logger.log_exception(agent_id, exception, "Context where exception occurred")

# Disable logging
logger.disable()
```

## Implementation Details

### Singleton Logger Class

The `SingletonLogger` class in `logger.py` implements the Singleton pattern with double-checked locking for thread safety. Key methods:

- `enable(log_file)`: Enable logging to specified file
- `disable()`: Disable logging and close handlers
- `log(message, level)`: Generic logging method
- `info/debug/warning/error/critical(message)`: Convenience methods for each level
- `log_agent_init(agent_id, agent_class, system_prompt)`: Log agent initialization
- `log_agent_action(agent_id, action, details)`: Log agent actions
- `log_exception(agent_id, exception, context)`: Log exceptions

### Agent Integration

Each agent class automatically:
1. Generates a unique UUID on initialization
2. Logs its system prompt when created
3. Logs all actions (e.g., sending prompts, receiving responses)
4. Logs all exceptions with context
5. Logs file operations (save_to_csv, save_to_excel)

### Agent Classes with Logging

- `AgentAI`: Base agent class with logging
- `AgentAIC`: C code agent with compilation logging
- `AgentCompiler`: Compiler agent with error fixing logs
- `AgentStaticAnalyzer`: Static analyzer with analysis logs
- `AgentHuman`: Human-in-the-loop agent with interaction logs
- `AgentDiagram`: Diagram generation agent (uses base class logging)

## Log Entry Format

Each log entry follows this format:

```
YYYY-MM-DD HH:MM:SS - LEVEL - MESSAGE
```

Examples:

```
2025-12-08 08:00:14 - INFO - [Agent:a1b2c3d4-e5f6-7890-abcd-ef1234567890] Initialized AgentAI
2025-12-08 08:00:14 - INFO - [Agent:a1b2c3d4-e5f6-7890-abcd-ef1234567890] System Prompt: You are a helpful assistant
2025-12-08 08:00:15 - INFO - [Agent:a1b2c3d4-e5f6-7890-abcd-ef1234567890] Sending prompt to LLM - Model: gpt-4
2025-12-08 08:00:16 - INFO - [Agent:a1b2c3d4-e5f6-7890-abcd-ef1234567890] Received response from LLM
2025-12-08 08:00:17 - ERROR - [Agent:a1b2c3d4-e5f6-7890-abcd-ef1234567890] Exception in get_response: TimeoutError: Request timeout
```

## Testing

Comprehensive tests are available in `test/test_logger.py`. Run them with:

```bash
python -m unittest test.test_logger -v
```

Tests cover:
- Singleton pattern enforcement
- Thread safety
- Concurrent logging
- All log levels
- Agent lifecycle logging
- Exception logging
- File persistence
- Timestamp formatting

## Performance Considerations

The logger is designed for minimal performance impact:
- Uses Python's built-in `logging` module (optimized in C)
- File I/O is buffered for efficiency
- Thread-safe operations use minimal locking
- Disabled by default (no overhead unless explicitly enabled)

## Best Practices

1. **Always use `--log` flag in production**: Helps with debugging and monitoring
2. **Review logs regularly**: Check for errors, warnings, and unexpected behavior
3. **Use appropriate log levels**: INFO for normal operations, ERROR for exceptions
4. **Don't log sensitive data**: Be careful with API keys, passwords, etc.
5. **Rotate logs periodically**: Large log files can slow down operations

## Future Enhancements

Potential improvements for future versions:
- Log rotation support
- Remote logging (e.g., to syslog or cloud services)
- Structured logging (JSON format)
- Log filtering by agent ID or level
- Performance metrics logging
- Configurable log format
