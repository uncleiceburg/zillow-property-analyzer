#!/usr/bin/env python3
"""
Zillow Property Scraper

A web scraper for extracting property details from Zillow listings.
Uses requests and BeautifulSoup to fetch and parse Zillow property pages.

NOTE: This script is for educational purposes. Scraping Zillow may violate
their Terms of Service. Use responsibly and at your own risk.

Usage:
    python zillow_scraper.py

Requirements:
    pip install requests beautifulsoup4
"""

import json
import re
import sys
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class ZillowScraper:
    """
    A class to scrape property details from Zillow listing pages.
    
    Attributes:
        base_url: The base URL for Zillow.
        headers: HTTP headers to mimic a browser request.
        session: Requests session for making HTTP requests.
    """
    
    # Browser headers to mimic a real user request
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        """
        Initialize the ZillowScraper.
        
        Args:
            headers: Optional custom HTTP headers. If not provided, uses DEFAULT_HEADERS.
        """
        self.base_url = 'https://www.zillow.com'
        self.headers = headers or self.DEFAULT_HEADERS.copy()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.property_data: Dict[str, Any] = {}
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if the provided URL is a valid Zillow property URL.
        
        Args:
            url: The URL to validate.
            
        Returns:
            True if valid Zillow property URL, False otherwise.
        """
        try:
            parsed = urlparse(url)
            # Check if it's a zillow.com domain and appears to be a property URL
            if parsed.netloc and 'zillow.com' in parsed.netloc:
                # Accept various Zillow URL patterns for property listings
                patterns = [
                    r'/homedetails/.*',
                    r'/b/.*',
                    r'/multifamily/.*',
                    r'/condo/.*',
                    r'/townhouse/.*',
                    r'/for_sale/.*',
                ]
                for pattern in patterns:
                    if re.search(pattern, parsed.path, re.IGNORECASE):
                        return True
                # Also accept URLs with zpid parameter (older Zillow format)
                if 'zpid' in url:
                    return True
            return False
        except Exception:
            return False
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch the HTML content from a Zillow property page.
        
        Args:
            url: The URL of the property page to fetch.
            
        Returns:
            The HTML content as a string, or None if fetching failed.
            
        Raises:
            ValueError: If the URL is invalid.
            requests.RequestException: If the HTTP request fails.
        """
        if not self.validate_url(url):
            raise ValueError(f"Invalid Zillow property URL: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            raise requests.RequestException("Request timed out. Please check your connection.")
        except requests.exceptions.ConnectionError:
            raise requests.RequestException("Connection error. Please check your internet connection.")
        except requests.exceptions.HTTPError as e:
            raise requests.RequestException(f"HTTP error: {e}")
        except requests.RequestException as e:
            raise requests.RequestException(f"Request failed: {e}")
    
    def parse_price(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the property price from the page.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            The price as a string, or None if not found.
        """
        # Try multiple selectors for price
        price_selectors = [
            'span[data-testid="price"]',
            'span.ManualPrice__ManualPriceSpan-sc-1mgelww-0',
            'div.price-section span',
            '.price-badge span',
            'h2[data-testid="price"]',
        ]
        
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        # Fallback: look for any element containing a price pattern
        price_pattern = re.compile(r'\$[\d,]+')
        for element in soup.find_all(text=price_pattern):
            parent = element.parent
            if parent and '$' in parent.get_text():
                return parent.get_text(strip=True)
        
        return None
    
    def parse_address(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the property address from the page.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            The address as a string, or None if not found.
        """
        # Try multiple selectors for address
        address_selectors = [
            'h1[data-testid="address"]',
            'address[data-testid="address"]',
            'div.building-address span',
            'h1.override-zps-address',
            '.zsg-content_hcomponent h1',
            'h2[data-testid="street-address"]',
        ]
        
        for selector in address_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        # Fallback: look for address in meta tags
        meta_address = soup.find('meta', property='og:title')
        if meta_address and meta_address.get('content'):
            return meta_address['content'].split('|')[0].strip()
        
        return None
    
    def parse_beds_baths_sqft(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract bed, bath, and square footage information.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            Dictionary with 'beds', 'baths', and 'sqft' keys.
        """
        result = {'beds': None, 'baths': None, 'sqft': None}
        
        # Look for the facts section
        facts_selectors = [
            'div[data-testid="home-details-stats"]',
            'div.overview-content',
            'div.home-details-chip',
        ]
        
        facts_text = ''
        for selector in facts_selectors:
            element = soup.select_one(selector)
            if element:
                facts_text = element.get_text(strip=True)
                break
        
        if not facts_text:
            # Try to get text from entire page and search for patterns
            facts_text = soup.get_text()
        
        # Parse beds
        beds_patterns = [
            r'(\d+)\s*(?:bed|bedroom|bd|bdr)',
            r'(\d+)\s+(?:bed|bedroom)',
        ]
        for pattern in beds_patterns:
            match = re.search(pattern, facts_text, re.IGNORECASE)
            if match:
                result['beds'] = match.group(1)
                break
        
        # Parse baths
        baths_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom|ba|bd)',
            r'(\d+(?:\.\d+)?)\s+(?:bath|bathroom)',
        ]
        for pattern in baths_patterns:
            match = re.search(pattern, facts_text, re.IGNORECASE)
            if match:
                result['baths'] = match.group(1)
                break
        
        # Parse sqft
        sqft_patterns = [
            r'([\d,]+)\s*(?:sqft|square\s*feet|sq\s*ft)',
            r'([\d,]+)\s+sq\s*ft',
        ]
        for pattern in sqft_patterns:
            match = re.search(pattern, facts_text, re.IGNORECASE)
            if match:
                result['sqft'] = match.group(1).replace(',', '')
                break
        
        return result
    
    def parse_lot_size(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the lot size from the page.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            The lot size as a string, or None if not found.
        """
        lot_patterns = [
            r'([\d,]+)\s*(?:acre|acres|ac)',
            r'Lot:\s*([\d,]+)\s*(?:sqft|acre)',
        ]
        
        page_text = soup.get_text()
        
        for pattern in lot_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # Try looking in specific elements
        lot_selectors = [
            'span[data-testid="lot-size"]',
            'li.lot-size',
        ]
        
        for selector in lot_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def parse_year_built(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the year built from the page.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            The year as a string, or None if not found.
        """
        year_patterns = [
            r'Built\s*(?:in)?\s*(\d{4})',
            r'Year\s*(?:Built)?:\s*(\d{4})',
            r'(\d{4})\s*(?:year|built)',
        ]
        
        page_text = soup.get_text()
        
        for pattern in year_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                year = match.group(1)
                # Validate year is reasonable (1800-2030)
                if 1800 <= int(year) <= 2030:
                    return year
        
        return None
    
    def parse_property_type(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the property type from the page.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            The property type as a string, or None if not found.
        """
        type_patterns = [
            r'(Single\s*Family)',
            r'(Multi[- ]*Family)',
            r'(Condo)',
            r'(Townhouse)',
            r'(Townhome)',
            r'(Apartment)',
            r'(Studio)',
            r'(Lot|Land)',
            r'(Manufactured)',
            r'(Co[- ]?op)',
        ]
        
        page_text = soup.get_text()
        
        for pattern in type_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Try specific selectors
        type_selectors = [
            'span[data-testid="property-type"]',
            'div.property-type',
            'span.property-type-badge',
        ]
        
        for selector in type_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        return None
    
    def parse_mls_number(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the MLS number from the page if visible.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            The MLS number as a string, or None if not found.
        """
        mls_patterns = [
            r'(?:MLS\s*#?|MLS#|Listing\s*#):\s*([A-Z0-9-]+)',
            r'(?:MLS\s*ID|MLS\s*Number):\s*([A-Z0-9-]+)',
            r'(?<!L) MLS #:?\s*([A-Z0-9-]+)',
        ]
        
        page_text = soup.get_text()
        
        for pattern in mls_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def parse_description(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the listing description from the page.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            The description as a string, or None if not found.
        """
        # Try meta description first
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Try specific selectors for description
        desc_selectors = [
            'div[data-testid="description"]',
            'div.notes-container',
            'div.property-description',
            'section.description-section',
            'div.zsg-lg-16',
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 20:  # Filter out very short text
                    return text
        
        return None
    
    def parse_features_amenities(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract listed features and amenities from the page.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            List of feature/amenity strings.
        """
        features = []
        
        # Common feature selectors
        feature_selectors = [
            'ul.features li',
            'div.amenities li',
            'ul[data-testid="amenities"] li',
            'div.amenities-container li',
        ]
        
        for selector in feature_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and text not in features:
                    features.append(text)
        
        # Also look for specific common amenities in text
        common_amenities = [
            'Pool', 'Garage', 'Parking', 'Fireplace', 'Central Air',
            'Heating', 'Washer', 'Dryer', 'Dishwasher', 'Refrigerator',
            'Microwave', 'Hardwood Floors', 'Carpet', 'Tile', 'Balcony',
            'Patio', 'Garden', 'Fenced Yard', 'Security System',
            'Smart Home', 'Solar Panels', 'EV Charging', 'Gym',
            'Doorman', 'Laundry', 'Storage', 'Basement', 'Attic',
        ]
        
        page_text = soup.get_text()
        for amenity in common_amenities:
            if amenity.lower() in page_text.lower():
                if amenity not in features:
                    features.append(amenity)
        
        return features
    
    def parse_property_data(self, html: str) -> Dict[str, Any]:
        """
        Parse all property data from the HTML content.
        
        Args:
            html: The HTML content as a string.
            
        Returns:
            Dictionary containing all extracted property data.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        self.property_data = {
            'address': self.parse_address(soup),
            'price': self.parse_price(soup),
            'beds': self.parse_beds_baths_sqft(soup).get('beds'),
            'baths': self.parse_beds_baths_sqft(soup).get('baths'),
            'sqft': self.parse_beds_baths_sqft(soup).get('sqft'),
            'lot_size': self.parse_lot_size(soup),
            'year_built': self.parse_year_built(soup),
            'property_type': self.parse_property_type(soup),
            'mls_number': self.parse_mls_number(soup),
            'description': self.parse_description(soup),
            'features': self.parse_features_amenities(soup),
        }
        
        return self.property_data
    
    def save_to_json(self, filename: str = 'property_data.json') -> bool:
        """
        Save the property data to a JSON file.
        
        Args:
            filename: The name of the JSON file to save to.
            
        Returns:
            True if saved successfully, False otherwise.
        """
        if not self.property_data:
            print("No property data to save.")
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.property_data, f, indent=2, ensure_ascii=False)
            print(f"Property data saved to {filename}")
            return True
        except IOError as e:
            print(f"Error saving to JSON: {e}")
            return False
    
    def scrape(self, url: str, save_json: bool = True) -> Dict[str, Any]:
        """
        Main method to scrape a Zillow property page.
        
        Args:
            url: The URL of the Zillow property page to scrape.
            save_json: Whether to save the data to a JSON file.
            
        Returns:
            Dictionary containing the scraped property data.
            
        Raises:
            ValueError: If the URL is invalid.
            requests.RequestException: If the HTTP request fails.
        """
        print(f"Scraping property data from:\n{url}\n")
        
        # Fetch the page
        html = self.fetch_page(url)
        
        if not html:
            raise ValueError("Failed to fetch page content")
        
        # Parse the data
        print("Parsing property details...")
        property_data = self.parse_property_data(html)
        
        # Save to JSON if requested
        if save_json:
            self.save_to_json()
        
        return property_data
    
    def display_results(self, data: Dict[str, Any]) -> None:
        """
        Display the scraped property data in a readable format.
        
        Args:
            data: The property data dictionary.
        """
        print("\n" + "=" * 50)
        print("SCRAPED PROPERTY DATA")
        print("=" * 50)
        
        for key, value in data.items():
            if key == 'features' and isinstance(value, list):
                print(f"\n{key.replace('_', ' ').title()}:")
                for feature in value:
                    print(f"  - {feature}")
            elif value:
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        print("=" * 50)


def get_user_input() -> str:
    """
    Prompt the user to paste a Zillow URL.
    
    Returns:
        The URL entered by the user.
    """
    print("\n" + "-" * 50)
    print("ZILLOW PROPERTY SCRAPER")
    print("-" * 50)
    print("\nEnter a Zillow property URL to scrape.")
    print("Example: https://www.zillow.com/homedetails/...")
    print("\nPaste URL (or press Enter to use example URL):")
    
    url = input("\n> ").strip()
    
    # Use a demo URL if user enters nothing
    if not url:
        url = "https://www.zillow.com/homedetails/123456789.html"
        print(f"Using example URL: {url}")
    
    return url


def main():
    """
    Main entry point for the Zillow scraper script.
    """
    try:
        # Get URL from user
        url = get_user_input()
        
        # Initialize scraper
        scraper = ZillowScraper()
        
        # Scrape the property
        property_data = scraper.scrape(url)
        
        # Display results
        scraper.display_results(property_data)
        
        print("\nScraping completed successfully!")
        return 0
        
    except ValueError as e:
        print(f"\nError: {e}")
        print("Please provide a valid Zillow property URL.")
        return 1
    except requests.RequestException as e:
        print(f"\nNetwork Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\nScraping cancelled by user.")
        return 130
    except Exception as e:
        print(f"\nUnexpected Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
