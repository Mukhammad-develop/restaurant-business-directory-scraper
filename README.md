# 🍽️ Restaurant Business Directory Scraper

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-production--ready-brightgreen)]()

A comprehensive, enterprise-grade restaurant and business directory scraper that collects data from **Yelp** and **Google Maps**. This tool is designed for marketing agencies, restaurants, and businesses looking for lead generation and market intelligence.

## ✨ Features

### 🔍 **Multi-Platform Scraping**
- **Yelp Integration**: Complete business listings, reviews, ratings, and contact information
- **Google Maps Integration**: Business details, location data, and customer reviews
- **Unified Data Model**: Seamlessly combines data from multiple sources

### 📊 **Comprehensive Data Collection**
- Business name, address, phone number, website, email
- Category, cuisine type, price level, ratings, review count
- Operating hours, features, and amenities
- Customer reviews with sentiment analysis
- Geographic coordinates and location data

### 🛡️ **Anti-Bot Protection**
- **Proxy Rotation**: Support for multiple proxy servers with automatic rotation
- **User-Agent Rotation**: Dynamic user agent switching to avoid detection
- **Undetected ChromeDriver**: Advanced anti-detection browser automation
- **Request Delays**: Configurable delays to mimic human behavior

### 🔧 **Data Processing & Validation**
- **Email Validation**: Verify email addresses for deliverability
- **Duplicate Removal**: Intelligent deduplication based on name and location similarity
- **Data Cleaning**: Normalize phone numbers, addresses, and other fields
- **Advanced Filtering**: Filter by rating, cuisine type, location, and more

### 📈 **Analytics & Visualization**
- **Interactive Maps**: Folium-based maps with business locations and details
- **Analytics Dashboard**: Comprehensive charts and statistics using Plotly
- **Sentiment Analysis**: VADER and TextBlob-powered review sentiment analysis
- **Export Formats**: CSV, Excel, and Google Sheets integration

### ⏰ **Automation & Scheduling**
- **Task Scheduler**: Automated scraping with cron-like scheduling
- **Background Processing**: Run tasks daily, weekly, or monthly
- **CLI Management**: Command-line interface for task management
- **Persistent Storage**: Task configurations saved and restored automatically

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for Selenium)
- Google Chrome WebDriver (automatically managed)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Mukhammad-develop/restaurant-business-directory-scraper.git
cd restaurant-business-directory-scraper
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure settings**
```bash
cp env.example .env
# Edit .env with your API keys and preferences
```

4. **Run your first scrape**
```bash
python main.py --city "New York, NY" --cuisine Italian --min-rating 4.0 --export csv
```

## 📖 Usage Examples

### Basic Scraping
```bash
# Search for Italian restaurants in New York with high ratings
python main.py --city "New York, NY" --cuisine Italian --min-rating 4.0

# Search for pizza places within 15 miles of Los Angeles
python main.py --city "Los Angeles, CA" --keywords pizza --radius 15

# Export to multiple formats with reviews
python main.py --city "Chicago, IL" --export csv,excel,google_sheets --with-reviews
```

### Advanced Filtering
```bash
# High-end restaurants with specific criteria
python main.py \
  --city "San Francisco, CA" \
  --min-rating 4.5 \
  --min-reviews 100 \
  --platforms yelp,google_maps \
  --validate-emails \
  --generate-map \
  --generate-analytics
```

### Scheduled Tasks
```bash
# Add a daily scraping task
python scheduler_cli.py add \
  --id "daily_italian_nyc" \
  --city "New York, NY" \
  --cuisine Italian \
  --frequency daily \
  --time "02:00" \
  --export csv,google_sheets

# Start the scheduler
python scheduler_cli.py start --daemon

# Check scheduler status
python scheduler_cli.py status

# List all tasks
python scheduler_cli.py list
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file based on `env.example`:

```bash
# API Keys (optional but recommended)
YELP_API_KEY=your_yelp_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Google Sheets Integration
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials/google_credentials.json

# Proxy Configuration (optional)
PROXY_HOST=your_proxy_host
PROXY_PORT=your_proxy_port
PROXY_USERNAME=your_proxy_username
PROXY_PASSWORD=your_proxy_password

# Scraping Configuration
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY=2
HEADLESS_BROWSER=true
```

### Configuration File
Customize `config.yaml` for advanced settings:

```yaml
# Scraping Settings
scraping:
  delay_between_requests: 2
  timeout: 30
  max_retries: 3
  concurrent_requests: 5

# Search Parameters
search:
  default_radius: 10
  max_results_per_search: 100
  default_city: "New York, NY"

# Anti-Bot Protection
anti_bot:
  use_proxies: false
  rotate_user_agents: true
  headless_browser: true

# Export Settings
export:
  formats: ["csv", "excel"]
  output_directory: "data/exports"
```

## 📊 Output Examples

### CSV Export
The scraper generates clean, structured CSV files with columns including:
- Business name, address, city, state, zip code
- Phone, website, email (validated)
- Category, cuisine type, price level
- Rating, review count, sentiment scores
- Data sources, scraping metadata

### Interactive Maps
- **Business Locations**: Clickable markers with detailed popups
- **Cuisine Grouping**: Color-coded by cuisine type
- **Clustering**: Automatic marker clustering for dense areas
- **Heatmaps**: Density visualization based on ratings
- **Statistics Panel**: Real-time statistics overlay

### Analytics Dashboard
- **Cuisine Distribution**: Bar charts of popular cuisine types
- **Rating Analysis**: Histograms and statistical summaries
- **Geographic Insights**: City-wise business distribution
- **Sentiment Analysis**: Review sentiment visualization
- **Top Businesses**: Ranked lists of highest-rated establishments

## 🛠️ Advanced Features

### Proxy Management
```python
from src.automation.proxy_manager import proxy_manager

