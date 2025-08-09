"""Summarise collections of posts using an LLM."""
import os
import re
from typing import List


def summarize(texts: List[str]) -> str:
    """Return a concise summary of provided texts."""
    if not texts:
        return "No content to summarise."
    joined = "\n".join(texts)[:4000]

    # Prefer local models served by Ollama when configured
    model = os.getenv("OLLAMA_MODEL")
    if model:
        try:
            import ollama

            prompt = (
                "Provide a short news style summary of the following:\n" + joined
            )
            result = ollama.generate(model=model, prompt=prompt)
            return strip_think(result.get("response", ""))
        except Exception as exc:
            print("Ollama summarisation failed", exc)

    # Use transformers summariser (downloads model on first run)
    try:
        from transformers import pipeline

        model_name = os.getenv("HF_SUMMARY_MODEL", "t5-small")
        summarizer = pipeline("summarization", model=model_name)
        result = summarizer(joined, max_length=120, min_length=30, do_sample=False)
        return strip_think(result[0]["summary_text"])
    except Exception as exc:
        print("transformers pipeline failed", exc)

    return strip_think(joined[:500])


def strip_think(text: str) -> str:
    """Remove <think>...</think> sections from text."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
