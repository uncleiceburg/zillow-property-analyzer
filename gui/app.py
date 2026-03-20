#!/usr/bin/env python3
"""
Flask GUI for Zillow Property Analyzer
======================================
A web interface for the Zillow property analysis pipeline.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
from zillow_scraper import ZillowScraper
from comparable_analyzer import ComparableAnalyzer
from appraisal_engine import AppraisalEngine

app = Flask(__name__)

# Get the base directory for file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROPERTY_DATA_FILE = os.path.join(BASE_DIR, "property_data.json")
COMPARABLE_DATA_FILE = os.path.join(BASE_DIR, "comparable_analysis.json")
APPRAISAL_REPORT_FILE = os.path.join(BASE_DIR, "appraisal_report.txt")


@app.route("/")
def index():
    """Render the main input page."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Run the full 3-stage analysis pipeline:
    1. Scrape property data from Zillow
    2. Find comparable properties
    3. Generate appraisal and upgrade recommendations
    
    Returns JSON with all results or error message.
    """
    data = request.get_json()
    url = data.get("url", "").strip()
    
    if not url:
        return jsonify({"error": "Please provide a Zillow property URL."}), 400
    
    try:
        # Stage 1: Scrape the property
        scraper = ZillowScraper()
        property_data = scraper.scrape(url, save_json=True)
        
        # Stage 2: Analyze comparables
        analyzer = ComparableAnalyzer(
            input_file=PROPERTY_DATA_FILE,
            output_file=COMPARABLE_DATA_FILE
        )
        comp_data = analyzer.run_analysis()
        
        # Stage 3: Generate appraisal and upgrades
        engine = AppraisalEngine(
            property_data_path=PROPERTY_DATA_FILE,
            comparable_data_path=COMPARABLE_DATA_FILE,
            report_output_path=APPRAISAL_REPORT_FILE
        )
        engine.load_data()
        appraisal_result = engine.calculate_appraisal()
        upgrades = engine.generate_upgrade_recommendations()
        engine.generate_report()
        
        # Build response
        result = {
            "success": True,
            "property": _format_property_data(property_data),
            "comparables": _format_comparables(comp_data),
            "appraisal": _format_appraisal(appraisal_result),
            "upgrades": _format_upgrades(upgrades[:10])  # Top 10 upgrades
        }
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except FileNotFoundError as e:
        return jsonify({"error": f"File not found: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


def _format_property_data(data):
    """Format property data for JSON response."""
    return {
        "address": data.get("address", "N/A"),
        "price": data.get("price", "N/A"),
        "beds": data.get("beds", "N/A"),
        "baths": data.get("baths", "N/A"),
        "sqft": data.get("sqft", "N/A"),
        "lot_size": data.get("lot_size", "N/A"),
        "year_built": data.get("year_built", "N/A"),
        "property_type": data.get("property_type", "N/A"),
        "mls_number": data.get("mls_number", "N/A"),
        "description": data.get("description", "N/A"),
        "features": data.get("features", [])
    }


def _format_comparables(data):
    """Format comparable analysis data for JSON response."""
    if not data:
        return {}
    
    subject = data.get("subject_property", {})
    comparables = data.get("comparables", [])
    price_analysis = data.get("price_analysis", {})
    ppsf_analysis = data.get("price_per_sqft_analysis", {})
    
    formatted_comps = []
    for comp in comparables[:6]:  # Limit to 6 comparables
        formatted_comps.append({
            "address": comp.get("address", "N/A"),
            "price": _format_currency(comp.get("price", 0)),
            "sqft": _format_number(comp.get("sqft", 0)),
            "price_per_sqft": _format_currency(comp.get("price_per_sqft", 0)),
            "distance": f"{comp.get('distance_miles', 0):.1f} mi",
            "bedrooms": comp.get("bedrooms", "N/A"),
            "bathrooms": comp.get("bathrooms", "N/A")
        })
    
    return {
        "subject": {
            "address": subject.get("address", "N/A"),
            "city": subject.get("city", "N/A"),
            "state": subject.get("state", "N/A"),
            "zip_code": subject.get("zip_code", "N/A"),
            "beds": subject.get("bedrooms", "N/A"),
            "baths": subject.get("bathrooms", "N/A"),
            "sqft": _format_number(subject.get("sqft", 0)),
            "property_type": subject.get("property_type", "N/A")
        },
        "comparables": formatted_comps,
        "price_range": price_analysis.get("price_range", {}).get("suggested_offer_range", "N/A"),
        "median_price": _format_currency(price_analysis.get("statistics", {}).get("median_price", 0)),
        "average_price": _format_currency(price_analysis.get("statistics", {}).get("average_price", 0)),
        "avg_price_per_sqft": _format_currency(ppsf_analysis.get("statistics", {}).get("average", 0)),
        "confidence_level": data.get("valuation_estimate", {}).get("confidence_level", "N/A")
    }


def _format_appraisal(data):
    """Format appraisal result for JSON response."""
    if not data:
        return {}
    
    return {
        "estimated_value": _format_currency(data.get("appraisal_value", 0)),
        "confidence_low": _format_currency(data.get("confidence_low", 0)),
        "confidence_high": _format_currency(data.get("confidence_high", 0)),
        "comparable_value": _format_currency(data.get("comparable_value", 0)),
        "ppsf_value": _format_currency(data.get("ppsf_value", 0)),
        "adjusted_value": _format_currency(data.get("adjusted_value", 0)),
        "price_per_sqft": _format_currency(data.get("price_per_sqft", 0)),
        "comp_avg_ppsf": _format_currency(data.get("comp_avg_ppsf", 0))
    }


def _format_upgrades(upgrades):
    """Format upgrade recommendations for JSON response."""
    formatted = []
    for upgrade in upgrades:
        formatted.append({
            "name": upgrade.get("name", "N/A"),
            "estimated_cost": _format_currency(upgrade.get("estimated_cost", 0)),
            "resale_return": f"{upgrade.get('resale_return', 0) * 100:.0f}%",
            "roi": f"{upgrade.get('roi', 0) * 100:.0f}%",
            "value_recovery": _format_currency(upgrade.get("estimated_value_recovery", 0)),
            "regional_priority": upgrade.get("regional_priority", 3),
            "priority_label": _get_priority_label(upgrade.get("regional_priority", 3))
        })
    return formatted


def _format_currency(value):
    """Format a number as USD currency."""
    if isinstance(value, (int, float)):
        return f"${value:,.0f}"
    return str(value)


def _format_number(value):
    """Format a number with commas."""
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return str(value)


def _get_priority_label(priority):
    """Get priority label from priority number."""
    labels = {1: "High Priority", 2: "Medium Priority", 3: "Standard"}
    return labels.get(priority, "Standard")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
