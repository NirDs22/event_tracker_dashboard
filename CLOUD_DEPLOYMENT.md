# Streamlit Cloud Deployment Notes

This document outlines important considerations when deploying this application to Streamlit Cloud.

## Cloud-Specific Configurations

The application includes specific optimizations for Streamlit Cloud:

1. **Environment Detection**:
   - The app automatically detects if it's running in Streamlit Cloud and makes UI adjustments accordingly
   - Look for `IS_CLOUD` variable in the code which handles these adaptations

2. **Custom CSS**:
   - Special CSS files are loaded in the `.streamlit` directory:
     - `style.css`: General styling improvements
     - `custom_css.css`: Cloud-specific fixes for layout issues

3. **Card Height Adjustments**:
   - The app increases card heights slightly when running in the cloud environment
   - This prevents content truncation which can happen due to different rendering behaviors

4. **Font Handling**:
   - The app uses system fonts as fallbacks when custom fonts can't be loaded
   - This ensures consistent typography across different deployment environments

5. **Responsive Layout**:
   - Column layouts use explicit ratios (`[1, 1]` instead of `2`)
   - Container widths are set for all charts and visualizations

## Troubleshooting Cloud Issues

If you encounter display issues in Streamlit Cloud:

1. **Check CSS Loading**:
   - Make sure the `.streamlit` directory and its contents are properly deployed
   - Consider adding additional CSS fixes in the `.streamlit/custom_css.css` file

2. **Monitor Console Errors**:
   - Use browser developer tools to check for any console errors
   - Look for blocked resources or CSP violations

3. **Layout Problems**:
   - If layouts appear broken, check column definitions and ensure they use explicit ratios
   - Add additional responsive CSS for problematic components

4. **Image Loading**:
   - Some image URLs might be blocked by CSP in cloud environments
   - Consider using proxy services or ensuring all image URLs use HTTPS

5. **Performance Issues**:
   - The cloud environment might have different resource limitations
   - Consider optimizing heavy operations or large datasets

## Testing Changes

Before pushing updates to production:

1. Test locally first
2. Check both desktop and mobile views
3. Test with different screen sizes using browser developer tools
4. Verify that all interactive elements work correctly
