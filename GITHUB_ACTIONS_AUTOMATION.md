# GitHub Actions Automation Workflows

This document explains the automated GitHub Actions workflows for the Event Tracker Dashboard.

## Overview

We have two main automation workflows:

1. **Data Collection** - Runs every hour to collect data from all topics
2. **Digest Emails** - Runs daily at 7:55 AM Israel Time to send personalized digest emails

## 1. Data Collection Workflow

**File:** `.github/workflows/auto-collect-data.yml`

### Schedule
- **Automatic**: Every hour at minute 0 (e.g., 1:00, 2:00, 3:00, etc.)
- **Manual**: Can be triggered manually via GitHub Actions UI

### What it does
- Collects data from all shared topics in the database
- Uses the shared topic system for efficient data collection
- Sources include: Twitter, Reddit, News, YouTube, Instagram, Facebook, Photos
- Avoids duplicate collection (skips topics collected within last 30 minutes)
- Updates collection timestamps for each topic

### Configuration
The workflow requires these GitHub Secrets:
- `POSTGRES_URL` - Database connection string
- `OPENAI_API_KEY` - For AI summarization
- Email configuration (for notifications)
- API keys for various data sources (Twitter, Reddit, etc.)

### Manual Triggering
You can manually trigger with options:
- `force_collection` - Force collection even for recently collected topics
- `specific_topics` - Collect only specific topic IDs (comma-separated)

## 2. Digest Email Workflow

**File:** `.github/workflows/auto-send-digest-emails.yml`

### Schedule
- **Automatic**: Daily at 7:55 AM Israel Time
- **Cron**: `55 4 * * *` (4:55 AM UTC = 7:55 AM Israel Time in winter)
- **Manual**: Can be triggered manually via GitHub Actions UI

### What it does
1. Finds all eligible users (non-guests with email addresses and digest enabled)
2. Filters users based on their digest frequency preferences (daily, weekly, etc.)
3. Generates personalized digest emails with AI summaries
4. Sends emails using Gmail SMTP (primary) with Brevo fallback
5. Updates user's `last_digest_sent` timestamp
6. Provides detailed statistics and error reporting

### User Eligibility
Users receive digests if:
- They have `digest_enabled = true`
- They have a valid email address
- They are not guest users
- Enough time has passed based on their frequency setting

### Digest Frequencies Supported
- Daily
- Every 2-6 days
- Weekly
- Monthly

### Configuration
Required GitHub Secrets:
- `POSTGRES_URL` - Database connection
- `OPENAI_API_KEY` - For AI digest summaries
- **Email Configuration:**
  - `EMAIL_HOST` - Gmail SMTP host (smtp.gmail.com)
  - `EMAIL_PORT` - SMTP port (587)
  - `EMAIL_USER` - Gmail email address
  - `EMAIL_PASS` - Gmail app password
- **Brevo Fallback:**
  - `BREVO_API` - Brevo API key
  - `BREVO_FROM` - Sender email for Brevo
  - `BREVO_FROM_NAME` - Sender name for Brevo
- **Testing:**
  - `TEST_EMAIL` - Email address for test mode

### Manual Triggering
You can manually trigger with options:
- `test_mode` - Send all digests to the test email address
- `force_send` - Force send even if users received digest today
- `specific_user_ids` - Send only to specific user IDs (comma-separated)

## Helper Scripts

### `automation_digest_sender.py`
A standalone Python script that handles digest email sending. Can be run locally or in CI/CD:

```bash
# Send digests normally
python automation_digest_sender.py

# Test mode
python automation_digest_sender.py --test-mode --test-email="test@example.com"

# Force send to specific users
python automation_digest_sender.py --force-send --specific-user-ids="1,2,3"
```

## Monitoring and Troubleshooting

### Workflow Status
Check the GitHub Actions tab in your repository to see:
- Workflow run history
- Success/failure status
- Detailed logs for each step

### Common Issues

1. **Database Connection Failures**
   - Check `POSTGRES_URL` secret is correct
   - Verify database is accessible from GitHub Actions

2. **Email Sending Failures**
   - Verify Gmail SMTP credentials
   - Check if Gmail app password is correctly set
   - Ensure Brevo fallback is configured

3. **API Rate Limits**
   - Data collection may hit rate limits on social media APIs
   - Workflows include delays and retry logic

### Logs and Debugging
Each workflow provides detailed logs including:
- Number of topics/users processed
- Success/failure counts
- Error messages with stack traces
- Database statistics
- Processing times

## Security Notes

- All sensitive data is stored in GitHub Secrets
- Secrets are not exposed in logs
- Database credentials use encrypted connections
- Email credentials support app passwords for additional security

## Customization

### Changing Schedule
Edit the `cron` expressions in the workflow files:
- Data collection: Currently every hour
- Digest emails: Currently 7:55 AM Israel Time

### Adding New Data Sources
1. Update the collectors in `monitoring/collectors.py`
2. Add new source to shared collectors
3. Configure any required API keys as GitHub Secrets

### Custom Email Templates
Modify the digest HTML generation in `ui/sidebar.py`:
- `create_enhanced_digest_html()` - Main email template
- `generate_digest_ai_summary()` - AI summary generation

## Israel Time Considerations

The digest workflow uses UTC time but aims for 7:55 AM Israel Time:
- **Israel Standard Time**: UTC+2 (summer) → 5:55 AM UTC
- **Israel Daylight Time**: UTC+3 (winter) → 4:55 AM UTC
- Current setting: 4:55 AM UTC (covers winter time, will be 1 hour early in summer)

To adjust for daylight saving time automatically, consider using a more sophisticated scheduling solution or manually updating the cron schedule twice a year.

## Performance

- **Data Collection**: Typically takes 10-30 minutes depending on number of topics
- **Digest Emails**: Usually takes 2-10 minutes depending on number of users
- **Rate Limiting**: Built-in delays prevent overwhelming external APIs
- **Database**: Uses optimized queries to minimize database load

## Getting Started

1. Set up all required GitHub Secrets
2. Ensure database is accessible and contains user data
3. Test both workflows manually first
4. Monitor the first few automatic runs
5. Adjust settings as needed based on your usage patterns
