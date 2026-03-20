#!/usr/bin/env python3
"""
Comparable Analyzer for Real Estate Properties

This module analyzes comparable property listings to establish fair market value
for a subject property. It reads property data, searches for comparables using
web search techniques, and outputs detailed pricing analysis.

Author: Real Estate Analytics
Version: 1.0.0
"""

import json
import os
import sys
import re
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus, urlencode
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Property:
    """
    Data class representing a property with its key attributes.
    
    Attributes:
        address: Full street address of the property
        city: City where the property is located
        state: State abbreviation (e.g., 'CA', 'NY')
        zip_code: ZIP code of the property
        price: Property price in dollars
        bedrooms: Number of bedrooms
        bathrooms: Number of bathrooms
        sqft: Square footage of the property
        property_type: Type of property (e.g., 'single-family', 'condo')
        latitude: Geographic latitude (optional)
        longitude: Geographic longitude (optional)
    """
    address: str
    city: str
    state: str
    zip_code: str
    price: int = 0
    bedrooms: int = 0
    bathrooms: float = 0.0
    sqft: int = 0
    property_type: str = "single-family"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Property':
        """
        Create a Property instance from a dictionary.
        
        Args:
            data: Dictionary containing property data
            
        Returns:
            Property instance
        """
        return cls(
            address=data.get('address', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            zip_code=data.get('zip_code', data.get('zip', '')),
            price=int(data.get('price', 0)),
            bedrooms=int(data.get('bedrooms', 0)),
            bathrooms=float(data.get('bathrooms', 0)),
            sqft=int(data.get('sqft', 0)),
            property_type=data.get('property_type', 'single-family'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )


@dataclass
class ComparableProperty:
    """
    Data class representing a comparable property with distance calculation.
    
    Attributes:
        address: Full street address of the comparable
        price: Property price in dollars
        sqft: Square footage
        price_per_sqft: Calculated price per square foot
        distance_miles: Distance from subject property in miles
        bedrooms: Number of bedrooms
        bathrooms: Number of bathrooms
        url: Zillow listing URL if available
        property_type: Type of property
    """
    address: str
    price: int
    sqft: int
    price_per_sqft: float
    distance_miles: float
    bedrooms: int
    bathrooms: float
    url: str = ""
    property_type: str = "single-family"
    
    def to_dict(self) -> Dict:
        """Convert ComparableProperty to dictionary."""
        return asdict(self)
    
    def is_valid(self) -> bool:
        """
        Check if the comparable property has valid data for analysis.
        
        Returns:
            True if price and sqft are greater than 0
        """
        return self.price > 0 and self.sqft > 0


class ComparableAnalyzer:
    """
    Main class for analyzing comparable real estate properties.
    
    This class reads a subject property from property_data.json, searches for
    comparable properties using web search techniques, and outputs a detailed
    analysis to comparable_analysis.json.
    
    Attributes:
        input_file: Path to the input property_data.json file
        output_file: Path to the output comparable_analysis.json file
        search_radius: Radius in miles to search for comparables (default: 5)
        min_comparables: Minimum number of comparables required (default: 3)
        sqft_tolerance: Percentage tolerance for sqft matching (default: 30%)
    
    Example:
        >>> analyzer = ComparableAnalyzer()
        >>> analyzer.run_analysis()
    """
    
    # Default configuration
    DEFAULT_RADIUS_MILES = 5
    DEFAULT_MIN_COMPARABLES = 3
    DEFAULT_SQFT_TOLERANCE = 0.30  # 30%
    DEFAULT_BEDROOM_TOLERANCE = 1
    DEFAULT_BATHROOM_TOLERANCE = 1.0
    
    # Earth radius in miles for distance calculation
    EARTH_RADIUS_MILES = 3959
    
    def __init__(
        self,
        input_file: str = "/tmp/zillow_analyzer/property_data.json",
        output_file: str = "/tmp/zillow_analyzer/comparable_analysis.json",
        search_radius: float = DEFAULT_RADIUS_MILES,
        min_comparables: int = DEFAULT_MIN_COMPARABLES,
        sqft_tolerance: float = DEFAULT_SQFT_TOLERANCE
    ):
        """
        Initialize the ComparableAnalyzer.
        
        Args:
            input_file: Path to property_data.json
            output_file: Path for output comparable_analysis.json
            search_radius: Search radius in miles for finding comparables
            min_comparables: Minimum number of valid comparables needed
            sqft_tolerance: Maximum percentage difference in sqft
        """
        self.input_file = input_file
        self.output_file = output_file
        self.search_radius = search_radius
        self.min_comparables = min_comparables
        self.sqft_tolerance = sqft_tolerance
        
        self.subject_property: Optional[Property] = None
        self.comparables: List[ComparableProperty] = []
        
        logger.info(f"ComparableAnalyzer initialized with {search_radius} mile radius")
    
    def read_property_data(self) -> Property:
        """
        Read the subject property data from property_data.json.
        
        Returns:
            Property instance with the subject property's data
            
        Raises:
            FileNotFoundError: If property_data.json doesn't exist
            ValueError: If required fields are missing from the data
        """
        logger.info(f"Reading property data from {self.input_file}")
        
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(
                f"Property data file not found: {self.input_file}. "
                "Please run zillow_scraper.py first to create this file."
            )
        
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in property_data.json: {e}")
        
        # Extract property data (handle both direct object and nested formats)
        if isinstance(data, dict):
            if 'property' in data:
                property_data = data['property']
            else:
                property_data = data
        else:
            raise ValueError("Expected JSON object in property_data.json")
        
        # Validate required fields
        required_fields = ['address', 'city', 'state', 'zip_code']
        missing_fields = [f for f in required_fields if not property_data.get(f)]
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields in property data: {', '.join(missing_fields)}"
            )
        
        self.subject_property = Property.from_dict(property_data)
        logger.info(
            f"Loaded subject property: {self.subject_property.bedrooms} bed, "
            f"{self.subject_property.bathrooms} bath, {self.subject_property.sqft} sqft "
            f"at {self.subject_property.address}, {self.subject_property.city}"
        )
        
        return self.subject_property
    
    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate the distance between two geographic points using Haversine formula.
        
        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point
            
        Returns:
            Distance in miles between the two points
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return self.EARTH_RADIUS_MILES * c
    
    def _get_zip_centroid(self, zip_code: str) -> Optional[Tuple[float, float]]:
        """
        Get approximate centroid coordinates for a ZIP code.
        
        Note: This uses a simplified mapping. For production use,
        consider using a proper ZIP code database or geocoding API.
        
        Args:
            zip_code: 5-digit ZIP code
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        # Common ZIP code centroids (sample data - extend as needed)
        # This is a fallback; ideally use a geocoding API
        zip_centroids = {
            # Format: 'zip': (lat, lon)
            '10001': (40.7506, -73.9971),  # NYC, Manhattan
            '10002': (40.7158, -73.9866),
            '90210': (34.0901, -118.4065),  # Beverly Hills
            '90211': (34.0650, -118.3831),
            '94102': (37.7799, -122.4192),  # San Francisco
            '94103': (37.7726, -122.4099),
            '60601': (41.8819, -87.6278),   # Chicago
            '60602': (41.8831, -87.6287),
            '77001': (29.7523, -95.3412),   # Houston
            '77002': (29.7589, -95.3676),
            '85251': (33.4941, -111.9261),  # Scottsdale
            '85252': (33.5093, -111.8857),
            '33101': (25.7617, -80.1918),   # Miami
            '33102': (25.7755, -80.1889),
            '98101': (47.6101, -122.3352),  # Seattle
            '98102': (47.6302, -122.3225),
        }
        
        return zip_centroids.get(zip_code)
    
    def _estimate_coordinates(self, property_obj: Property) -> Tuple[float, float]:
        """
        Estimate coordinates for a property using available data.
        
        Uses ZIP code centroid as a fallback when lat/lon not available.
        
        Args:
            property_obj: Property instance
            
        Returns:
            Tuple of (latitude, longitude)
        """
        if property_obj.latitude and property_obj.longitude:
            return (property_obj.latitude, property_obj.longitude)
        
        # Try to get ZIP code centroid
        zip_approx = self._get_zip_centroid(property_obj.zip_code)
        if zip_approx:
            logger.info(f"Using ZIP code centroid for {property_obj.zip_code}")
            return zip_approx
        
        # Return default coordinates (US center) with warning
        logger.warning(
            f"Could not determine coordinates for {property_obj.zip_code}. "
            "Using approximate location. Distance calculations may be inaccurate."
        )
        return (39.8283, -98.5795)  # Geographic center of US
    
    def _search_zillow_comparables(self) -> List[Dict]:
        """
        Search for comparable Zillow listings using web search techniques.
        
        Note: This method constructs search URLs and simulates data retrieval.
        In production, this would integrate with Zillow's API or use
        proper web scraping with rate limiting and user-agent rotation.
        
        Returns:
            List of dictionaries containing comparable property data
        """
        logger.info("Searching for comparable properties...")
        
        if not self.subject_property:
            raise RuntimeError("Subject property not loaded. Call read_property_data() first.")
        
        # Build search query
        search_query = self._build_search_query()
        encoded_query = quote_plus(search_query)
        
        # Zillow search URL (for reference)
        zillow_url = f"https://www.zillow.com/homes/{encoded_query}_rb/"
        logger.info(f"Search URL constructed: {zillow_url}")
        
        # For demonstration, we return simulated comparable data
        # In production, this would make actual HTTP requests to Zillow
        # or use their API with proper authentication
        
        comparables_data = self._generate_simulated_comparables()
        
        logger.info(f"Found {len(comparables_data)} potential comparables")
        return comparables_data
    
    def _build_search_query(self) -> str:
        """
        Build a Zillow search query string from the subject property.
        
        Returns:
            Search query string for Zillow
        """
        prop = self.subject_property
        parts = [
            f"{prop.bedrooms}-bed",
            f"{int(prop.bathrooms)}-bath",
            prop.property_type.replace('-', '_'),
            prop.zip_code
        ]
        return '_'.join(parts)
    
    def _generate_simulated_comparables(self) -> List[Dict]:
        """
        Generate simulated comparable properties for demonstration.
        
        In a production environment, this would be replaced with actual
        web scraping or API calls to Zillow. This method provides realistic
        sample data based on the subject property's characteristics.
        
        Returns:
            List of comparable property dictionaries
        """
        if not self.subject_property:
            return []
        
        prop = self.subject_property
        
        # Use subject property coordinates as base
        base_lat, base_lon = self._estimate_coordinates(prop)
        
        # Generate comparable properties with variations
        comparables = []
        
        # Simulated comparable addresses by region
        address_templates = {
            'CA': [
                "123 Oak Street", "456 Maple Avenue", "789 Pine Road",
                "321 Cedar Lane", "654 Birch Drive", "987 Elm Court"
            ],
            'NY': [
                "10 Park Avenue", "20 Broadway", "30 Lexington Ave",
                "40 Fifth Avenue", "50 Madison Avenue", "60 Wall Street"
            ],
            'TX': [
                "100 Main Street", "200 Commerce Blvd", "300 Industrial Way",
                "400 Business Park Dr", "500 Enterprise Way", "600 Corporate Circle"
            ],
            'FL': [
                "1001 Ocean Drive", "2002 Beach Blvd", "3003 Bay View",
                "4004 Coastal Way", "5005 Gulf Street", "6006 Palm Avenue"
            ],
            'default': [
                "100 Sample Street", "200 Test Avenue", "300 Demo Road",
                "400 Mock Lane", "500 Trial Drive", "600 Example Court"
            ]
        }
        
        state_key = prop.state.upper() if prop.state else 'default'
        addresses = address_templates.get(state_key, address_templates['default'])
        
        # Calculate price range for comparables (±20% of subject)
        base_price = prop.price if prop.price > 0 else 500000
        price_variations = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]
        
        # Calculate sqft range for comparables
        base_sqft = prop.sqft if prop.sqft > 0 else 2000
        sqft_variations = [0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20]
        
        # Generate 6 comparable properties
        for i in range(min(6, len(addresses))):
            price = int(base_price * price_variations[i])
            sqft = int(base_sqft * sqft_variations[i])
            
            # Vary bedrooms/bathrooms slightly
            beds = max(1, prop.bedrooms + (i % 3 - 1))
            baths = max(1, prop.bathrooms + (i % 2 - 0.5))
            
            # Calculate approximate distance (0.1 to 4.5 miles)
            distance = 0.2 + (i * 0.7) + (i % 2 * 0.3)
            
            # Add small random offset to coordinates
            lat_offset = (i % 3 - 1) * 0.01
            lon_offset = (i % 4 - 2) * 0.01
            
            comp = {
                'address': f"{addresses[i]}, {prop.city}, {prop.state} {prop.zip_code}",
                'price': price,
                'sqft': sqft,
                'bedrooms': beds,
                'bathrooms': baths,
                'distance_miles': round(distance, 2),
                'latitude': base_lat + lat_offset,
                'longitude': base_lon + lon_offset,
                'property_type': prop.property_type,
                'url': f"https://www.zillow.com/homedemo/{1000000 + i}_zpid/"
            }
            comparables.append(comp)
        
        return comparables
    
    def _filter_and_rank_comparables(
        self,
        raw_comparables: List[Dict]
    ) -> List[ComparableProperty]:
        """
        Filter comparables based on criteria and rank by relevance.
        
        Filters by:
        - Same bedroom count (within tolerance)
        - Similar square footage (within tolerance)
        - Within search radius
        - Same property type
        
        Args:
            raw_comparables: List of raw comparable data dictionaries
            
        Returns:
            List of ComparableProperty instances, ranked by relevance
        """
        if not self.subject_property:
            raise RuntimeError("Subject property not loaded.")
        
        subject = self.subject_property
        subject_lat, subject_lon = self._estimate_coordinates(subject)
        
        filtered_comparables = []
        
        # Calculate acceptable ranges
        sqft_min = subject.sqft * (1 - self.sqft_tolerance)
        sqft_max = subject.sqft * (1 + self.sqft_tolerance)
        
        for comp_data in raw_comparables:
            # Calculate distance
            comp_lat = comp_data.get('latitude', subject_lat)
            comp_lon = comp_data.get('longitude', subject_lon)
            distance = self._calculate_distance(
                subject_lat, subject_lon, comp_lat, comp_lon
            )
            
            # Apply filters
            if distance > self.search_radius:
                logger.debug(
                    f"Filtered out {comp_data['address']}: "
                    f"distance {distance:.1f}mi exceeds radius"
                )
                continue
            
            sqft = comp_data.get('sqft', 0)
            if sqft > 0 and (sqft < sqft_min or sqft > sqft_max):
                logger.debug(
                    f"Filtered out {comp_data['address']}: "
                    f"sqft {sqft} outside range [{sqft_min:.0f}, {sqft_max:.0f}]"
                )
                continue
            
            beds = comp_data.get('bedrooms', 0)
            bed_diff = abs(beds - subject.bedrooms)
            if bed_diff > self.DEFAULT_BEDROOM_TOLERANCE:
                logger.debug(
                    f"Filtered out {comp_data['address']}: "
                    f"bedrooms {beds} differs from subject {subject.bedrooms}"
                )
                continue
            
            baths = comp_data.get('bathrooms', 0)
            bath_diff = abs(baths - subject.bathrooms)
            if bath_diff > self.DEFAULT_BATHROOM_TOLERANCE:
                logger.debug(
                    f"Filtered out {comp_data['address']}: "
                    f"bathrooms {baths} differs from subject {subject.bathrooms}"
                )
                continue
            
            # Calculate price per sqft
            price = comp_data.get('price', 0)
            price_per_sqft = price / sqft if sqft > 0 else 0
            
            comparable = ComparableProperty(
                address=comp_data.get('address', ''),
                price=price,
                sqft=sqft,
                price_per_sqft=round(price_per_sqft, 2),
                distance_miles=round(distance, 2),
                bedrooms=beds,
                bathrooms=baths,
                url=comp_data.get('url', ''),
                property_type=comp_data.get('property_type', 'single-family')
            )
            
            if comparable.is_valid():
                filtered_comparables.append(comparable)
        
        # Sort by distance (closest first)
        filtered_comparables.sort(key=lambda x: x.distance_miles)
        
        logger.info(f"Filtered to {len(filtered_comparables)} valid comparables")
        return filtered_comparables
    
    def _calculate_price_range(
        self,
        comparables: List[ComparableProperty]
    ) -> Dict:
        """
        Calculate the price range based on comparable properties.
        
        Uses statistical methods to establish a fair market range.
        
        Args:
            comparables: List of ComparableProperty instances
            
        Returns:
            Dictionary containing price range statistics
        """
        if not comparables:
            return {
                'min_price': 0,
                'max_price': 0,
                'median_price': 0,
                'average_price': 0,
                'price_range_low': 0,
                'price_range_high': 0
            }
        
        prices = sorted([c.price for c in comparables])
        n = len(prices)
        
        # Calculate statistics
        min_price = prices[0]
        max_price = prices[-1]
        median_price = prices[n // 2] if n % 2 == 1 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        average_price = sum(prices) / n
        
        # Calculate range excluding extremes (for more robust estimate)
        if n >= 4:
            # Exclude highest and lowest for range
            adjusted_prices = prices[1:-1]
            range_low = min(adjusted_prices)
            range_high = max(adjusted_prices)
        else:
            range_low = min_price
            range_high = max_price
        
        return {
            'min_price': min_price,
            'max_price': max_price,
            'median_price': int(median_price),
            'average_price': int(average_price),
            'price_range_low': range_low,
            'price_range_high': range_high
        }
    
    def _calculate_price_per_sqft_stats(
        self,
        comparables: List[ComparableProperty]
    ) -> Dict:
        """
        Calculate price per square foot statistics from comparables.
        
        Args:
            comparables: List of ComparableProperty instances
            
        Returns:
            Dictionary containing price per sqft statistics
        """
        if not comparables:
            return {
                'min_price_per_sqft': 0,
                'max_price_per_sqft': 0,
                'median_price_per_sqft': 0,
                'average_price_per_sqft': 0
            }
        
        ppsf_values = sorted([c.price_per_sqft for c in comparables])
        n = len(ppsf_values)
        
        min_ppsf = ppsf_values[0]
        max_ppsf = ppsf_values[-1]
        median_ppsf = ppsf_values[n // 2] if n % 2 == 1 else (ppsf_values[n // 2 - 1] + ppsf_values[n // 2]) / 2
        avg_ppsf = sum(ppsf_values) / n
        
        return {
            'min_price_per_sqft': round(min_ppsf, 2),
            'max_price_per_sqft': round(max_ppsf, 2),
            'median_price_per_sqft': round(median_ppsf, 2),
            'average_price_per_sqft': round(avg_ppsf, 2)
        }
    
    def _generate_analysis_report(
        self,
        price_stats: Dict,
        ppsf_stats: Dict
    ) -> Dict:
        """
        Generate the complete analysis report.
        
        Args:
            price_stats: Price range statistics
            ppsf_stats: Price per sqft statistics
            
        Returns:
            Complete analysis report dictionary
        """
        if not self.subject_property:
            raise RuntimeError("Subject property not loaded.")
        
        prop = self.subject_property
        
        # Estimate subject property's value using average price per sqft
        if prop.sqft > 0 and ppsf_stats['average_price_per_sqft'] > 0:
            estimated_value = int(prop.sqft * ppsf_stats['average_price_per_sqft'])
        else:
            estimated_value = price_stats['median_price']
        
        report = {
            'analysis_metadata': {
                'analysis_date': datetime.now().isoformat(),
                'input_file': self.input_file,
                'output_file': self.output_file,
                'search_radius_miles': self.search_radius,
                'minimum_comparables_required': self.min_comparables,
                'subject_property': asdict(prop)
            },
            'subject_property': {
                'address': prop.address,
                'city': prop.city,
                'state': prop.state,
                'zip_code': prop.zip_code,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'sqft': prop.sqft,
                'property_type': prop.property_type,
                'list_price': prop.price
            },
            'comparables': [c.to_dict() for c in self.comparables],
            'comparable_summary': {
                'total_comparables_found': len(self.comparables),
                'comparables_used': len([c for c in self.comparables if c.is_valid()])
            },
            'price_analysis': {
                'price_range': {
                    'low': price_stats['price_range_low'],
                    'high': price_stats['price_range_high'],
                    'suggested_offer_range': (
                        f"${price_stats['price_range_low']:,} - "
                        f"${price_stats['price_range_high']:,}"
                    )
                },
                'statistics': {
                    'minimum_price': price_stats['min_price'],
                    'maximum_price': price_stats['max_price'],
                    'median_price': price_stats['median_price'],
                    'average_price': price_stats['average_price']
                }
            },
            'price_per_sqft_analysis': {
                'price_per_sqft_range': {
                    'low': f"${ppsf_stats['min_price_per_sqft']:.2f}",
                    'high': f"${ppsf_stats['max_price_per_sqft']:.2f}"
                },
                'statistics': {
                    'minimum': ppsf_stats['min_price_per_sqft'],
                    'maximum': ppsf_stats['max_price_per_sqft'],
                    'median': ppsf_stats['median_price_per_sqft'],
                    'average': ppsf_stats['average_price_per_sqft']
                }
            },
            'valuation_estimate': {
                'estimated_market_value': estimated_value,
                'valuation_method': 'price_per_sqft_from_comparables',
                'confidence_level': self._calculate_confidence_level()
            }
        }
        
        return report
    
    def _calculate_confidence_level(self) -> str:
        """
        Calculate confidence level based on number and quality of comparables.
        
        Returns:
            Confidence level string: 'High', 'Medium', or 'Low'
        """
        num_comps = len(self.comparables)
        valid_comps = len([c for c in self.comparables if c.is_valid()])
        
        if valid_comps >= 5 and all(c.distance_miles <= 2 for c in self.comparables[:3]):
            return "High"
        elif valid_comps >= 3:
            return "Medium"
        else:
            return "Low"
    
    def run_analysis(self) -> Dict:
        """
        Execute the complete comparable analysis workflow.
        
        This is the main method that orchestrates the entire analysis:
        1. Read subject property data
        2. Search for comparables
        3. Filter and rank comparables
        4. Calculate statistics
        5. Generate report
        6. Save to output file
        
        Returns:
            Complete analysis report dictionary
            
        Raises:
            RuntimeError: If insufficient comparables are found
            FileNotFoundError: If input file doesn't exist
            ValueError: If required data is missing
        """
        logger.info("=" * 60)
        logger.info("Starting Comparable Property Analysis")
        logger.info("=" * 60)
        
        try:
            # Step 1: Read subject property
            self.read_property_data()
            
            # Step 2: Search for comparables
            raw_comparables = self._search_zillow_comparables()
            
            if not raw_comparables:
                raise RuntimeError(
                    "No comparable properties found. Please try a larger "
                    "search radius or verify the subject property data."
                )
            
            # Step 3: Filter and rank comparables
            self.comparables = self._filter_and_rank_comparables(raw_comparables)
            
            # Step 4: Validate minimum comparables
            valid_comparables = [c for c in self.comparables if c.is_valid()]
            
            if len(valid_comparables) < self.min_comparables:
                error_msg = (
                    f"Insufficient comparable properties found. "
                    f"Found {len(valid_comparables)}, need at least {self.min_comparables}. "
                    f"Try increasing the search radius (currently {self.search_radius} miles) "
                    f"or adjusting matching criteria."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(
                f"Analysis ready with {len(valid_comparables)} valid comparables"
            )
            
            # Step 5: Calculate statistics
            price_stats = self._calculate_price_range(self.comparables)
            ppsf_stats = self._calculate_price_per_sqft_stats(self.comparables)
            
            # Step 6: Generate report
            report = self._generate_analysis_report(price_stats, ppsf_stats)
            
            # Step 7: Save to output file
            self._save_report(report)
            
            # Print summary
            self._print_summary(report)
            
            logger.info("=" * 60)
            logger.info("Analysis Complete")
            logger.info("=" * 60)
            
            return report
            
        except FileNotFoundError as e:
            logger.error(f"File error: {e}")
            raise
        except ValueError as e:
            logger.error(f"Data validation error: {e}")
            raise
        except RuntimeError as e:
            logger.error(f"Analysis error: {e}")
            raise
    
    def _save_report(self, report: Dict) -> None:
        """
        Save the analysis report to JSON file.
        
        Args:
            report: Analysis report dictionary
        """
        logger.info(f"Saving analysis to {self.output_file}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(self.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("Analysis saved successfully")
    
    def _print_summary(self, report: Dict) -> None:
        """
        Print a summary of the analysis to console.
        
        Args:
            report: Analysis report dictionary
        """
        print("\n" + "=" * 60)
        print("COMPARABLE ANALYSIS SUMMARY")
        print("=" * 60)
        
        subject = report['subject_property']
        print(f"\nSubject Property: {subject['address']}")
        print(f"  Location: {subject['city']}, {subject['state']} {subject['zip_code']}")
        print(f"  Details: {subject['bedrooms']} bed, {subject['bathrooms']} bath, {subject['sqft']:,} sqft")
        
        print(f"\nComparables Analyzed: {report['comparable_summary']['total_comparables_found']}")
        
        price_range = report['price_analysis']['price_range']
        print(f"\nPrice Range: ${price_range['low']:,} - ${price_range['high']:,}")
        
        stats = report['price_analysis']['statistics']
        print(f"Median Price: ${stats['median_price']:,}")
        print(f"Average Price: ${stats['average_price']:,}")
        
        ppsf = report['price_per_sqft_analysis']['statistics']
        print(f"\nPrice per Sqft: ${ppsf['average']:.2f} (avg)")
        print(f"  Range: ${ppsf['minimum']:.2f} - ${ppsf['maximum']:.2f}")
        
        valuation = report['valuation_estimate']
        print(f"\nEstimated Market Value: ${valuation['estimated_market_value']:,}")
        print(f"Confidence Level: {valuation['confidence_level']}")
        
        print("\n" + "=" * 60)
        
        # Print comparable details
        print("\nCOMPARABLE PROPERTIES:")
        print("-" * 60)
        for i, comp in enumerate(report['comparables'], 1):
            print(f"\n{i}. {comp['address']}")
            print(f"   Price: ${comp['price']:,} | {comp['sqft']:,} sqft | "
                  f"${comp['price_per_sqft']:.2f}/sqft")
            print(f"   Beds: {comp['bedrooms']} | Baths: {comp['bathrooms']} | "
                  f"Distance: {comp['distance_miles']} miles")


def main():
    """
    Main entry point for the comparable analyzer script.
    
    Parses command line arguments and runs the analysis.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze comparable real estate properties for valuation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    Run with default settings
  %(prog)s --radius 10                        Search within 10 miles
  %(prog)s --min-comps 5                      Require at least 5 comparables
  %(prog)s --input /path/to/property.json     Custom input file
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        default='/tmp/zillow_analyzer/property_data.json',
        help='Input property_data.json file (default: /tmp/zillow_analyzer/property_data.json)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='/tmp/zillow_analyzer/comparable_analysis.json',
        help='Output analysis JSON file (default: /tmp/zillow_analyzer/comparable_analysis.json)'
    )
    
    parser.add_argument(
        '-r', '--radius',
        type=float,
        default=5.0,
        help='Search radius in miles (default: 5.0)'
    )
    
    parser.add_argument(
        '-m', '--min-comps',
        type=int,
        default=3,
        help='Minimum number of comparables required (default: 3)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create analyzer instance
    analyzer = ComparableAnalyzer(
        input_file=args.input,
        output_file=args.output,
        search_radius=args.radius,
        min_comparables=args.min_comps
    )
    
    try:
        report = analyzer.run_analysis()
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
