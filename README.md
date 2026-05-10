# Google-Maps-Scrapper
This Python project utilizes the Playwright library to perform web scraping and data extraction from Google Maps, and includes a modern Streamlit web interface. It is particularly designed for obtaining information about businesses, including their name, address, website, phone number, reviews, and extracting emails directly from their websites.

## Multiple Branches
The repo currently has 3 branches
- Main
- Latest Libraries (The one that works with latest libraries, can cause issues. Prefer Main)
- Linux ( Linux Support if main branch does not work correctly)

To do a custom web scraping project you can find me on Upwork

<a href="https://www.upwork.com/freelancers/~01dbb4d47d167c2d43" target="_blank">
<img src=https://img.shields.io/badge/Upwork-6FDA44?&style=for-the-badge&logo=medium&logoColor=white alt=medium style="margin-bottom: 5px;" />
</a>

## Table of Contents
- [Prerequisites](#prerequisites)
- [Key Features](#key-features)
- [Installation](#installation)
- [Usage](#usage)
- [Notes](#notes)
- [Video Example](#video-example)

## Prerequisites
- Python 3.8 or 3.9 (Python 3.10+ may not be compatible with some dependencies)
- Google Chrome or Chromium browser installed (for Playwright)

## Key Features
- **Streamlit Web UI**: An easy-to-use web interface for scraping without using the command line!
- **Data Scraping**: Scrapes data from Google Maps listings, extracting name, address, website, and contact details.
- **Email Extraction**: Automatically visits the scraped websites and extracts associated email addresses!
- **Review Analysis**: Extracts review counts and average ratings.
- **Business Type Detection**: Identifies whether a business offers in-store shopping, in-store pickup, or delivery services.
- **Operating Hours**: Extracts information about the business's operating hours.
- **Introduction Extraction**: Scrapes introductory information about the businesses when available.
- **CSV Export**: The cleaned data can be downloaded as a CSV file directly from the web interface.

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/zohaibbashir/Google-Maps-Scrapper.git
   cd google-maps-scraper
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Usage

Run the Streamlit web application:

```bash
streamlit run app.py
```

The script will launch a web interface in your default browser. From the sidebar, you can enter your **Search Query** (e.g. "Turkish Restaurants in Toronto Canada"), specify the **Total Results to Scrape**, and optionally choose to **Extract Emails from Websites**. Progress will be displayed directly in the UI, and the final results can be downloaded as a CSV file.

## Notes
- The script opens a visible browser window (not headless) for scraping Google Maps data.
- Google Maps DOM may change, which can break the script. If you encounter issues, update the XPaths in `app.py`.
- Avoid running too many scrapes in a short period to prevent being blocked by Google.

## Video Example

https://www.linkedin.com/posts/zohaibbashir_python-data-webscraping-activity-7093920891411062784-flEQ

## License
MIT
