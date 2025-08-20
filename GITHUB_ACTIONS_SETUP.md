# GitHub Actions Auto Data Collection Setup Guide

## Overview
This GitHub Actions workflow automatically collects data for all shared topics every hour and stores it in your PostgreSQL database on Neon.

## Required GitHub Secrets

To set up the automated data collection, you need to configure the following secrets in your GitHub repository:

### Go to: Repository → Settings → Secrets and Variables → Actions

Add these secrets:

### Database Connection
- `POSTGRES_URL` - Your Neon PostgreSQL connection string
  - Format: `postgresql://username:password@host/database?sslmode=require`
  - Get this from your Neon dashboard

### API Keys for Data Sources
- `OPENAI_API_KEY` - OpenAI API key for AI summaries
- `NEWS_API_KEY` - NewsAPI key for news collection
- `REDDIT_CLIENT_ID` - Reddit API client ID
- `REDDIT_CLIENT_SECRET` - Reddit API client secret
- `REDDIT_USER_AGENT` - Reddit API user agent string

### Email Configuration (Optional)
- `EMAIL_FROM` - Your sender email address
- `EMAIL_PASSWORD` - Email password or app password
- `SMTP_SERVER` - SMTP server (e.g., smtp.gmail.com)
- `SMTP_PORT` - SMTP port (e.g., 587)

## Workflow Features

### ⏰ **Scheduling**
- Runs every hour automatically (`0 * * * *`)
- Can be triggered manually via GitHub Actions UI
- Includes manual override for force collection

### 🛡️ **Safety Features**
- 45-minute timeout to prevent runaway jobs
- Skip topics collected within the last 30 minutes
- Health checks after collection
- Error reporting and monitoring
- Database connection testing

### 📊 **Data Collection**
- Collects from multiple sources: News, Reddit, Twitter, YouTube
- Intelligent source selection based on topic keywords
- Batch processing for efficiency
- Duplicate post prevention
- Progress tracking and logging

### 🔍 **Monitoring**
- Real-time collection progress
- Success/failure reporting
- Database health checks
- Post count tracking
- Error alerting

## Workflow Files Created

### `.github/workflows/auto-collect-data.yml`
- Main collection workflow
- Runs every hour
- Two jobs: `collect-data` and `health-check`
- Complete error handling and reporting

## Manual Triggers

### Force Collection
You can manually trigger the workflow with force collection:

1. Go to Actions tab in your repository
2. Select "Auto Collect Data Every Hour"
3. Click "Run workflow"
4. Enable "Force collection for all topics" if needed

### Monitoring Workflow

The workflow provides detailed logging:

```
🚀 Starting automated data collection...
⏰ Collection started at: 2025-08-20 14:00:00 UTC
📋 Processing 5 topics...
🔄 Collecting data for topic: AI Technology
✅ Successfully collected 12 posts for AI Technology
📊 Collection Summary:
✅ Successful topics: 5
❌ Failed topics: 0
📊 Posts collected in last hour: 47
```

## Error Handling

The workflow handles various error scenarios:
- Database connection failures
- API rate limits
- Network timeouts
- Invalid topic configurations
- Missing secrets

If more than 50% of topics fail, the workflow exits with an error code for alerting.

## Database Updates

The workflow:
- ✅ Tests database connection before collection
- ✅ Initializes database tables if needed
- ✅ Updates topic collection timestamps
- ✅ Prevents duplicate posts
- ✅ Runs health checks after collection
- ✅ Tracks collection statistics

## Performance Optimization

- Intelligent source selection per topic
- Batch processing where possible
- Skip recently collected topics (30-min cooldown)
- Connection pooling for database efficiency
- Timeout protection for long-running jobs

## Next Steps

1. **Add GitHub Secrets**: Configure all required secrets in repository settings
2. **Test Manual Run**: Trigger workflow manually to test setup
3. **Monitor Logs**: Check workflow logs for any issues
4. **Verify Data**: Confirm new posts appear in your application
5. **Optional**: Set up notifications for failures

## Troubleshooting

### Common Issues:
- **Missing secrets**: Check all required secrets are configured
- **Database connection**: Verify `POSTGRES_URL` is correct
- **API limits**: Some sources may have rate limits
- **Timeout**: Large topic collections may need timeout adjustment

### Debug Steps:
1. Check workflow logs in GitHub Actions
2. Verify secrets are properly set
3. Test database connection manually
4. Check API key validity
5. Monitor Neon database dashboard

The workflow will now automatically keep your database updated with fresh content every hour! 🚀
