# Social & News Monitoring Dashboard

A Streamlit-based dashboard for tracking people or topics across Twitter, Reddit and news sites.

## Features

- Add topics with custom keywords
- Automatic collection from Twitter (snscrape), Reddit (PRAW) and News (NewsAPI or Google News RSS)
- SQLite database storage using SQLAlchemy
- Word clouds, time series charts and AI summaries (supports local models via Ollama or HuggingFace)
- Daily scheduled collection and optional email digests

## Beginner-Friendly Setup Guide

These steps work on **Windows, macOS and Linux**. No prior Python knowledge is required.

### 1. Install Python and Git

1. Visit [python.org](https://www.python.org/downloads/) and install Python 3.9 or newer.
   - On Windows, tick "Add Python to PATH" during installation.
2. Install [Git](https://git-scm.com/downloads) so you can clone the repository.

### 2. Download the Project

Open your terminal (Command Prompt on Windows or Terminal on Mac/Linux) and run:

```bash
git clone https://github.com/example/event_tracker_dashboard.git
cd event_tracker_dashboard
```

### 3. (Optional) Create a Virtual Environment

Keeping dependencies isolated is recommended but optional:

```bash
python -m venv venv
# Activate it
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate        # Windows
```

### 4. Install Requirements

```bash
pip install -r requirements.txt
```

### 5. Create a Configuration File

Copy the sample environment file and edit it with any text editor:

```bash
cp .env.example .env           # macOS/Linux
copy .env.example .env         # Windows
```

All values are **optional**. Without them the app still works using free public data. To unlock more sources:

- **NEWSAPI_KEY** – create a free account at [newsapi.org](https://newsapi.org) and paste the key.
- **Reddit keys** – visit [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps), create an app and copy the client ID and secret.
- **SMTP settings** – needed only if you want daily email digests.
- **OLLAMA_MODEL** – install [Ollama](https://ollama.ai) and run `ollama pull qwen:latest`, then set `OLLAMA_MODEL=qwen` for local AI summaries.

### 6. Run the Dashboard

```bash
streamlit run app.py
```

Your browser will open to the dashboard. Use the sidebar to add topics, optional keywords, and click **Collect Now** to fetch data.

### 7. What You'll See

- Time‑series chart of mentions
- Word cloud of common terms
- Recent posts with links
- AI‑generated summary of latest content

### 8. Troubleshooting & Common Errors

| Message | How to fix |
| --- | --- |
| `Reddit credentials missing...` | Set `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in `.env`. Create a Reddit app if you don't have one. |
| `NewsAPI request failed...` | The key may be wrong or expired. Double‑check `NEWSAPI_KEY` in `.env` or remove it to use the free Google News RSS fallback. |
| `snscrape not installed` | Install with `pip install snscrape`. |
| `praw not installed` | Install with `pip install praw`. |
| `Background scheduler did not start` | The scheduler library may be missing or blocked. Collections can still be triggered manually with **Collect Now**. |

More help and advanced tips are available in the comments within `.env.example` and in the source code.

## Screenshots

*(Add your own screenshots here)*

## Security

All data and API keys remain local. Never commit `.env` files with secrets.

## License

MIT
