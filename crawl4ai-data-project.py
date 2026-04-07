"""
Cấu trúc thư mục project:
- .env
- requirements.txt
- main.py
- crawler/
  - __init__.py
  - crawler.py
  - utils.py
- data/
  - raw/
  - processed/
"""

# Nội dung file .env
```
# API Keys
CRAWL4AI_API_KEY=your_api_key_here
CRAWL4AI_SECRET=your_secret_here

# Cấu hình Crawler
MAX_PAGES=100
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT=30
CRAWL_DELAY=2

# Đường dẫn lưu dữ liệu
RAW_DATA_PATH=./data/raw
PROCESSED_DATA_PATH=./data/processed

# Cấu hình Database (nếu cần)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crawl_db
DB_USER=postgres
DB_PASSWORD=password
```

# Nội dung file requirements.txt
```
python-dotenv==1.0.0
requests==2.31.0
beautifulsoup4==4.12.2
pandas==2.1.0
numpy==1.26.0
crawl4ai==1.0.0  # Giả định tên package
SQLAlchemy==2.0.20  # Nếu cần lưu dữ liệu vào database
tqdm==4.66.1
```

# Nội dung file main.py
```python
import os
import argparse
from dotenv import load_dotenv
from crawler.crawler import Crawl4AIDataCrawler
from crawler.utils import setup_logging

# Load biến môi trường từ file .env
load_dotenv()

def main():
    # Thiết lập logging
    logger = setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Crawl data using Crawl4AI')
    parser.add_argument('--url', type=str, required=True, help='URL to start crawling')
    parser.add_argument('--output', type=str, default=os.environ.get('RAW_DATA_PATH'), 
                        help='Path to save raw data')
    parser.add_argument('--max_pages', type=int, default=int(os.environ.get('MAX_PAGES', 100)), 
                        help='Maximum number of pages to crawl')
    args = parser.parse_args()
    
    # Initialize crawler
    crawler = Crawl4AIDataCrawler(
        api_key=os.environ.get('CRAWL4AI_API_KEY'),
        api_secret=os.environ.get('CRAWL4AI_SECRET'),
        user_agent=os.environ.get('USER_AGENT'),
        timeout=int(os.environ.get('REQUEST_TIMEOUT')),
        delay=float(os.environ.get('CRAWL_DELAY'))
    )
    
    # Start crawling
    logger.info(f"Starting crawl from URL: {args.url}")
    crawler.crawl(args.url, args.output, args.max_pages)
    logger.info("Crawling completed!")
    
    # Process data
    crawler.process_data(
        input_path=args.output,
        output_path=os.environ.get('PROCESSED_DATA_PATH')
    )
    logger.info("Data processing completed!")

if __name__ == "__main__":
    main()
```

# Nội dung file crawler/__init__.py
```python
# Crawler package
```

