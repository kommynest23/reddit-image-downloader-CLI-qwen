"""Helper utilities for the VK Media Downloader."""

import asyncio
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: The original filename
        
    Returns:
        Sanitized filename safe for the filesystem
    """
    # Replace potentially problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length to prevent OS issues
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def format_bytes(size_bytes: int) -> str:
    """
    Format bytes size to human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.2f} {size_names[i]}"


async def semaphore_wrapper(semaphore: asyncio.Semaphore, coro):
    """
    Wrapper to run a coroutine with a semaphore to limit concurrency.
    
    Args:
        semaphore: Semaphore to acquire
        coro: Coroutine to run
        
    Returns:
        Result of the coroutine
    """
    async with semaphore:
        return await coro