import time
import urllib.robotparser
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from typing import Dict, Any, Optional
import re

from src.config import settings
from src.utils.logger import logger

class WebScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.robot_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.last_scrape_time = 0.0

    def _can_fetch(self, url: str) -> bool:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if base_url not in self.robot_parsers:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{base_url}/robots.txt")
            try:
                rp.read()
            except Exception as e:
                logger.debug(f"Could not read robots.txt for {base_url}: {e}")
                # Assume allowed if we can't fetch robots.txt
            self.robot_parsers[base_url] = rp
            
        rp = self.robot_parsers[base_url]
        try:
            return rp.can_fetch(self.headers["User-Agent"], url)
        except Exception:
            return True

    def _clean_soup(self, soup: BeautifulSoup):
        # Remove common non-content elements
        for tag in soup.find_all(['nav', 'header', 'footer', 'script', 'style', 'noscript', 'iframe', 'aside']):
            tag.decompose()
        # Remove ads or comments
        for class_name in ['ad', 'ads', 'comments', 'related', 'sidebar', 'newsletter', 'share', 'social']:
            for tag in soup.find_all(class_=lambda c: c and class_name in c.lower()):
                tag.decompose()

    def _parse_theken(self, soup: BeautifulSoup) -> str:
        # The Ken content (might be paywalled, we extract what is visible)
        article = soup.find('article') or soup.find(class_='article-content') or soup.find('main')
        if article:
            return str(article)
        return ""

    def _parse_inc42(self, soup: BeautifulSoup) -> str:
        article = soup.find('article') or soup.find(id='content') or soup.find(class_=lambda c: c and 'article' in c.lower())
        if article:
            return str(article)
        return ""

    def _parse_morningcontext(self, soup: BeautifulSoup) -> str:
        article = soup.find(class_='story-content') or soup.find('article') or soup.find('main')
        if article:
            return str(article)
        return ""

    def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        # 6. Respect robots.txt
        if not self._can_fetch(url):
            logger.warning(f"Scraping disallowed by robots.txt for URL: {url}")
            return None

        # 7. Rate limiting using configured delay
        time_since_last = time.time() - self.last_scrape_time
        delay = getattr(settings, 'scrape_delay_seconds', 2.0)
        if time_since_last < delay:
            time.sleep(delay - time_since_last)

        try:
            logger.info(f"Scraping URL: {url}")
            response = httpx.get(url, headers=self.headers, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
            self.last_scrape_time = time.time()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 3. Extract metadata
            title = ""
            if soup.title:
                title = soup.title.string.strip()
            elif soup.find('h1'):
                title = soup.find('h1').get_text(strip=True)
                
            author = ""
            author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
            if author_meta:
                author = author_meta.get('content', '')
            else:
                author_tag = soup.find(class_=lambda c: c and 'author' in c.lower())
                if author_tag:
                    author = author_tag.get_text(strip=True)

            date = ""
            date_meta = soup.find('meta', {'property': 'article:published_time'})
            if date_meta:
                date = date_meta.get('content', '')
            else:
                date_tag = soup.find('time')
                if date_tag:
                    date = date_tag.get('datetime', '') or date_tag.get_text(strip=True)

            # 4. Remove clutter
            self._clean_soup(soup)

            # 8. Site specific handling
            html_content = ""
            domain = urlparse(url).netloc.lower()
            if 'theken.co' in domain or 'the-ken.com' in domain:
                html_content = self._parse_theken(soup)
            elif 'inc42.com' in domain:
                html_content = self._parse_inc42(soup)
            elif 'themorningcontext.com' in domain or 'themorningcontext.in' in domain:
                html_content = self._parse_morningcontext(soup)
                
            # Fallback
            if not html_content:
                main_tag = soup.find('main') or soup.find('article') or soup.find('body')
                if main_tag:
                    html_content = str(main_tag)

            if not html_content:
                logger.warning(f"Could not extract main content for {url}")
                return None

            # 5. Convert to clean markdown
            md_content = md(html_content, heading_style="ATX").strip()
            md_content = re.sub(r'\n{3,}', '\n\n', md_content)

            word_count = len(md_content.split())

            return {
                "url": url,
                "title": title,
                "author": author,
                "date": date[:10] if date else "", # Standardize YYYY-MM-DD
                "content": md_content,
                "word_count": word_count
            }

        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None
