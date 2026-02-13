#!/usr/bin/env python3
"""
Centralized logging configuration for Nocturne platform
Provides structured logging with rotation and multiple handlers
"""

import asyncio
import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Optional

# Log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter that properly escapes message content"""

    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'file': record.filename,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry['stack'] = self.formatStack(record.stack_info)
            
        return json.dumps(log_entry)


# Log formats
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
SIMPLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
JSON_FORMATTER = JsonFormatter()


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    use_json: bool = False
) -> logging.Logger:
    """
    Setup a logger with file and console handlers

    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file name (if None, only console logging)
        max_bytes: Max bytes per log file before rotation
        backup_count: Number of backup files to keep
        use_json: Use JSON format for structured logging

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers = []

    # Format
    formatter = JSON_FORMATTER if use_json else logging.Formatter(DETAILED_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (with rotation)
    if log_file:
        file_path = os.path.join(LOG_DIR, log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Main application logger
app_logger = setup_logger(
    name='nocturne',
    level=logging.INFO,
    log_file='app.log'
)

# API logger
api_logger = setup_logger(
    name='nocturne.api',
    level=logging.INFO,
    log_file='api.log'
)

# Scraper logger
scraper_logger = setup_logger(
    name='nocturne.scraper',
    level=logging.INFO,
    log_file='scraper.log'
)

# Database logger
db_logger = setup_logger(
    name='nocturne.database',
    level=logging.INFO,
    log_file='database.log'
)

# Email logger
email_logger = setup_logger(
    name='nocturne.email',
    level=logging.INFO,
    log_file='email.log'
)

# Performance logger (for metrics)
perf_logger = setup_logger(
    name='nocturne.performance',
    level=logging.INFO,
    log_file='performance.log',
    use_json=True
)


class PerformanceTimer:
    """Context manager for timing operations and logging performance metrics"""
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger or perf_logger
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"START: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(f"FAILED: {self.operation} - {exc_val} - Duration: {duration:.3f}s")
        else:
            self.logger.info(f"COMPLETE: {self.operation} - Duration: {duration:.3f}s")
        
        return False  # Don't suppress exceptions
    
    @property
    def duration(self) -> float:
        """Get duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


def log_function_call(logger: Optional[logging.Logger] = None):
    """Decorator to log function calls with arguments and return values"""
    def decorator(func):
        import functools
        log = logger or app_logger
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            log.debug(f"CALL: {func_name} - Args: {args}, Kwargs: {kwargs}")
            
            try:
                result = await func(*args, **kwargs)
                log.debug(f"RETURN: {func_name} - Success")
                return result
            except Exception as e:
                log.error(f"ERROR: {func_name} - {str(e)}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            log.debug(f"CALL: {func_name} - Args: {args}, Kwargs: {kwargs}")
            
            try:
                result = func(*args, **kwargs)
                log.debug(f"RETURN: {func_name} - Success")
                return result
            except Exception as e:
                log.error(f"ERROR: {func_name} - {str(e)}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Convenience imports for other modules
__all__ = [
    'app_logger',
    'api_logger',
    'scraper_logger',
    'db_logger',
    'email_logger',
    'perf_logger',
    'setup_logger',
    'PerformanceTimer',
    'log_function_call'
]


# Test if run directly
if __name__ == "__main__":
    print("Testing logging configuration...")
    
    # Test different log levels
    app_logger.debug("Debug message")
    app_logger.info("Info message")
    app_logger.warning("Warning message")
    app_logger.error("Error message")
    
    # Test performance timer
    with PerformanceTimer("Test Operation"):
        import time
        time.sleep(0.1)
    
    print(f"Logs written to: {LOG_DIR}")
    print("Test complete!")