# Nội dung file crawler/crawler.py
```python
import os
import json
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import logging

class Crawl4AIDataCrawler:
    """
    Crawler sử dụng Crawl4AI API để thu thập dữ liệu
    """
    
    def __init__(self, api_key, api_secret, user_agent=None, timeout=30, delay=2):
        """
        Khởi tạo crawler
        
        Parameters:
        - api_key: Crawl4AI API key
        - api_secret: Crawl4AI API secret
        - user_agent: User agent string to use in requests
        - timeout: Request timeout in seconds
        - delay: Delay between requests in seconds
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.user_agent = user_agent
        self.timeout = timeout
        self.delay = delay
        self.logger = logging.getLogger(__name__)
        
        # Validate API credentials
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required")
            
        # Headers for requests
        self.headers = {
            'User-Agent': self.user_agent,
            'X-API-Key': self.api_key,
            'X-API-Secret': self.api_secret
        }
        
    def _make_request(self, url):
        """Make a request to the given URL with delay"""
        try:
            time.sleep(self.delay)  # Respect crawl delay
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error requesting {url}: {e}")
            return None
    
    def _extract_links(self, html, base_url):
        """Extract links from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            # Handle relative URLs
            if href.startswith('/'):
                href = f"{base_url.rstrip('/')}{href}"
            # Only include links from the same domain
            if href.startswith(base_url):
                links.append(href)
                
        return list(set(links))  # Remove duplicates
    
    def _extract_data(self, html, url):
        """
        Extract relevant data from HTML
        Override this method in subclasses to customize extraction logic
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Default extraction: title, description and text content
        title = soup.title.string if soup.title else ""
        
        # Get meta description
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content')
        
        # Get main text content
        paragraphs = soup.find_all('p')
        text_content = "\n".join([p.get_text().strip() for p in paragraphs])
        
        return {
            "url": url,
            "title": title,
            "description": description,
            "content": text_content,
            "timestamp": time.time()
        }
        
    def crawl(self, start_url, output_path, max_pages=100):
        """
        Crawl pages starting from the given URL
        
        Parameters:
        - start_url: URL to start crawling from
        - output_path: Path to save raw data
        - max_pages: Maximum number of pages to crawl
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Initialize crawl queue and visited set
        queue = [start_url]
        visited = set()
        crawled_data = []
        
        self.logger.info(f"Starting crawl from {start_url}, max pages: {max_pages}")
        
        with tqdm(total=max_pages, desc="Crawling") as pbar:
            while queue and len(visited) < max_pages:
                url = queue.pop(0)
                
                if url in visited:
                    continue
                    
                self.logger.debug(f"Crawling: {url}")
                response = self._make_request(url)
                
                if not response:
                    continue
                    
                visited.add(url)
                
                try:
                    # Extract data
                    data = self._extract_data(response.text, url)
                    crawled_data.append(data)
                    
                    # Extract links for BFS crawling
                    links = self._extract_links(response.text, start_url)
                    for link in links:
                        if link not in visited and link not in queue:
                            queue.append(link)
                            
                    # Update progress bar
                    pbar.update(1)
                    
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {e}")
        
        # Save crawled data
        timestamp = int(time.time())
        output_file = os.path.join(output_path, f"crawled_data_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(crawled_data, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"Saved {len(crawled_data)} crawled pages to {output_file}")
        return output_file
    
    def process_data(self, input_path, output_path):
        """
        Process raw data and convert to structured format
        
        Parameters:
        - input_path: Path to raw data directory or file
        - output_path: Path to save processed data
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Determine if input is a file or directory
        if os.path.isfile(input_path):
            files = [input_path]
        else:
            files = [os.path.join(input_path, f) for f in os.listdir(input_path) 
                    if f.endswith('.json')]
        
        all_data = []
        
        # Process each file
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                all_data.extend(data)
            except Exception as e:
                self.logger.error(f"Error processing file {file_path}: {e}")
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(all_data)
        
        # Basic cleaning and processing
        if not df.empty:
            # Remove duplicates
            df.drop_duplicates(subset=['url'], inplace=True)
            
            # Clean text content (example)
            if 'content' in df.columns:
                df['content'] = df['content'].str.replace('\s+', ' ', regex=True)
            
            # Save processed data
            timestamp = int(time.time())
            csv_file = os.path.join(output_path, f"processed_data_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding='utf-8')
            
            # Save as JSON as well
            json_file = os.path.join(output_path, f"processed_data_{timestamp}.json")
            df.to_json(json_file, orient='records', force_ascii=False, indent=2)
            
            self.logger.info(f"Saved {len(df)} processed records")
            return csv_file
        else:
            self.logger.warning("No data to process")
            return None
```

# Nội dung file crawler/utils.py
```python
import os
import logging
import json
from datetime import datetime

def setup_logging(log_file=None, level=logging.INFO):
    """
    Set up logging configuration
    
    Parameters:
    - log_file: Path to log file (optional)
    - level: Logging level
    
    Returns:
    - logger: Configured logger
    """
    # Create logs directory if log_file is specified
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    else:
        # Default log file
        if not os.path.exists('logs'):
            os.makedirs('logs', exist_ok=True)
        log_file = f"logs/crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger

def save_to_json(data, output_path):
    """
    Save data to JSON file
    
    Parameters:
    - data: Data to save
    - output_path: Path to save JSON file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
def load_from_json(input_path):
    """
    Load data from JSON file
    
    Parameters:
    - input_path: Path to JSON file
    
    Returns:
    - data: Loaded data
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def extract_domain(url):
    """Extract domain from URL"""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    return parsed_url.netloc
```
