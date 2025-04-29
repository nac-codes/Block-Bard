"""
Minimal configuration system for loading story structure schemas.
"""

import json
import os
import logging
from pathlib import Path

# Setup logger
logger = logging.getLogger("story_config")

def get_schema_dir():
    """Get the schema directory path"""
    # Check if we're running from a package or directly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    schemas_dir = os.path.join(parent_dir, "schemas")
    if os.path.isdir(schemas_dir):
        return schemas_dir
    
    # Fallback to a user directory if running as a standalone script
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, ".block_bard", "schemas")

def load_schema(schema_name_or_path):
    """
    Load a JSON schema by name or from a file path.
    
    Args:
        schema_name_or_path: Either a schema name (e.g., 'bible', 'novel') 
                             or a path to a JSON schema file
    
    Returns:
        A dictionary containing the JSON schema
    """
    # Get the schemas directory
    schema_dir = get_schema_dir()
    
    # Check if it's a built-in schema name (without .json extension)
    if isinstance(schema_name_or_path, str) and not schema_name_or_path.endswith('.json'):
        schema_path = os.path.join(schema_dir, f"{schema_name_or_path}.json")
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                logger.info(f"Loaded schema: {schema_name_or_path}")
                return schema
            except Exception as e:
                logger.error(f"Error loading schema {schema_name_or_path}: {e}")
    
    # Try to load as a custom file path
    if os.path.exists(schema_name_or_path):
        try:
            with open(schema_name_or_path, 'r') as f:
                schema = json.load(f)
            logger.info(f"Loaded schema from file: {schema_name_or_path}")
            return schema
        except Exception as e:
            logger.error(f"Error loading schema from {schema_name_or_path}: {e}")
    
    # Try to load the minimal schema as fallback
    minimal_path = os.path.join(schema_dir, "minimal.json")
    if os.path.exists(minimal_path):
        try:
            with open(minimal_path, 'r') as f:
                schema = json.load(f)
            logger.warning(f"Schema '{schema_name_or_path}' not found. Using minimal schema.")
            return schema
        except Exception as e:
            logger.error(f"Error loading minimal schema: {e}")
    
    # Last resort hardcoded fallback
    logger.error(f"All schema loading attempts failed. Using hardcoded minimal schema.")
    return {
        "type": "object",
        "required": ["Content", "storyPosition"],
        "properties": {
            "Content": {"type": "string"},
            "Author": {"type": "string"},
            "storyPosition": {
                "type": "object",
                "properties": {
                    "position": {"type": "integer"}
                }
            },
            "previousPosition": {
                "type": "object",
                "properties": {
                    "position": {"type": "integer"}
                }
            }
        }
    } 