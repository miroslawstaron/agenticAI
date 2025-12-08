"""Singleton Logger for AgenticAI.

This module provides a thread-safe Singleton logger for the AgenticAI project.
It supports fast logging with timestamps and different log levels.
All logs are written to the execution.log file.
"""

import logging
import threading
from datetime import datetime
from typing import Optional
import os


class SingletonLogger:
    """Thread-safe Singleton Logger class.
    
    This class implements the Singleton pattern to ensure only one logger
    instance exists throughout the application. It provides fast logging
    with timestamps and supports different log levels.
    """
    
    _instance: Optional['SingletonLogger'] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        """Create or return the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super(SingletonLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, log_file: str = "execution.log", enabled: bool = False):
        """Initialize the logger (only once).
        
        Args:
            log_file: Path to the log file (default: "execution.log")
            enabled: Whether logging is enabled (default: False)
        """
        # Only initialize once
        if SingletonLogger._initialized:
            return
            
        with SingletonLogger._lock:
            if SingletonLogger._initialized:
                return
                
            self.enabled = enabled
            self.log_file = log_file
            self._logger = logging.getLogger('AgenticAI')
            self._logger.setLevel(logging.DEBUG)
            
            # Properly close and remove any existing handlers
            for handler in self._logger.handlers[:]:
                handler.close()
                self._logger.removeHandler(handler)
            self._logger.handlers.clear()
            
            if self.enabled:
                # Create file handler with UTF-8 encoding
                file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                
                # Create formatter with timestamp
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(formatter)
                
                # Add handler to logger
                self._logger.addHandler(file_handler)
            
            SingletonLogger._initialized = True
    
    def enable(self, log_file: str = "execution.log"):
        """Enable logging.
        
        Args:
            log_file: Path to the log file (default: "execution.log")
        """
        with SingletonLogger._lock:
            if not self.enabled:
                self.enabled = True
                self.log_file = log_file
                
                # Properly close and remove any existing handlers
                for handler in self._logger.handlers[:]:
                    handler.close()
                    self._logger.removeHandler(handler)
                self._logger.handlers.clear()
                
                # Create file handler with UTF-8 encoding
                file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                
                # Create formatter with timestamp
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(formatter)
                
                # Add handler to logger
                self._logger.addHandler(file_handler)
    
    def disable(self):
        """Disable logging."""
        with SingletonLogger._lock:
            self.enabled = False
            # Properly close and remove handlers
            for handler in self._logger.handlers[:]:
                handler.close()
                self._logger.removeHandler(handler)
            self._logger.handlers.clear()
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with the specified level.
        
        Args:
            message: The message to log
            level: Log level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
        """
        if not self.enabled:
            return
            
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        log_level = level_map.get(level.upper(), logging.INFO)
        self._logger.log(log_level, message)
    
    def info(self, message: str):
        """Log an info message.
        
        Args:
            message: The message to log
        """
        self.log(message, "INFO")
    
    def debug(self, message: str):
        """Log a debug message.
        
        Args:
            message: The message to log
        """
        self.log(message, "DEBUG")
    
    def warning(self, message: str):
        """Log a warning message.
        
        Args:
            message: The message to log
        """
        self.log(message, "WARNING")
    
    def error(self, message: str):
        """Log an error message.
        
        Args:
            message: The message to log
        """
        self.log(message, "ERROR")
    
    def critical(self, message: str):
        """Log a critical message.
        
        Args:
            message: The message to log
        """
        self.log(message, "CRITICAL")
    
    def log_agent_init(self, agent_id: str, agent_class: str, system_prompt: str):
        """Log agent initialization with system prompt.
        
        Args:
            agent_id: Unique agent identifier
            agent_class: Name of the agent class
            system_prompt: The system prompt for the agent
        """
        self.info(f"[Agent:{agent_id}] Initialized {agent_class}")
        self.info(f"[Agent:{agent_id}] System Prompt: {system_prompt}")
    
    def log_agent_action(self, agent_id: str, action: str, details: str = ""):
        """Log an agent action.
        
        Args:
            agent_id: Unique agent identifier
            action: Description of the action
            details: Additional details (optional)
        """
        message = f"[Agent:{agent_id}] {action}"
        if details:
            message += f" - {details}"
        self.info(message)
    
    def log_exception(self, agent_id: str, exception: Exception, context: str = ""):
        """Log an exception.
        
        Args:
            agent_id: Unique agent identifier
            exception: The exception that occurred
            context: Additional context about where the exception occurred
        """
        message = f"[Agent:{agent_id}] Exception: {type(exception).__name__}: {str(exception)}"
        if context:
            message = f"[Agent:{agent_id}] Exception in {context}: {type(exception).__name__}: {str(exception)}"
        self.error(message)


def get_logger() -> SingletonLogger:
    """Get the singleton logger instance.
    
    Returns:
        The singleton logger instance
    """
    return SingletonLogger()
