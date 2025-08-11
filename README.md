# Social & News Monitoring Dashboard

A modern Streamlit-based dashboard for tracking topics, people, or events across multiple social media platforms and news sites, with configurable email digests and AI-powered summaries.

## Features

- **Multi-platform Monitoring**: Track topics across Twitter/X, Reddit, Facebook, Instagram, YouTube, and news sites
- **Customizable Topics**: Add topics with custom keywords, profiles, and sources
- **Sleek UI**: Modern Apple-inspired UI with responsive cards, smooth animations, and intuitive navigation
- **Data Visualization**: Interactive time series charts, word clouds, and source distribution analytics
- **AI Summaries**: Generate concise topic summaries using local models via Ollama or HuggingFace
- **Configurable Email Digests**: Send daily, weekly, or custom frequency email reports
- **Non-blocking Operations**: Background processing for data collection and email sending
- **SQLite Database**: Efficient data storage and querying with SQLAlchemy
- **Photo Collection**: Gather relevant images from Unsplash or Pexels APIs

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

All values are **optional**. Without them the app still works using free public data. To unlock more features:

- **NEWSAPI_KEY** – Create a free account at [newsapi.org](https://newsapi.org) and paste the key
- **Reddit keys** – Visit [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps), create an app and copy the client ID and secret
- **UNSPLASH_ACCESS_KEY** or **PEXELS_API_KEY** – Add one of these to enable photo collection for your topics
- **Email Settings**:
  - **BREVO_API** – Sign up for a free [Brevo/Sendinblue](https://www.brevo.com/) account and copy your API key
  - **BREVO_FROM** – Email address to send from (must be validated in your Brevo account)
  - **BREVO_FROM_NAME** – Display name for the sender
- **AI Models**:
  - **OLLAMA_MODEL** – Install [Ollama](https://ollama.ai) and run `ollama pull qwen:latest`, then set `OLLAMA_MODEL=qwen`
  - **OPENAI_API_KEY** – Or use OpenAI for summary generation
- **Social Media Sources**:
  - **Twitter/X** – Uses snscrape (no authentication needed)
  - **Facebook pages** – No key required. When adding a topic, include public Facebook page URLs in the **Profiles** field
  - **Instagram** – Add Instagram usernames to the Profiles field
  - **YouTube** – Uses public search API (no authentication needed)

### 6. Run the Dashboard

```bash
streamlit run app.py
```

Your browser will open to the dashboard. Use the sidebar to add topics, optional keywords, and click **Collect Now** to fetch data.

### 7. What You'll See

- **Home Dashboard**: Overview of all your topics with key metrics
- **Topic View**: Detailed analysis of each topic with:
  - Time‑series charts and source distribution
  - Word cloud of common terms
  - Recent posts with links organized by platform
  - Interactive tabs for News, Reddit, Instagram, Facebook, YouTube, and Photos
  - AI‑generated summary of latest content
- **Newsletter Settings**: Configure email digest frequency (daily, weekly, every 2/3/4/5/6 days)
- **Intuitive Navigation**: Easy Home button navigation between views

### 8. Troubleshooting & Common Errors

| Message | How to fix |
| --- | --- |
| `Reddit credentials missing...` | Set `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in `.env`. Create a Reddit app if you don't have one. |
| `NewsAPI request failed...` | The key may be wrong or expired. Double‑check `NEWSAPI_KEY` in `.env` or remove it to use the free Google News RSS fallback. |
| `snscrape not installed` | Install with `pip install snscrape`. |
| `praw not installed` | Install with `pip install praw`. |
| `facebook-scraper not installed` | Install with `pip install "facebook-scraper[lxml]" lxml_html_clean`. |
| `Twitter fetch failed...blocked (404)` | Twitter/X may temporarily block anonymous scraping. Update to the latest snscrape with `pip install -U snscrape` or try again later. |
| `Background scheduler did not start` | The scheduler library may be missing or blocked. Collections can still be triggered manually with **Collect Now**. |
| `Email sending failed` | Check your Brevo API key and sender email configuration in the `.env` file. |
| `No photos found` | Set up `UNSPLASH_ACCESS_KEY` or `PEXELS_API_KEY` in your `.env` file to enable photo collection. |
| `Streamlit RuntimeError` | Try clearing your browser cache or using incognito mode. If persisting, restart the Streamlit server. |

More help and advanced tips are available in the comments within `.env.example` and in the source code.

## Recent Improvements

- **Email Digest Frequency**: Configure newsletter delivery schedule (daily, weekly, or custom frequency)
- **Non-blocking Email Sending**: Background threading prevents UI freezing during email operations
- **Improved Email Handling**: Better error handling for the Brevo API with 2xx response support
- **Enhanced Topic View**: Streamlined navigation with a single Home button and clear topic headers
- **Responsive Design**: Better mobile compatibility and layout improvements
- **Pinned Dependencies**: Specific package versions for improved stability

## Screenshots

*(Add your own screenshots here)*

## Security

All data and API keys remain local. Never commit `.env` files with secrets.

## License

MIT
