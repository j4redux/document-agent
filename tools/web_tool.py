"""Web tools for fetching and searching web content."""

import asyncio
import html
import json
import re
import urllib.parse
import urllib.request
from typing import Optional
from urllib.error import URLError, HTTPError

from tools.base import Tool


class WebTool(Tool):
    """Tool for web operations like fetching URLs and searching."""

    def __init__(self):
        super().__init__(
            name="web",
            description="""
            Perform web operations like fetching content and searching.
            
            Operations:
            1. fetch: Get content from a URL
               - web(operation="fetch", url="https://example.com")
               - Returns content converted to markdown for readability
               
            2. search: Search the web (using DuckDuckGo HTML version)
               - web(operation="search", query="python tutorials")
               - Returns top search results
            
            Handles errors gracefully with timeouts and clear error messages.
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["fetch", "search"],
                        "description": "Operation to perform: 'fetch' or 'search'",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to fetch (required for fetch operation)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (required for search operation)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 10)",
                    },
                },
                "required": ["operation"],
            },
        )

    async def execute(
        self,
        operation: str,
        url: Optional[str] = None,
        query: Optional[str] = None,
        timeout: int = 10,
    ) -> str:
        """Execute web operations."""
        if operation == "fetch":
            if not url:
                return "Error: URL is required for fetch operation"
            return await self._fetch_url(url, timeout)
        elif operation == "search":
            if not query:
                return "Error: Query is required for search operation"
            return await self._search_web(query, timeout)
        else:
            return f"Error: Unknown operation '{operation}'"

    async def _fetch_url(self, url: str, timeout: int) -> str:
        """Fetch content from a URL and convert to markdown."""
        try:
            # Validate URL
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
            elif parsed.scheme not in ["http", "https"]:
                return f"Error: Only HTTP/HTTPS URLs are supported"

            # Create request with headers
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Agents/1.0) WebTool",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )

            # Fetch content with timeout
            response = await asyncio.to_thread(
                urllib.request.urlopen, req, timeout=timeout
            )
            
            # Read content
            content_bytes = await asyncio.to_thread(response.read)
            
            # Try to decode with detected or default encoding
            content_type = response.headers.get("Content-Type", "")
            encoding = "utf-8"
            if "charset=" in content_type:
                encoding = content_type.split("charset=")[-1].split(";")[0].strip()
            
            try:
                html_content = content_bytes.decode(encoding)
            except:
                # Fallback to utf-8 with error handling
                html_content = content_bytes.decode("utf-8", errors="replace")

            # Convert HTML to markdown-like format
            markdown = self._html_to_markdown(html_content)
            
            # Add metadata
            result = [
                f"URL: {url}",
                f"Status: {response.status}",
                f"Content-Type: {content_type}",
                "=" * 40,
                "",
                markdown,
            ]
            
            return "\n".join(result)

        except HTTPError as e:
            return f"HTTP Error {e.code}: {e.reason} for URL: {url}"
        except URLError as e:
            return f"URL Error: {str(e)} for URL: {url}"
        except asyncio.TimeoutError:
            return f"Timeout: Request timed out after {timeout} seconds for URL: {url}"
        except Exception as e:
            return f"Error fetching URL: {str(e)}"

    async def _search_web(self, query: str, timeout: int) -> str:
        """Search the web using DuckDuckGo HTML version."""
        try:
            # Use DuckDuckGo HTML version for simplicity
            search_url = "https://html.duckduckgo.com/html/"
            params = urllib.parse.urlencode({"q": query})
            
            # Create POST request
            data = params.encode("utf-8")
            req = urllib.request.Request(
                search_url,
                data=data,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )

            # Fetch results
            response = await asyncio.to_thread(
                urllib.request.urlopen, req, timeout=timeout
            )
            html_content = await asyncio.to_thread(response.read)
            html_content = html_content.decode("utf-8", errors="replace")

            # Parse search results
            results = self._parse_search_results(html_content)
            
            if not results:
                return f"No results found for query: {query}"
            
            # Format results
            output = [
                f"Search Query: {query}",
                f"Results: {len(results)}",
                "=" * 40,
                "",
            ]
            
            for i, result in enumerate(results[:10], 1):  # Top 10 results
                output.append(f"{i}. {result['title']}")
                output.append(f"   URL: {result['url']}")
                if result.get('snippet'):
                    output.append(f"   {result['snippet']}")
                output.append("")
            
            return "\n".join(output)

        except Exception as e:
            return f"Error searching web: {str(e)}"

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to simple markdown format."""
        # Remove script and style elements
        html_content = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_match.group(1).strip()) if title_match else "No Title"
        
        # Convert common tags
        # Headers
        for i in range(6, 0, -1):
            html_content = re.sub(
                f"<h{i}[^>]*>(.*?)</h{i}>",
                lambda m: "\n" + "#" * i + " " + html.unescape(m.group(1).strip()) + "\n",
                html_content,
                flags=re.IGNORECASE | re.DOTALL,
            )
        
        # Paragraphs
        html_content = re.sub(
            r"<p[^>]*>(.*?)</p>",
            lambda m: "\n" + html.unescape(m.group(1).strip()) + "\n",
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        
        # Links
        html_content = re.sub(
            r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
            lambda m: f"[{html.unescape(m.group(2).strip())}]({m.group(1)})",
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        
        # Lists
        html_content = re.sub(
            r"<li[^>]*>(.*?)</li>",
            lambda m: "- " + html.unescape(m.group(1).strip()),
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        
        # Bold
        html_content = re.sub(
            r"<(?:b|strong)[^>]*>(.*?)</(?:b|strong)>",
            lambda m: f"**{html.unescape(m.group(1).strip())}**",
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        
        # Italic
        html_content = re.sub(
            r"<(?:i|em)[^>]*>(.*?)</(?:i|em)>",
            lambda m: f"*{html.unescape(m.group(1).strip())}*",
            html_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        
        # Line breaks
        html_content = re.sub(r"<br[^>]*>", "\n", html_content, flags=re.IGNORECASE)
        
        # Remove remaining tags
        html_content = re.sub(r"<[^>]+>", "", html_content)
        
        # Unescape HTML entities
        html_content = html.unescape(html_content)
        
        # Clean up whitespace
        lines = []
        for line in html_content.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)
        
        # Add title at the top
        result = f"# {title}\n\n" + "\n".join(lines)
        
        # Truncate if too long
        if len(result) > 5000:
            result = result[:5000] + "\n\n... (content truncated)"
        
        return result

    def _parse_search_results(self, html_content: str) -> list:
        """Parse search results from DuckDuckGo HTML."""
        results = []
        
        # Find result blocks
        result_blocks = re.findall(
            r'<div class="result__body">(.*?)</div>\s*</div>',
            html_content,
            re.DOTALL | re.IGNORECASE
        )
        
        for block in result_blocks:
            try:
                # Extract URL
                url_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*class="result__url"', block)
                if not url_match:
                    continue
                url = html.unescape(url_match.group(1))
                
                # Extract title
                title_match = re.search(r'<a[^>]*class="result__link"[^>]*>(.*?)</a>', block, re.DOTALL)
                title = html.unescape(re.sub(r'<[^>]+>', '', title_match.group(1)).strip()) if title_match else url
                
                # Extract snippet
                snippet_match = re.search(r'<div class="result__snippet"[^>]*>(.*?)</div>', block, re.DOTALL)
                snippet = html.unescape(re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()) if snippet_match else ""
                
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                })
                
            except Exception:
                continue
        
        return results