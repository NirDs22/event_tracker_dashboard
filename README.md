# 📰 Social & News Monitor

A comprehensive **Event Tracker Dashboard** that monitors topics across multiple sources including social media, news sites, and RSS feeds. Built with Streamlit for easy deployment to Streamlit Cloud.

## 🚀 Features

- **Multi-Source Monitoring**: Track topics across Twitter/X, Facebook, Instagram, Reddit, YouTube, and news sources
- **Real Data Collection**: Professional web scraping with RSS feeds and proper rate limiting
- **Shared Topics**: Multi-user collaboration with shared topic subscriptions
- **Smart Authentication**: Secure user authentication with guest access
- **Real-time Updates**: Automatic background data collection and scheduling
- **Interactive Dashboard**: Beautiful visualizations with Plotly and custom UI components
- **Cloud-Ready**: Optimized for Streamlit Cloud deployment

## 📋 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/event-tracker-dashboard.git
   cd event-tracker-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Health Check**
   ```bash
   python3 health_check.py
   ```

### 🌐 Streamlit Cloud Deployment

1. **Fork/Clone this repository** to your GitHub account

2. **Deploy to Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Select this repository
   - Set the main file path to `app.py`
   - Deploy!

3. **Configuration**: The app is pre-configured for cloud deployment with:
   - Optimized `requirements.txt` with minimal dependencies
   - Python 3.10.12 runtime specification
   - Proper Streamlit configuration in `.streamlit/config.toml`
   - Cloud-aware app initialization

## 🛠 Technical Architecture

### Core Components

- **`app.py`**: Main Streamlit application entry point
- **`monitoring/`**: Data collection and database management
  - `collectors.py`: Web scraping and RSS feed collection
  - `database.py`: SQLAlchemy models and database operations
  - `scheduler.py`: Background task scheduling
- **`auth/`**: User authentication system
- **`ui/`**: User interface components and styling

### Data Collection Strategy

1. **RSS Feeds First**: Most reliable method using Google News RSS and platform-specific feeds
2. **Web Search Fallback**: DuckDuckGo search with proper rate limiting and retry logic
3. **Platform-Specific**: Targeted collection for each social media platform
4. **Professional Rate Limiting**: Conservative delays and request patterns

### Database Schema

- **Users**: Authentication and user management
- **SharedTopics**: Multi-user topic collaboration
- **SharedPosts**: Collected content for shared topics
- **UserTopicSubscriptions**: User-topic relationships

## 📦 Dependencies

**Core Requirements** (optimized for cloud deployment):
- `streamlit==1.48.1` - Web framework
- `pandas==2.2.2` - Data processing
- `plotly==5.24.1` - Interactive visualizations  
- `sqlalchemy==2.0.34` - Database ORM
- `feedparser==6.0.11` - RSS feed parsing
- `beautifulsoup4==4.12.3` - HTML parsing
- `requests==2.32.4` - HTTP requests
- `apscheduler==3.11.0` - Background scheduling
- `extra-streamlit-components` - Enhanced UI components
- `wordcloud==1.9.4` - Text visualization

## 🔧 Configuration

### Streamlit Configuration
The app uses `.streamlit/config.toml` for optimal cloud performance:
- Light theme with custom colors
- Wide layout for dashboard experience
- Minimal toolbar mode
- Headless server configuration

### Environment Variables
Optional configuration via Streamlit secrets or environment:
- Database connection strings
- API keys for enhanced features
- Rate limiting parameters

## 🚨 Important Notes for Cloud Deployment

1. **Database**: Uses PostgreSQL on Neon cloud database for production, SQLite fallback for local development
2. **Data Storage**: All data stored in secure cloud database with automatic backups
3. **Memory Usage**: Optimized for cloud resource limits
4. **Rate Limiting**: Conservative web scraping to avoid IP blocks
5. **Error Handling**: Robust error handling for network issues

## 🔍 Data Sources

- **News**: Google News RSS, Bing News RSS
- **Social Media**: Platform-specific search strategies
- **Reddit**: Native RSS feeds
- **YouTube**: RSS feed integration
- **Photos**: Multi-platform image search

## 🧪 Health Monitoring

Run the health check before deployment:
```bash
python3 health_check.py
```

This verifies:
- ✅ All dependencies import correctly
- ✅ Database initializes properly  
- ✅ Data collectors function
- ✅ Core functionality works

## 📈 Performance

- **Startup Time**: ~3-5 seconds on Streamlit Cloud
- **Data Collection**: 10-50 posts per topic per source
- **Background Tasks**: Automatic scheduling for data updates
- **Memory Usage**: Optimized for cloud constraints

## 🔒 Security

- Secure user authentication with bcrypt password hashing
- Session-based authentication with secure tokens
- Guest access with automatic cleanup
- Rate limiting to prevent abuse

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run health checks
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

For issues with deployment or functionality:
1. Check the health check output: `python3 health_check.py`
2. Review Streamlit Cloud logs
3. Verify all dependencies in `requirements.txt`
4. Check database permissions and file access

---

**Ready for Streamlit Cloud! 🚀**
