"""Summarise collections of posts using an LLM."""
import os
import re
from typing import List, Optional
import logging

# Configure logging for better error tracking
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_HF_MODEL = "facebook/bart-large-cnn"
MAX_INPUT_LENGTH = 4000
SUMMARY_MAX_LENGTH = 150
SUMMARY_MIN_LENGTH = 40


def summarize(texts: List[str]) -> str:
    """
    Return a concise summary of provided texts using available AI models.
    
    Attempts to use models in order of preference:
    1. Ollama (local AI model) - if configured
    2. Simple text extraction - lightweight fallback
    
    Args:
        texts: List of text strings to summarize
        
    Returns:
        A concise summary string
    """
    if not texts:
        return "No content to summarise."
    
    # Join texts and limit input length
    joined = "\n".join(text.strip() for text in texts if text.strip())[:MAX_INPUT_LENGTH]
    
    if not joined.strip():
        return "No meaningful content to summarise."

    # Try Ollama first (preferred for quality)
    summary = _try_ollama_summary(joined)
    if summary:
        return summary
    
    # Lightweight fallback: simple text extraction (no model downloads)
    logger.info("Ollama not available, using simple text extraction")
    return _simple_fallback(joined)


def _try_ollama_summary(text: str) -> Optional[str]:
    """Attempt to summarize using Ollama local AI model."""
    from .secrets import get_secret
    model = get_secret("OLLAMA_MODEL")
    ollama_host = get_secret("OLLAMA_HOST", "http://localhost:11434")
    
    if not model:
        return None
        
    try:
        import ollama
        
        # Set the host for Ollama
        client = ollama.Client(host=ollama_host)
        
        prompt = (
            "Summarize the following social media and news content in 2-3 sentences. "
            "Focus on the main topics, key events, and overall sentiment. "
            "Use bullet points for clarity and bold important phrases."
            "Order your response with the most important points first."
            "Be concise (medium length) and informative:\n\n" + text[:2000]  # Limit input size
        )
        
        # Generate summary with qwen3:4b specific parameters
        response = client.generate(
            model=model,
            prompt=prompt,
            options={
                "temperature": 0.3,  # Lower temperature for more focused summaries
                "top_p": 0.9,
                "max_tokens": 200,   # Limit output length
                "stop": ["---", "\n\n\n"]  # Stop tokens to prevent rambling
            }
        )
        
        summary = response.get("response", "").strip()
        
        if summary and len(summary.split()) > 5:  # Ensure meaningful content
            logger.info(f"Successfully generated summary using Ollama model: {model}")
            return strip_think(summary)
        else:
            logger.warning(f"Ollama returned empty or too short summary")
            
    except ImportError:
        logger.error("ollama package not installed. Install with: pip install ollama")
    except Exception as exc:
        logger.error(f"Ollama summarization failed: {exc}")
        logger.error(f"Check if Ollama is running and model '{model}' is available")
    
    return None


def _simple_fallback(text: str) -> str:
    """Enhanced fallback: extract key sentences and create a summary."""
    # Split into sentences
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    
    if not sentences:
        return strip_think(text[:300] + "...")
    
    # Take first and last sentences, plus any with key indicator words
    key_words = ['breaking', 'announced', 'revealed', 'confirmed', 'reported', 'according', 'new', 'first', 'major']
    
    summary_sentences = []
    
    # Always include first sentence
    if sentences:
        summary_sentences.append(sentences[0])
    
    # Add sentences with key words
    for sentence in sentences[1:-1]:
        if any(word in sentence.lower() for word in key_words) and len(summary_sentences) < 3:
            summary_sentences.append(sentence)
    
    # Add last sentence if we have room and it's different from first
    if len(sentences) > 1 and len(summary_sentences) < 3:
        summary_sentences.append(sentences[-1])
    
    summary = '. '.join(summary_sentences[:3])
    if not summary.endswith('.'):
        summary += '.'
        
    return strip_think(summary)


def strip_think(text: str) -> str:
    """
    Remove <think>...</think> sections and other unwanted patterns from text.
    
    Args:
        text: Input text that may contain thinking patterns
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove <think>...</think> sections
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    
    # Remove other common AI artifacts
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)  # Remove bold markdown
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)      # Remove italic markdown
    cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)  # Remove code blocks
    
    # Clean up whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)  # Multiple spaces to single space
    cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)  # Multiple newlines to double newline
    
    return cleaned.strip()
