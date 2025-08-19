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




def summarize_posts_for_digest(contents: List[str]) -> str:
    """
    Create a brief digest summary of posts for email.
    Focuses on key themes and important developments.
    """
    if not contents:
        return "No recent activity in your monitored topics."
    
    # Join content with topic context
    combined_text = "\n".join(contents)[:MAX_INPUT_LENGTH]
    
    try:
        # Use g4f for digest summarization with a specific prompt
        import g4f
        
        digest_prompt = f"""
        Create a very short summary of these posts organized by topic. Only include the most important/newsworthy points. Format as:

        **Topic Name**: Key point or development
        **Another Topic**: Important update

        Keep each point to 1 short sentence. Maximum 3-4 topics total. Skip boring or routine content.
        
        Content to summarize:
        {combined_text}
        """
        
        # Try multiple models for better reliability
        models_to_try = [
            g4f.models.gpt_4o_mini,
            g4f.models.gemini_pro,
            g4f.models.claude_3_5_sonnet
        ]
        
        for model in models_to_try:
            try:
                response = g4f.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "user", "content": digest_prompt}],
                    timeout=30
                )
                
                if response and len(response.strip()) > 20:
                    # Clean up the response
                    summary = response.strip()
                    # Remove any quotation marks that might wrap the response
                    summary = summary.strip('"\'')
                    return summary
                    
            except Exception as e:
                logger.warning(f"Failed to generate digest summary with {model}: {e}")
                continue
        
        # Fallback to basic text processing if AI fails
        return _generate_basic_digest_summary(contents)
        
    except Exception as e:
        logger.error(f"Error in digest summarization: {e}")
        return _generate_basic_digest_summary(contents)


def _generate_basic_digest_summary(contents: List[str]) -> str:
    """Generate a basic digest summary without AI, organized by topics."""
    if not contents:
        return "No recent activity in your monitored topics."
    
    # Extract topics and their key content
    topic_summaries = {}
    
    for content in contents:
        # Extract topic name (format: "Topic: TopicName - content")
        if "Topic:" in content and " - " in content:
            parts = content.split("Topic:")[1].split(" - ", 1)
            if len(parts) >= 2:
                topic_name = parts[0].strip()
                topic_content = parts[1].strip()
                
                if topic_name not in topic_summaries:
                    topic_summaries[topic_name] = []
                
                # Extract first meaningful sentence
                sentences = [s.strip() for s in topic_content.split('.') if s.strip() and len(s.strip()) > 20]
                if sentences:
                    topic_summaries[topic_name].append(sentences[0])
    
    if not topic_summaries:
        return f"Recent activity across your monitored topics with {len(contents)} new posts to review."
    
    # Format as topic-organized summary
    summary_parts = []
    for topic, content_list in list(topic_summaries.items())[:4]:  # Max 4 topics
        if content_list:
            # Take the most relevant content
            key_content = content_list[0][:100]  # Limit length
            summary_parts.append(f"**{topic}**: {key_content}")
    
    if summary_parts:
        return "\n".join(summary_parts)
    else:
        return f"Recent updates across {len(topic_summaries)} topics with new posts to review."


def summarize(texts: List[str]) -> str:
    """
    Return a concise summary of provided texts using available AI models.
    Attempts to use models in order of preference:
    1. g4f (try up to 3 models)
    2. Ollama (local AI model)
    3. Simple text extraction
    """
    if not texts:
        return "No content to summarise."
    joined = "\n".join(text.strip() for text in texts if text.strip())[:MAX_INPUT_LENGTH]
    if not joined.strip():
        return "No meaningful content to summarise."

    # Try g4f models in order, without freezing UI
    g4f_models = [ "gpt-4", "mixtral-8x7b", "gpt-3.5-turbo"]
    import streamlit as st
    try:
        import g4f
        for model_name in g4f_models:
            with st.spinner(f"Please wait... Trying AI model: {model_name}"):
                try:
                    response = g4f.ChatCompletion.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are an expert summarizer. Summarize the following social media and news content in 2-3 sentences. Focus on the main topics, key events, and overall sentiment. Use bullet points for clarity and bold important phrases. Order your response with the most important points first. Be concise (medium length) and informative."},
                            {"role": "user", "content": joined[:2000]}
                        ]
                    )
                    summary = response.strip()
                    if summary and len(summary.split()) > 5:
                        st.success(f"AI ({model_name}) summary generated.")
                        logger.info(f"Successfully generated summary using g4f model: {model_name}")
                        print(response)
                        return strip_think(summary)
                except Exception as e:
                    st.warning(f"AI model {model_name} failed: {e}")
                    logger.warning(f"g4f model {model_name} failed: {e}")
                    continue
    except Exception as e:
        st.error(f"g4f import or all models failed: {e}")
        logger.warning(f"g4f import or all models failed: {e}")

    # Try Ollama next
    summary = _try_ollama_summary(joined)
    if summary:
        return summary

    # Lightweight fallback: simple text extraction (no model downloads)
    logger.info("No AI available, using simple text extraction")
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
