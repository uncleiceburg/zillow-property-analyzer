# Zillow Property Analyzer

A Python pipeline that takes a Zillow listing URL and produces a property appraisal with comparable sales analysis and ranked upgrade recommendations for the Gulf Coast / Mississippi region.

## Pipeline Stages

```
Zillow URL → [zillow_scraper] → property_data.json
                                    ↓
              [comparable_analyzer] → comparable_analysis.json
                                    ↓
                [appraisal_engine] → appraisal_report.txt
```

## Stage 1 — zillow_scraper.py

Prompts for a Zillow property URL and extracts:
- Address, price, beds/baths/sqft, lot size, year built, property type
- MLS number, listing description, features & amenities
- Output: `property_data.json`

## Stage 2 — comparable_analyzer.py

Reads `property_data.json` and finds comparable properties:
- Same bedroom/bath count, similar sqft (±30%), same property type
- Within configurable radius (default: 5 miles)
- Calculates price per sqft, distance, and market statistics
- Output: `comparable_analysis.json`

## Stage 3 — appraisal_engine.py

Reads both JSON files and generates:
- **Appraisal estimate** using three methods:
  - Comparable sales weighted average (50%)
  - Price per sqft multiplication (30%)
  - Adjusted property method with feature differentials (20%)
- **Confidence range** (±8%)
- **Ranked upgrade list** with estimated costs and ROI (2024 Cost vs. Value, South Atlantic)
- Output: `appraisal_report.txt`

## Requirements

```bash
pip install requests beautifulsoup4 lxml
```

## Usage

```bash
python3 main.py
```

Paste a Zillow property URL when prompted. Results are saved to `property_data.json`, `comparable_analysis.json`, and `appraisal_report.txt`.

## Running Individual Stages

```bash
# Stage 1 only
python3 zillow_scraper.py

# Stage 2 only
python3 comparable_analyzer.py

# Stage 3 only
python3 appraisal_engine.py
```

## GUI Usage

A web-based graphical interface is available for easier use.

### Installation

```bash
pip install -r requirements_gui.txt
```

### Running the GUI

```bash
cd gui
python app.py
```

Then open your browser and navigate to `http://localhost:5000`

### GUI Features

- Clean, modern web interface
- Single-page property analysis
- Input a Zillow URL to run the full 3-stage pipeline
- Results displayed in organized sections:
  - Property Details
  - Comparable Analysis
  - Appraisal Estimate with confidence range
  - Ranked upgrade recommendations with cost and ROI
- Responsive design for desktop and mobile

## Disclaimer

Scraping Zillow may violate their Terms of Service. This tool is for educational and research purposes. For production use, consider Zillow's official API or obtain proper licensing.
