# Social & News Monitoring Dashboard

A Streamlit-based dashboard for tracking people or topics across Twitter, Reddit and news sites.

## Features

- Add topics with custom keywords
- Automatic collection from Twitter (snscrape), Reddit (PRAW) and NewsAPI
- SQLite database storage using SQLAlchemy
- Word clouds, time series charts and AI summaries (supports local models via Ollama)
- Daily scheduled collection and optional email digests

## Setup

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Provide configuration**

Copy the example file and fill in your own values:

```
cp .env.example .env
```

The most important values are API keys for Reddit and NewsAPI as well as
the model name served by [Ollama](https://ollama.com/).  By default the
app looks for a locally running model such as Qwen3 via `OLLAMA_MODEL`.
OpenAI keys are optional and only used when provided.

3. **Run the dashboard**

```bash
streamlit run app.py
```

The app stores data in `tracker.db` in the project directory. The scheduler runs in the background and collects new posts every 24 hours.

## Screenshots

*(Add your own screenshots here)*

## Security

All data and API keys remain local. Never commit `.env` files with secrets.

## License

MIT
