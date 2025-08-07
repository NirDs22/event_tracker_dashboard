# Social & News Monitoring Dashboard

A Streamlit-based dashboard for tracking people or topics across Twitter, Reddit and news sites.

## Features

- Add topics with custom keywords
- Automatic collection from Twitter (snscrape), Reddit (PRAW) and News (NewsAPI or Google News RSS)
- SQLite database storage using SQLAlchemy
- Word clouds, time series charts and AI summaries (supports local models via Ollama or HuggingFace)
- Daily scheduled collection and optional email digests

## Setup

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Optional configuration**

The app works with public sources out of the box. To enable Reddit, NewsAPI or
email digests, copy the example file and fill in your own values:

```
cp .env.example .env
```

If `NEWSAPI_KEY` is missing the app falls back to Google News RSS. When no
`OLLAMA_MODEL` is set summaries are generated with a small Transformers model
(`t5-small`).

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
