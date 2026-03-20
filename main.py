#!/usr/bin/env python3
"""
Zillow Property Analyzer
=========================
A multi-stage pipeline that scrapes a Zillow listing, finds comparable properties,
generates an appraisal estimate, and recommends value-adding upgrades.

Usage:
    python3 main.py

The program will prompt for a Zillow property URL and run all three stages automatically.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zillow_scraper import ZillowScraper
from comparable_analyzer import ComparableAnalyzer
from appraisal_engine import AppraisalEngine


def main():
    print("=" * 60)
    print("  Zillow Property Analyzer")
    print("  Appraisal + Comparable Analysis + Upgrade Recommendations")
    print("=" * 60)
    print()

    # Stage 1: Scrape the property
    print("[Stage 1/3] Scraping Zillow listing...")
    print("-" * 40)
    scraper = ZillowScraper()
    url = input("Paste a Zillow property URL: ").strip()
    if not url:
        print("No URL provided. Exiting.")
        return
    try:
        property_data = scraper.run(url)
        print(f"  Saved property data to property_data.json")
    except Exception as e:
        print(f"  Error: {e}")
        return
    print()

    # Stage 2: Find comparables
    print("[Stage 2/3] Analyzing comparable properties...")
    print("-" * 40)
    analyzer = ComparableAnalyzer()
    try:
        comp_data = analyzer.run()
        print(f"  Found {len(comp_data.get('comparables', []))} comparable properties")
        print(f"  Saved analysis to comparable_analysis.json")
    except Exception as e:
        print(f"  Error: {e}")
        return
    print()

    # Stage 3: Generate appraisal + upgrades
    print("[Stage 3/3] Generating appraisal and upgrade recommendations...")
    print("-" * 40)
    engine = AppraisalEngine()
    try:
        report = engine.generate_report()
        print("  Appraisal Report")
        print("  " + "-" * 38)
        print(report)
        print(f"\n  Full report saved to appraisal_report.txt")
    except Exception as e:
        print(f"  Error: {e}")
        return

    print()
    print("=" * 60)
    print("  Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
