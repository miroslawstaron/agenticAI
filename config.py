"""
AgenticAI Configuration - Centralized constants and settings.

This module defines all configuration parameters used throughout the framework.
AI agents should reference these constants instead of hardcoding values.
"""

# ============================================================================
# LLM Configuration
# ============================================================================

# Temperature settings control model creativity vs determinism
LLM_TEMPERATURE_GENERATION = 0.5  # General code/diagram generation (balanced creativity)
LLM_TEMPERATURE_FIXING = 0.3      # Error fixing and compilation loops (more deterministic)

# Token and timeout limits
LLM_MAX_TOKENS = 16000
LLM_TIMEOUT_SECONDS = 300

# Retry and resilience
LLM_RETRY_ATTEMPTS = 3
LLM_RETRY_TIMEOUT_MULTIPLIER = 1.5  # Increase timeout on retry

# ============================================================================
# Compilation Configuration (GCC-based)
# ============================================================================

COMPILER_PATH = "gcc"
COMPILER_FLAGS = ["-w", "-lm"]  # -w: suppress warnings, -lm: link math library
COMPILER_OUTPUT_FILE = "./temp/a.out"
COMPILER_SOURCE_FILE = "./temp/code_temp.c"
COMPILER_MAX_TRIALS = 3  # Max attempts to fix compilation errors

# Error patterns for parsing
COMPILER_ERROR_KEYWORD = "error"

# ============================================================================
# Python Execution Configuration
# ============================================================================

PYTHON_EXECUTOR_PATH = "python3"
PYTHON_MAX_TRIALS = 3  # Max attempts to fix runtime errors
PYTHON_EXECUTION_TIMEOUT = 30  # seconds

# ============================================================================
# Static Analysis Configuration (Cppcheck)
# ============================================================================

STATIC_ANALYZER_TOOL = "cppcheck"
STATIC_ANALYZER_MAX_TRIALS = 3

# ============================================================================
# Diagram Generation Configuration (Mermaid)
# ============================================================================

DIAGRAM_TYPES = ["class", "flowchart", "sequence", "er"]
DIAGRAM_VALIDATOR_CLI = "mermaid"  # mermaid-cli for validation
DIAGRAM_VALIDATION_TIMEOUT = 10  # seconds

# ============================================================================
# Agent Configuration
# ============================================================================

# Sequential agent IDs
AGENT_ID_MAX = 99
AGENT_ID_RESET_BETWEEN_RUNS = True  # Reset for deterministic test runs

# Agent initialization defaults
AGENT_DEFAULT_SERVER = "http://localhost:11434"  # Ollama default
AGENT_DEFAULT_MODEL = "ollama/qwen3:4b"

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_FILE = "execution.log"
LOG_ENABLED_BY_DEFAULT = False
LOG_LEVEL = "INFO"

# ============================================================================
# File Organization
# ============================================================================

RESULTS_DIR = "./results/"
TEMP_DIR = "./temp/"
REQUIREMENTS_DIR = "./requirements/"
EXAMPLES_DIR = "./examples/"
TEST_DIR = "./test/"

# ============================================================================
# Iteration and Experiment Limits
# ============================================================================

# Different use cases have different limits
MAX_ITERATIONS_QUICK_TEST = 2
MAX_ITERATIONS_BASIC_EXPERIMENT = 20
MAX_ITERATIONS_RESEARCH_STUDY = 5000

# ============================================================================
# Message Queue Configuration (Inter-agent Communication)
# ============================================================================

MESSAGE_QUEUE_DB_PATH = ":memory:"  # SQLite in-memory, or file path
MESSAGE_QUEUE_THREAD_SAFE = True    # Use threading locks
MESSAGE_QUEUE_BROADCAST_RECIPIENT = "broadcast"
MESSAGE_QUEUE_ANYONE_RECIPIENT = "anyone"

# ============================================================================
# Data Export Configuration
# ============================================================================

EXPORT_FORMAT_EXCEL = "xlsx"
EXPORT_FORMAT_CSV = "csv"
EXPORT_FORMAT_HTML = "html"

# Default role names for exported conversations
EXPORT_ROLE_USER = "user"          # Designer perspective
EXPORT_ROLE_ASSISTANT = "assistant"  # Programmer perspective

# ============================================================================
# API Key Configuration
# ============================================================================

# Environment variable names
API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_API_BASE_ENV_VAR = "OPENAI_API_BASE"

# ============================================================================
# 3GPP and Requirements Analysis
# ============================================================================

REQUIREMENTS_ANALYSIS_ENABLED = True
PDF_PARSER = "PyPDF2"

# ============================================================================
# Server Endpoints (for different environments)
# ============================================================================

SERVERS = {
    "local_ollama": "http://localhost:11434",
    "chalmers": "http://deepestthought.cse.chalmers.se:11434",
    "openai": None,  # Uses OPENAI_API_BASE env var
}

# ============================================================================
# Model Aliases (for convenience)
# ============================================================================

MODELS = {
    "qwen_small": "ollama/qwen3:4b",
    "deepseek_large": "ollama/deepseek-r1:70b",
    "gpt4": "gpt-4",
    "gpt35": "gpt-3.5-turbo",
}
