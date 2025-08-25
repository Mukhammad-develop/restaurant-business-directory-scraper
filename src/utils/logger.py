"""Logging utilities for the restaurant directory scraper."""

import os
import sys
from pathlib import Path
from loguru import logger
from src.config import config

def setup_logger():
    """Set up the logger with configuration from config file."""
    
    # Remove default logger
    logger.remove()
    
    # Get logging configuration
    log_config = config.logging
    log_level = log_config.get('level', 'INFO')
    log_file = log_config.get('log_file', 'logs/scraper.log')
    max_size = log_config.get('max_log_size', '10MB')
    backup_count = log_config.get('backup_count', 5)
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )
    
    # File handler with rotation
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=max_size,
        retention=backup_count,
        compression="zip",
        enqueue=True  # Thread-safe logging
    )
    
    return logger

# Initialize logger
setup_logger()

def get_logger(name: str = None):
    """Get a logger instance with optional name."""
    if name:
        return logger.bind(name=name)
    return logger 