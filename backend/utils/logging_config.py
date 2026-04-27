"""
Centralized logging configuration for CryptoPredict Agents.
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler
from rich.console import Console

# Console for rich output
console = Console()

# Log formatters
DETAILED_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"
SIMPLE_FORMAT = "%(name)s | %(levelname)s | %(message)s"


def get_log_dir() -> Path:
    """Get or create log directory."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir


def setup_logging(
    level: Optional[str] = None,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> None:
    """
    Setup centralized logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console with rich formatting
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    handlers = []
    
    # Console handler with Rich
    if log_to_console:
        rich_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True
        )
        rich_handler.setLevel(numeric_level)
        rich_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT))
        handlers.append(rich_handler)
    
    # File handlers
    if log_to_file:
        log_dir = get_log_dir()
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Main log file - rotating
        main_log = log_dir / f"crypto_agents_{timestamp}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log,
            maxBytes=10_000_000,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        handlers.append(file_handler)
        
        # Error log file
        error_log = log_dir / f"errors_{timestamp}.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log,
            maxBytes=10_000_000,
            backupCount=5,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        handlers.append(error_handler)
        
        # Agent-specific log
        agent_log = log_dir / f"agent_activity_{timestamp}.log"
        agent_handler = logging.handlers.RotatingFileHandler(
            agent_log,
            maxBytes=10_000_000,
            backupCount=3,
            encoding="utf-8"
        )
        agent_handler.setLevel(logging.INFO)
        agent_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        # Filter for agent-related logs
        agent_handler.addFilter(lambda record: "agent" in record.name.lower())
        handlers.append(agent_handler)
    
    # Add all handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Suppress noisy third-party logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apify_client").setLevel(logging.INFO)
    
    logging.info(f"Logging initialized at level {log_level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


class AgentLogger:
    """Structured logger for agent activities."""
    
    def __init__(self, agent_name: str):
        self.logger = get_logger(f"agent.{agent_name}")
        self.agent_name = agent_name
    
    def log_decision(self, decision: str, context: dict):
        """Log an agent decision with context."""
        self.logger.info(
            f"[{self.agent_name}] Decision: {decision}",
            extra={"agent": self.agent_name, "context": context, "type": "decision"}
        )
    
    def log_action(self, action: str, result: dict):
        """Log an agent action with result."""
        self.logger.info(
            f"[{self.agent_name}] Action: {action} -> {result}",
            extra={"agent": self.agent_name, "result": result, "type": "action"}
        )
    
    def log_error(self, error: Exception, context: dict = None):
        """Log an agent error."""
        self.logger.error(
            f"[{self.agent_name}] Error: {error}",
            exc_info=True,
            extra={"agent": self.agent_name, "context": context or {}, "type": "error"}
        )
    
    def log_metric(self, metric_name: str, value: float, tags: dict = None):
        """Log a metric."""
        self.logger.info(
            f"[{self.agent_name}] Metric: {metric_name}={value}",
            extra={"agent": self.agent_name, "metric": metric_name, 
                   "value": value, "tags": tags or {}, "type": "metric"}
        )