# Test proxies
proxy_manager.test_proxies()

# Get proxy statistics
stats = proxy_manager.get_proxy_stats()
print(f"Working proxies: {stats['working_proxies']}")
```

### Custom Data Processing
```python
from src.processors.data_processor import DataProcessor
from src.models import SearchFilter

processor = DataProcessor()
search_filter = SearchFilter(city="Boston, MA", min_rating=4.0)

# Process with custom filters
processed_data = processor.process_businesses(raw_businesses, search_filter)
```

### Sentiment Analysis
```python
from src.processors.sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()
businesses_with_sentiment = analyzer.analyze_businesses(businesses)

# Get trending sentiments
trends = analyzer.get_trending_sentiments(businesses, top_n=10)
```

## 🔧 API Integration

### Google Sheets Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API and Google Drive API
4. Create service account credentials
5. Download JSON credentials file to `credentials/google_credentials.json`
6. Share your Google Sheet with the service account email

### Yelp API (Optional)
1. Register at [Yelp Developers](https://www.yelp.com/developers)
2. Create an app to get API key
3. Add to your `.env` file as `YELP_API_KEY`

## 📈 Performance & Scalability

- **Concurrent Processing**: Multi-threaded scraping for faster data collection
- **Memory Efficient**: Streaming data processing for large datasets
- **Error Recovery**: Automatic retry mechanisms with exponential backoff
- **Rate Limiting**: Configurable delays to respect website policies
- **Caching**: Intelligent caching to avoid redundant requests

## 🛡️ Legal & Ethical Considerations

- **Robots.txt Compliance**: Respects website scraping policies
- **Rate Limiting**: Built-in delays to avoid overwhelming servers
- **Data Privacy**: No personal data collection beyond public business information
- **Terms of Service**: Users responsible for compliance with platform terms

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check our [Wiki](https://github.com/Mukhammad-develop/restaurant-business-directory-scraper/wiki) for detailed guides
- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/Mukhammad-develop/restaurant-business-directory-scraper/issues)
- **Discussions**: Join our [GitHub Discussions](https://github.com/Mukhammad-develop/restaurant-business-directory-scraper/discussions) for community support

## 🏆 Use Cases

### Marketing Agencies
- **Lead Generation**: Build targeted prospect lists for restaurant marketing
- **Market Research**: Analyze competitor landscapes and market opportunities
- **Client Reporting**: Generate comprehensive market analysis reports

### Restaurant Owners
- **Competitor Analysis**: Monitor competitor ratings, reviews, and offerings
- **Market Positioning**: Understand local market dynamics and pricing
- **Reputation Management**: Track sentiment trends across platforms

### Business Development
- **Partnership Opportunities**: Identify potential business partners and suppliers
- **Market Expansion**: Research new markets before expansion
- **Investment Analysis**: Due diligence for restaurant investments

## 📊 Sample Output

```
🍽️ Restaurant Business Directory Scraper Starting
Configuration loaded from: config.yaml
Search parameters: {'city': 'New York, NY', 'cuisine_type': 'Italian', 'min_rating': 4.0}
Enabled platforms: ['yelp', 'google_maps']

🔍 Starting scraping process...
Starting search on yelp
Found 45 businesses on yelp
Starting search on google_maps  
Found 38 businesses on google_maps
✅ Found 83 businesses total

🔧 Processing and validating data...
After filtering: 71 businesses
After validation: 68 businesses  
After deduplication: 52 businesses
Email validation completed
📊 Data processing completed: 52 valid businesses

💾 Exporting data...
✅ CSV export: data/exports/restaurant_directory_20241215_143022.csv
✅ EXCEL export: data/exports/restaurant_directory_20241215_143022.xlsx

🗺️ Generating interactive map...
✅ Interactive map generated: data/exports/business_map_20241215_143025.html

📊 Generating analytics dashboard...
✅ Analytics dashboard generated: data/exports/analytics_report_20241215_143028.html

✅ Application completed successfully
```

## 🔮 Roadmap

- [ ] **Database Integration**: PostgreSQL/MySQL support for large datasets
- [ ] **Web Interface**: Django/Flask web UI for non-technical users  
- [ ] **API Endpoints**: RESTful API for integration with other systems
- [ ] **Machine Learning**: Predictive analytics for business success
- [ ] **Mobile App**: React Native app for on-the-go data collection
- [ ] **Cloud Deployment**: Docker containerization and cloud deployment guides

---

<div align="center">

**Built with ❤️ for the restaurant and business intelligence community**

[⭐ Star this repo](https://github.com/Mukhammad-develop/restaurant-business-directory-scraper) | [🐛 Report Bug](https://github.com/Mukhammad-develop/restaurant-business-directory-scraper/issues) | [✨ Request Feature](https://github.com/Mukhammad-develop/restaurant-business-directory-scraper/issues)

</div> 