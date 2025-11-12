"""Web search tool using Anthropic's built-in web search capability."""

import json
from typing import Optional, Dict, Any, List
from tools.base import Tool


class AnthropicWebSearchTool(Tool):
    """Web search tool that uses Anthropic's built-in web search."""
    
    def __init__(self):
        """Initialize the Anthropic web search tool."""
        super().__init__(
            name="web_search",
            description="""
            Search the web using Anthropic's built-in web search capability.
            
            This tool allows Claude to search the web and use the results to inform responses.
            It provides up-to-date information for current events and recent data.
            
            Usage:
            - web_search(query="your search query")
            - web_search(query="latest AI news", allowed_domains=["arxiv.org", "openai.com"])
            - web_search(query="python tutorials", blocked_domains=["w3schools.com"])
            
            The tool returns search results that can be used to answer questions with current information.
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to use",
                        "minLength": 2
                    },
                    "allowed_domains": {
                        "type": "array",
                        "description": "Only include search results from these domains",
                        "items": {"type": "string"}
                    },
                    "blocked_domains": {
                        "type": "array", 
                        "description": "Never include search results from these domains",
                        "items": {"type": "string"}
                    }
                },
                "required": ["query"]
            }
        )
    
    async def execute(
        self,
        query: str,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Execute web search using Anthropic's capability.
        
        Note: This is a placeholder that returns a message indicating that
        web search should be handled by the Anthropic API directly.
        """
        # Build the search configuration
        search_config = {
            "query": query
        }
        
        if allowed_domains:
            search_config["allowed_domains"] = allowed_domains
        if blocked_domains:
            search_config["blocked_domains"] = blocked_domains
            
        # Format the response to indicate this should trigger Anthropic's web search
        return f"""[Web Search Request]
Query: {query}
Configuration: {json.dumps(search_config, indent=2)}

Note: This search should be performed using Anthropic's built-in web search capability.
The actual search will be handled by the Anthropic API when this tool is used in a conversation."""


class AnthropicWebTool(Tool):
    """Combined web tool with search and fetch capabilities using Anthropic's features."""
    
    def __init__(self):
        """Initialize the Anthropic web tool."""
        super().__init__(
            name="web",
            description="""
            Web operations using Anthropic's built-in capabilities.
            
            Operations:
            1. search: Search the web using Anthropic's web search
               - web(operation="search", query="your search query")
               - Returns current search results
               
            2. fetch: Get content from a URL (simulated)
               - web(operation="fetch", url="https://example.com")
               - Returns a message about fetching content
            
            This tool integrates with Anthropic's web search for current information.
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["search", "fetch"],
                        "description": "Operation to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (required for search operation)"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to fetch (required for fetch operation)"
                    },
                    "allowed_domains": {
                        "type": "array",
                        "description": "Only include search results from these domains",
                        "items": {"type": "string"}
                    },
                    "blocked_domains": {
                        "type": "array",
                        "description": "Never include search results from these domains", 
                        "items": {"type": "string"}
                    }
                },
                "required": ["operation"]
            }
        )
    
    async def execute(
        self,
        operation: str,
        query: Optional[str] = None,
        url: Optional[str] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Execute web operation."""
        
        if operation == "search":
            if not query:
                return "Error: Query is required for search operation."
                
            # Format search request for Anthropic's web search
            search_config = {"query": query}
            if allowed_domains:
                search_config["allowed_domains"] = allowed_domains
            if blocked_domains:
                search_config["blocked_domains"] = blocked_domains
                
            return f"""[Anthropic Web Search]
Query: {query}
Configuration: {json.dumps(search_config, indent=2)}

This search will be performed using Anthropic's built-in web search capability."""
            
        elif operation == "fetch":
            if not url:
                return "Error: URL is required for fetch operation."
                
            return f"""[URL Fetch Request]
URL: {url}

Note: URL fetching should be handled by appropriate tools or the Anthropic API."""
            
        else:
            return f"Error: Unknown operation '{operation}'. Use 'search' or 'fetch'."