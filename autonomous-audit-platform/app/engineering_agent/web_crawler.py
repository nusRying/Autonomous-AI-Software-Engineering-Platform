"""
web_crawler.py — Integration with Crawl4AI for requirement extraction.
"""
from typing import Dict, Any, Optional
from loguru import logger

try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("Crawl4AI not installed. Web analysis will use basic fallback.")

class RequirementCrawler:
    """
    Analyzes existing web applications to reverse-engineer requirements.
    """
    
    async def analyze_url(self, url: str) -> Dict[str, Any]:
        """
        Crawls a URL and returns a technical summary of the page structure and features.
        """
        if not CRAWL4AI_AVAILABLE:
            return self._basic_fallback(url)

        try:
            logger.info(f"Crawling URL for requirement analysis: {url}")
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                
                # Crawl4AI provides markdown and structured metadata
                return {
                    "url": url,
                    "title": result.metadata.get("title", "Unknown"),
                    "markdown_content": result.markdown[:5000], # Truncate for prompt efficiency
                    "links": result.metadata.get("links", []),
                    "status": "success",
                    "engine": "crawl4ai"
                }
        except Exception as e:
            logger.error(f"Crawl4AI failed: {e}")
            return self._basic_fallback(url)

    def _basic_fallback(self, url: str) -> Dict[str, Any]:
        """Simple fallback analysis if Crawl4AI is missing."""
        import httpx
        try:
            # Just fetch the HTML and return it as context
            return {
                "url": url,
                "note": "Basic fallback used. Full crawl4ai not available.",
                "status": "partial_success",
                "engine": "httpx"
            }
        except Exception:
            return {"url": url, "status": "failed", "error": "Could not reach URL"}
