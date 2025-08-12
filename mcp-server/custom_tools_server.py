#!/usr/bin/env python3
"""
Custom MCP Server with utility tools for ServiceOpsAI
"""

from fastmcp import FastMCP
from datetime import datetime
import json
import random
import string
import hashlib
import base64

# Initialize the MCP server
mcp = FastMCP("ServiceOpsAI Custom Tools")

# Tool 1: Generate random IDs
@mcp.tool
def generate_id(prefix: str = "ID", length: int = 8) -> str:
    """
    Generate a random ID with a given prefix and length.
    
    Args:
        prefix: The prefix for the ID (default: "ID")
        length: The length of the random part (default: 8)
    
    Returns:
        A random ID string
    """
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}_{random_part}"

# Tool 2: Get current timestamp
@mcp.tool
def get_timestamp(format: str = "iso") -> str:
    """
    Get the current timestamp in various formats.
    
    Args:
        format: The format of the timestamp ("iso", "unix", "readable")
    
    Returns:
        Current timestamp in the specified format
    """
    now = datetime.now()
    
    if format == "iso":
        return now.isoformat()
    elif format == "unix":
        return str(int(now.timestamp()))
    elif format == "readable":
        return now.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return now.isoformat()

# Tool 3: Calculate hash
@mcp.tool
def calculate_hash(text: str, algorithm: str = "sha256") -> str:
    """
    Calculate the hash of a given text.
    
    Args:
        text: The text to hash
        algorithm: The hashing algorithm ("md5", "sha256", "sha512")
    
    Returns:
        The hash of the text
    """
    if algorithm == "md5":
        return hashlib.md5(text.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(text.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(text.encode()).hexdigest()
    else:
        return hashlib.sha256(text.encode()).hexdigest()

# Tool 4: Base64 encoding/decoding
@mcp.tool
def base64_encode(text: str) -> str:
    """
    Encode text to base64.
    
    Args:
        text: The text to encode
    
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(text.encode()).decode()

@mcp.tool
def base64_decode(encoded: str) -> str:
    """
    Decode base64 text.
    
    Args:
        encoded: The base64 encoded string
    
    Returns:
        Decoded text
    """
    try:
        return base64.b64decode(encoded).decode()
    except Exception as e:
        return f"Error decoding: {str(e)}"

# Tool 5: JSON formatter
@mcp.tool
def format_json(json_string: str, indent: int = 2) -> str:
    """
    Format a JSON string with proper indentation.
    
    Args:
        json_string: The JSON string to format
        indent: Number of spaces for indentation (default: 2)
    
    Returns:
        Formatted JSON string
    """
    try:
        parsed = json.loads(json_string)
        return json.dumps(parsed, indent=indent, sort_keys=True)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {str(e)}"

# Tool 6: String operations
@mcp.tool
def transform_string(text: str, operation: str = "upper") -> str:
    """
    Transform a string with various operations.
    
    Args:
        text: The text to transform
        operation: The operation to perform ("upper", "lower", "title", "reverse", "capitalize")
    
    Returns:
        Transformed string
    """
    if operation == "upper":
        return text.upper()
    elif operation == "lower":
        return text.lower()
    elif operation == "title":
        return text.title()
    elif operation == "reverse":
        return text[::-1]
    elif operation == "capitalize":
        return text.capitalize()
    else:
        return text

# Tool 7: Service health check simulator
@mcp.tool
def check_service_health(service_name: str) -> dict:
    """
    Simulate a health check for a service.
    
    Args:
        service_name: The name of the service to check
    
    Returns:
        A dictionary with health status information
    """
    # Simulate random health status
    status_options = ["healthy", "degraded", "unhealthy"]
    status = random.choice(status_options)
    
    return {
        "service": service_name,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "uptime": f"{random.randint(1, 999)} hours",
        "response_time": f"{random.randint(10, 500)}ms",
        "memory_usage": f"{random.randint(30, 90)}%",
        "cpu_usage": f"{random.randint(10, 80)}%"
    }

# Add a prompt for the server
@mcp.prompt
def service_ops_helper() -> str:
    """Get helpful prompts for ServiceOps tasks."""
    return """You are a ServiceOps AI assistant with access to custom utility tools.
    
    Available tools:
    - generate_id: Create unique identifiers
    - get_timestamp: Get current time in various formats
    - calculate_hash: Hash text using different algorithms
    - base64_encode/decode: Encode or decode base64 strings
    - format_json: Format JSON strings
    - transform_string: Transform text (upper, lower, reverse, etc.)
    - check_service_health: Check health status of services
    
    Use these tools to help with service operations and data processing tasks."""

if __name__ == "__main__":
    # Run the server
    mcp.run()