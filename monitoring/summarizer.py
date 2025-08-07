"""Summarise collections of posts using an LLM."""
import os
from typing import List


def summarize(texts: List[str]) -> str:
    """Return a concise summary of provided texts."""
    if not texts:
        return "No content to summarise."
    joined = "\n".join(texts)[:4000]
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        try:
            import openai
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Provide a short news style summary"},
                    {"role": "user", "content": joined}
                ]
            )
            return response['choices'][0]['message']['content']
        except Exception as exc:
            print('OpenAI summarisation failed', exc)
    # Fallback to transformers summariser
    try:
        from transformers import pipeline
        summarizer = pipeline('summarization')
        result = summarizer(joined, max_length=120, min_length=30, do_sample=False)
        return result[0]['summary_text']
    except Exception as exc:
        print('transformers pipeline failed', exc)
    return joined[:500]
