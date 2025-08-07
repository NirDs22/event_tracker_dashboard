# Social & News Monitoring Dashboard

A Streamlit-based dashboard for tracking people or topics across Twitter, Reddit and news sites.

## Features

- Add topics with custom keywords
- Automatic collection from Twitter (snscrape), Reddit (PRAW) and NewsAPI
- SQLite database storage using SQLAlchemy
- Word clouds, time series charts and AI summaries
- Daily scheduled collection and optional email digests

## Setup

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Provide API keys**

Create a `.env` file or export environment variables:

```
OPENAI_API_KEY=...
NEWSAPI_KEY=...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
SMTP_HOST=...
SMTP_USER=...
SMTP_PASSWORD=...
```

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
