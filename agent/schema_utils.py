"""
Utility functions for working with JSON schemas and Pydantic models.
"""

import logging
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger("schema_utils")

def create_pydantic_model_from_schema(schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Create a Pydantic model dynamically based on a JSON schema.
    
    Args:
        schema: A JSON schema dictionary
        
    Returns:
        A Pydantic model class
    """
    try:
        # Extract required fields and properties from the schema
        required = schema.get('required', [])
        properties = schema.get('properties', {})
        
        fields = {}
        for field_name, field_info in properties.items():
            # Determine the type from the schema
            field_type = field_info.get('type')
            
            # Map JSON schema types to Python types
            type_map = {
                'string': str,
                'integer': int,
                'number': float,
                'boolean': bool,
                'array': list,
                'object': dict
            }
            
            python_type = type_map.get(field_type, Any)
            is_required = field_name in required
            
            # Special handling for nested objects like storyPosition and previousPosition
            if field_type == 'object' and 'properties' in field_info:
                nested_required = field_info.get('required', [])
                nested_props = field_info.get('properties', {})
                nested_fields = {}
                
                for nested_name, nested_info in nested_props.items():
                    nested_type = type_map.get(nested_info.get('type'), Any)
                    nested_fields[nested_name] = (
                        Optional[nested_type] if nested_name not in nested_required else nested_type,
                        Field(description=nested_info.get('description', ''))
                    )
                
                # Create dynamic model for nested object
                nested_model = create_model(
                    f"{field_name.title()}Model",
                    **nested_fields
                )
                
                fields[field_name] = (
                    Optional[nested_model] if not is_required else nested_model,
                    Field(description=field_info.get('description', ''))
                )
            else:
                # Regular field
                fields[field_name] = (
                    Optional[python_type] if not is_required else python_type,
                    Field(description=field_info.get('description', ''))
                )
        
        # Create the model dynamically
        model = create_model(
            "DynamicStoryModel",
            **fields
        )
        
        logger.info(f"Created Pydantic model with fields: {list(fields.keys())}")
        return model
        
    except Exception as e:
        logger.error(f"Error creating Pydantic model: {e}")
        
        # Create a minimal fallback model
        class MinimalModel(BaseModel):
            Content: str
            storyPosition: Dict[str, Any]
            previousPosition: Optional[Dict[str, Any]] = None
            
        logger.warning("Using minimal fallback model")
        return MinimalModel 