"""
appraisal_engine.py
===================

A Python script for automated real estate property appraisal and upgrade
recommendation analysis. Designed for the Gulf Coast / Mississippi Gulfport
area, leveraging comparable sales, price-per-sqft analysis, and regional
cost-vs-value data.

Classes
-------
AppraisalEngine
    Main orchestrator class that coordinates data loading, appraisal
    calculation, and report generation.

Functions
---------
load_json(path)
    Safely load and parse a JSON file, returning an empty dict on failure.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data Loading Helpers
# ---------------------------------------------------------------------------

def load_json(path: str) -> dict:
    """
    Load a JSON file and return its contents as a dictionary.

    Parameters
    ----------
    path : str
        Absolute or relative path to the JSON file.

    Returns
    -------
    dict
        Parsed JSON content, or an empty dict if the file cannot be read.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARNING] Could not load '{path}': {e}")
        return {}


# ---------------------------------------------------------------------------
# Regional Cost Data — Gulf Coast / Mississippi Gulfport
# ---------------------------------------------------------------------------

# Upgrade cost estimates are based on Mississippi Gulf Coast / Southern US
# regional data. Costs are approximate and include materials + labor.
# Sources: 2024 Remodeling Magazine Cost vs. Value Report (South Atlantic),
# HomeAdvisor, Angi (2023–2024).

UPGRADE_COSTS: dict[str, float] = {
    # Kitchen
    "minor_kitchen_remodel": 24_000,      # Minor cabinet/ countertop refresh
    "major_kitchen_remodel": 68_000,      # Full gut renovation
    "kitchen_appliance_upgrade": 4_500,   # Stainless steel appliance package
    # Bathroom
    "bathroom_remodel": 11_500,           # Mid-range full bath update
    "luxury_bathroom_remodel": 22_000,    # High-end bath renovation
    "bathroom_fixtures": 2_500,           # Fixtures only (faucet, toilet, etc.)
    # Curb Appeal / Exterior
    "roof_replacement": 12_500,           # Asphalt shingle, 2,000 sqft home
    "siding_replacement": 14_500,         # Vinyl siding, full home wrap
    "landscaping_upgrade": 3_500,         # Native/ drought-tolerant plantings
    "new_garage_door": 3_800,             # 16×7 steel garage door
    "exterior_paint": 4_200,              # Full house exterior repaint
    "driveway_replacement": 7_000,        # 600 sqft concrete driveway
    # Energy Efficiency (Gulf Coast climate priorities)
    "hvac_replacement": 8_200,            # Central AC/heat pump, 2,000 sqft
    "attic_insulation": 2_400,            # Blown-in insulation, R-38
    "energy_star_windows": 6_500,         # 10 windows, vinyl frame
    "solar_panels": 18_000,               # 4kW system after incentives
    "tankless_water_heater": 3_200,       # Gas tankless WH installation
    # Interior
    "hardwood_flooring": 8_000,           # 1,500 sqft, engineered hardwood
    "carpet_replacement": 4_000,          # 1,500 sqft, mid-range carpet
    "interior_paint": 3_000,              # Full interior repaint, 2,000 sqft home
    "basement_finish": 22_000,            # 600 sqft finished basement
    "deck_addition": 9_500,               # 400 sqft pressure-treated wood deck
    # Structural / Systems
    "electrical_panel_upgrade": 2_800,    # 200-amp panel replacement
    "plumbing_update": 4_500,             # Repipe with PEX, 2-bath home
    "foundation_repair": 7_500,           # Minor crack repair/ leveling
    "pool_installation": 35_000,          # In-ground vinyl pool (Southern US avg)
    "pool_maintenance_system": 4_500,     # Saltwater system/ automation
}

# Typical resale value recovered for each upgrade in the South Atlantic region.
# Values are percentages (0.0–1.0) derived from Remodeling Magazine's
# 2024 Cost vs. Value Report (South Atlantic).
UPGRADE_RESALE_RETURNS: dict[str, float] = {
    # Kitchen
    "minor_kitchen_remodel": 0.71,
    "major_kitchen_remodel": 0.54,
    "kitchen_appliance_upgrade": 0.80,
    # Bathroom
    "bathroom_remodel": 0.65,
    "luxury_bathroom_remodel": 0.52,
    "bathroom_fixtures": 0.72,
    # Curb Appeal / Exterior
    "roof_replacement": 0.66,
    "siding_replacement": 0.74,
    "landscaping_upgrade": 0.75,
    "new_garage_door": 0.81,
    "exterior_paint": 0.69,
    "driveway_replacement": 0.62,
    # Energy Efficiency
    "hvac_replacement": 0.72,
    "attic_insulation": 0.70,
    "energy_star_windows": 0.64,
    "solar_panels": 0.58,
    "tankless_water_heater": 0.67,
    # Interior
    "hardwood_flooring": 0.77,
    "carpet_replacement": 0.70,
    "interior_paint": 0.73,
    "basement_finish": 0.64,
    "deck_addition": 0.65,
    # Structural / Systems
    "electrical_panel_upgrade": 0.75,
    "plumbing_update": 0.68,
    "foundation_repair": 0.70,
    "pool_installation": 0.50,
    "pool_maintenance_system": 0.65,
}

# Regional upgrade priorities for Gulf Coast / Southern US market.
# Priority tiers: 1 (highest), 2, 3.  Reflects buyer/seller concerns unique
# to the humid subtropical climate and Gulf Coast buyer profile.
REGIONAL_PRIORITIES: dict[str, int] = {
    # Tier 1 — Critical for Gulf Coast climate
    "hvac_replacement": 1,
    "roof_replacement": 1,
    "bathroom_remodel": 1,
    "minor_kitchen_remodel": 1,
    "landscaping_upgrade": 1,       # Hurricane/ flood resilience landscaping
    "siding_replacement": 1,
    # Tier 2 — High value-add
    "kitchen_appliance_upgrade": 2,
    "bathroom_fixtures": 2,
    "attic_insulation": 2,          # Heat management
    "energy_star_windows": 2,       # Storm resistance + energy
    "exterior_paint": 2,
    "interior_paint": 2,
    "hardwood_flooring": 2,         # Humidity-aware flooring
    "new_garage_door": 2,
    # Tier 3 — Situational
    "tankless_water_heater": 3,
    "solar_panels": 3,
    "major_kitchen_remodel": 3,
    "luxury_bathroom_remodel": 3,
    "electrical_panel_upgrade": 3,
    "plumbing_update": 3,
    "deck_addition": 3,
    "driveway_replacement": 3,
    "basement_finish": 3,           # Less common in Gulf Coast
    "foundation_repair": 3,
    "carpet_replacement": 3,
    "pool_installation": 3,
    "pool_maintenance_system": 3,
}

# ---------------------------------------------------------------------------
# AppraisalEngine
# ---------------------------------------------------------------------------

class AppraisalEngine:
    """
    Automated property appraisal and upgrade recommendation engine.

    Parameters
    ----------
    property_data_path : str
        Path to the property_data.json file.
    comparable_data_path : str
        Path to the comparable_analysis.json file.
    report_output_path : str, optional
        Path for the output appraisal report. Defaults to
        'appraisal_report.txt' in the current working directory.

    Attributes
    ----------
    property_data : dict
        Loaded property data.
    comparable_data : dict
        Loaded comparable sales data.
    appraisal_value : float or None
        Calculated estimated appraisal value.
    confidence_range : tuple[float, float] or None
        (Low, High) estimate range.
    upgrades : list[dict]
        Ranked list of recommended upgrades with cost/ROI data.

    Methods
    -------
    load_data()
        Load and validate input JSON files.
    calculate_appraisal()
        Run all appraisal sub-methods and return a summary dict.
    generate_upgrade_recommendations()
        Build ranked upgrade list with ROI estimates.
    generate_report()
        Write the full appraisal report to disk.
    run()
        Execute the full appraisal pipeline.
    """

    # -------------------------------------------------------------------------
    # Configuration constants
    # -------------------------------------------------------------------------
    DEFAULT_WEIGHT_COMPARABLE = 0.50   # Weight for comparable sales method
    DEFAULT_WEIGHT_PPSF = 0.30         # Weight for price-per-sqft method
    DEFAULT_WEIGHT_ADJUSTED = 0.20     # Weight for adjusted property method

    # Confidence interval half-width as a percentage of appraised value.
    CONFIDENCE_MARGIN = 0.08           # ±8 %

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(
        self,
        property_data_path: str = "property_data.json",
        comparable_data_path: str = "comparable_analysis.json",
        report_output_path: str = "appraisal_report.txt",
    ) -> None:
        self.property_data_path = property_data_path
        self.comparable_data_path = comparable_data_path
        self.report_output_path = report_output_path

        # Runtime state
        self.property_data: dict = {}
        self.comparable_data: dict = {}
        self.appraisal_value: Optional[float] = None
        self.confidence_range: Optional[tuple[float, float]] = None
        self.upgrades: list[dict] = []
        self._report_lines: list[str] = []

    # -------------------------------------------------------------------------
    # Data Loading
    # -------------------------------------------------------------------------

    def load_data(self) -> None:
        """
        Load property_data.json and comparable_analysis.json from disk.

        Prints a warning for each file that cannot be found or parsed.
        """
        self.property_data = load_json(self.property_data_path)
        self.comparable_data = load_json(self.comparable_data_path)

        if not self.property_data:
            print("[WARNING] property_data.json is empty or not found.")
        if not self.comparable_data:
            print("[WARNING] comparable_analysis.json is empty or not found.")

    # -------------------------------------------------------------------------
    # Appraisal Calculation
    # -------------------------------------------------------------------------

    def calculate_appraisal(self) -> dict:
        """
        Calculate the estimated property appraisal value using three methods:

        1. **Comparable Sales Analysis (weighted average)**
           Computes a weighted average price from the most similar comps,
           giving higher weight to comps with fewer adjustments required.

        2. **Price Per Square Foot (PPSF) Method**
           Multiplies the subject property's heated living area by the
           weighted average price-per-sqft of the comparables.

        3. **Adjusted Property Value Method**
           Starts from the median comp price and applies explicit
           dollar adjustments for each attribute difference between
           the subject and the comps.

        The final estimate blends all three methods using configured weights
        and is returned alongside a confidence interval.

        Returns
        -------
        dict
            A summary dictionary containing:

            - ``appraisal_value`` (float): Blended point estimate.
            - ``confidence_low`` (float): Lower bound of ±8 % range.
            - ``confidence_high`` (float): Upper bound of ±8 % range.
            - ``comparable_value`` (float): Value from comp-sales method.
            - ``ppsf_value`` (float): Value from price-per-sqft method.
            - ``adjusted_value`` (float): Value from adjusted method.
            - ``price_per_sqft`` (float): Implied $/sqft for subject.
            - ``comp_avg_ppsf`` (float): Weighted average $/sqft of comps.
        """
        comps = self.comparable_data.get("comparables", [])
        subj = self.property_data

        # ------------------------------------------------------------------
        # 1 — Comparable Sales Analysis
        # ------------------------------------------------------------------
        comp_value, comp_avg_ppsf = self._comparable_sales_analysis(comps, subj)

        # ------------------------------------------------------------------
        # 2 — Price Per Square Foot Method
        # ------------------------------------------------------------------
        ppsf_value = self._ppsf_method(comps, subj, comp_avg_ppsf)

        # ------------------------------------------------------------------
        # 3 — Adjusted Property Value Method
        # ------------------------------------------------------------------
        adjusted_value = self._adjusted_property_method(comps, subj)

        # ------------------------------------------------------------------
        # 4 — Blend the three estimates
        # ------------------------------------------------------------------
        raw_value = (
            comp_value * self.DEFAULT_WEIGHT_COMPARABLE
            + ppsf_value * self.DEFAULT_WEIGHT_PPSF
            + adjusted_value * self.DEFAULT_WEIGHT_ADJUSTED
        )

        # Round to nearest $500 for a more realistic appraisal figure
        self.appraisal_value = _round_to_nearest(raw_value, 500)

        margin = self.appraisal_value * self.CONFIDENCE_MARGIN
        self.confidence_range = (
            _round_to_nearest(self.appraisal_value - margin, 500),
            _round_to_nearest(self.appraisal_value + margin, 500),
        )

        return {
            "appraisal_value": self.appraisal_value,
            "confidence_low": self.confidence_range[0],
            "confidence_high": self.confidence_range[1],
            "comparable_value": comp_value,
            "ppsf_value": ppsf_value,
            "adjusted_value": adjusted_value,
            "price_per_sqft": self._get_subject_ppsf(subj),
            "comp_avg_ppsf": comp_avg_ppsf,
        }

    # ---- Sub-methods --------------------------------------------------------

    def _comparable_sales_analysis(
        self, comps: list[dict], subj: dict
    ) -> tuple[float, float]:
        """
        Calculate the weighted average value from comparable sales.

        Comps with fewer adjustments receive higher weight.

        Parameters
        ----------
        comps : list[dict]
            List of comparable property records.
        subj : dict
            Subject property record.

        Returns
        -------
        tuple[float, float]
            (weighted_average_value, weighted_average_ppsf)
        """
        if not comps:
            return self._fallback_appraisal(subj), 0.0

        total_weight = 0.0
        weighted_value = 0.0
        weighted_ppsf = 0.0

        for comp in comps:
            price = comp.get("sale_price", 0)
            sqft = comp.get("heated_sqft", 1)
            ppsf = price / sqft if sqft > 0 else 0

            # Weight inversely proportional to adjustment count/ magnitude
            adjustment = self._total_adjustment(comp, subj)
            weight = 1.0 / (1.0 + abs(adjustment) / 100_000)

            weighted_value += price * weight
            weighted_ppsf += ppsf * weight
            total_weight += weight

        if total_weight == 0:
            return self._fallback_appraisal(subj), 0.0

        return weighted_value / total_weight, weighted_ppsf / total_weight

    def _ppsf_method(
        self, comps: list[dict], subj: dict, comp_avg_ppsf: float
    ) -> float:
        """
        Price-per-sqft valuation: subject_sqft × comp_avg_ppsf.

        Parameters
        ----------
        comps : list[dict]
            Comparable properties (used only to derive avg PPSF if not passed).
        subj : dict
            Subject property.
        comp_avg_ppsf : float
            Pre-computed weighted average comp $/sqft.

        Returns
        -------
        float
            Estimated value based on square footage.
        """
        subj_sqft = subj.get("heated_sqft", 1)
        if comp_avg_ppsf > 0:
            return subj_sqft * comp_avg_ppsf

        # Fallback: use median comp price × (subject_sqft / median_comp_sqft)
        if comps:
            prices = [c.get("sale_price", 0) for c in comps if c.get("sale_price")]
            sqfts = [c.get("heated_sqft", 1) for c in comps if c.get("heated_sqft")]
            if prices and sqfts:
                median_price = sorted(prices)[len(prices) // 2]
                median_sqft = sorted(sqfts)[len(sqfts) // 2]
                ratio = subj_sqft / median_sqft if median_sqft > 0 else 1
                return median_price * ratio
        return self._fallback_appraisal(subj)

    def _adjusted_property_method(self, comps: list[dict], subj: dict) -> float:
        """
        Adjusted property method: start with median comp price, apply
        explicit attribute adjustments for beds, baths, sqft, lot size,
        and year built differences.

        Parameters
        ----------
        comps : list[dict]
            Comparable properties.
        subj : dict
            Subject property.

        Returns
        -------
        float
            Adjusted estimated value.
        """
        if not comps:
            return self._fallback_appraisal(subj)

        prices = [c.get("sale_price", 0) for c in comps if c.get("sale_price")]
        if not prices:
            return self._fallback_appraisal(subj)

        base_price = sorted(prices)[len(prices) // 2]

        # Calculate average adjustment across all comps
        total_adj = sum(self._total_adjustment(c, subj) for c in comps) / len(comps)
        return base_price + total_adj

    def _total_adjustment(self, comp: dict, subj: dict) -> float:
        """
        Calculate the total dollar adjustment needed to make a comparable
        property equivalent to the subject property.

        Adjustment factors (positive = comp is inferior = add value;
                          negative = comp is superior = subtract value):

        - Bedroom difference  : ±$5,000 per bedroom
        - Bathroom difference : ±$7,500 per bathroom
        - Sqft difference     : ±$75 per sqft
        - Lot size difference : ±$2 per sqft of lot
        - Year built delta    : ±$500 per year difference (newer = more $)

        Parameters
        ----------
        comp : dict
            Comparable property.
        subj : dict
            Subject property.

        Returns
        -------
        float
            Total adjustment in dollars.
        """
        subj_beds = subj.get("beds", 0)
        subj_baths = subj.get("baths", 0)
        subj_sqft = subj.get("heated_sqft", 1)
        subj_lot = subj.get("lot_sqft", 0)
        subj_year = subj.get("year_built", 2000)

        comp_beds = comp.get("beds", 0)
        comp_baths = comp.get("baths", 0)
        comp_sqft = comp.get("heated_sqft", 1)
        comp_lot = comp.get("lot_sqft", 0)
        comp_year = comp.get("year_built", 2000)

        bed_adj = (subj_beds - comp_beds) * 5_000
        bath_adj = (subj_baths - comp_baths) * 7_500
        sqft_adj = (subj_sqft - comp_sqft) * 75
        lot_adj = (subj_lot - comp_lot) * 2
        year_adj = (subj_year - comp_year) * 500

        return bed_adj + bath_adj + sqft_adj + lot_adj + year_adj

    def _get_subject_ppsf(self, subj: dict) -> float:
        """Return the subject property's implied price per sqft (appraisal / sqft)."""
        sqft = subj.get("heated_sqft", 1)
        if self.appraisal_value and sqft > 0:
            return self.appraisal_value / sqft
        return 0.0

    def _fallback_appraisal(self, subj: dict) -> float:
        """
        Return a rough fallback estimate when insufficient comp data exists.

        Uses a regional median price-per-sqft for Gulf Coast homes (~$185/sqft)
        multiplied by the subject's heated square footage.
        """
        sqft = subj.get("heated_sqft", 1)
        gulf_coast_median_ppsf = 185.0
        return sqft * gulf_coast_median_ppsf

    # -------------------------------------------------------------------------
    # Upgrade Recommendations
    # -------------------------------------------------------------------------

    def generate_upgrade_recommendations(self) -> list[dict]:
        """
        Generate a ranked list of value-adding upgrades for the subject
        property based on its current condition, features, and regional
        market priorities for the Gulf Coast / Mississippi Gulfport area.

        Ranking Logic
        ------------
        1. **Condition score** — Properties rated 'fair' or 'poor' get
           fundamental repairs (HVAC, roof, bathroom) prioritized higher.
        2. **Regional tier** — Tier-1 regional priorities are boosted above
           Tier-3 upgrades regardless of ROI.
        3. **ROI** — Pure ROI-weighted sort as a tiebreaker.

        Returns
        -------
        list[dict]
            List of upgrade records, each containing:

            - ``upgrade_key`` (str): Unique identifier from the cost table.
            - ``name`` (str): Human-readable upgrade name.
            - ``estimated_cost`` (float): Project cost in dollars.
            - ``resale_return`` (float): Fraction of cost recovered at sale.
            - ``roi`` (float): Estimated ROI as a decimal (e.g. 0.72).
            - ``regional_priority`` (int): 1 (highest) – 3 (lowest).
            - ``priority_score`` (float): Combined ranking score.
        """
        subj = self.property_data
        condition = subj.get("condition", "unknown").lower()
        beds = subj.get("beds", 0)
        baths = subj.get("baths", 0)
        sqft = subj.get("heated_sqft", 1)
        year = subj.get("year_built", 2000)
        has_pool = subj.get("features", {}).get("pool", False)
        heating = subj.get("features", {}).get("hvac_age", None)

        upgrades: list[dict] = []

        for key in UPGRADE_COSTS:
            # Skip pool if already present
            if key == "pool_installation" and has_pool:
                continue

            cost = UPGRADE_COSTS[key]
            resale_return = UPGRADE_RESALE_RETURNS.get(key, 0.60)
            roi = resale_return  # Simplified: ROI ≈ resale recovery rate
            regional_tier = REGIONAL_PRIORITIES.get(key, 3)

            # Condition-based scoring adjustments
            cond_priority_boost = 0.0
            if condition in ("fair", "poor"):
                if key in ("hvac_replacement", "roof_replacement", "bathroom_remodel"):
                    cond_priority_boost = 3.0
                elif key in ("siding_replacement", "attic_insulation", "exterior_paint"):
                    cond_priority_boost = 2.0
            elif condition == "good":
                if key in ("minor_kitchen_remodel", "kitchen_appliance_upgrade"):
                    cond_priority_boost = 1.5

            # Age-based boost for older HVAC systems
            if key == "hvac_replacement":
                try:
                    hvac_age = int(heating) if heating else 0
                    if hvac_age > 10:
                        cond_priority_boost += 2.0
                except (ValueError, TypeError):
                    pass

            # Size-based boost (larger homes benefit more from major remodels)
            size_factor = min(sqft / 2_000, 1.5)  # Cap at 1.5× for homes > 3,000 sqft

            # Combined priority score
            # Formula: (4 - regional_tier) gives tier-1 items a base of 3
            # then adds ROI, condition boost, and size factor
            priority_score = (
                (4 - regional_tier) * 2.0
                + roi * 2.0
                + cond_priority_boost
                + size_factor * (1 - regional_tier / 3)
            )

            upgrades.append({
                "upgrade_key": key,
                "name": _format_name(key),
                "estimated_cost": cost,
                "resale_return": resale_return,
                "roi": roi,
                "estimated_value_recovery": round(cost * resale_return, 2),
                "regional_priority": regional_tier,
                "priority_score": round(priority_score, 3),
            })

        # Sort: highest priority_score first
        upgrades.sort(key=lambda x: x["priority_score"], reverse=True)

        self.upgrades = upgrades
        return upgrades

    # -------------------------------------------------------------------------
    # Report Generation
    # -------------------------------------------------------------------------

    def generate_report(self) -> str:
        """
        Build the formatted appraisal report as a string and write it to
        the configured output path.

        Returns
        -------
        str
            The full report text.
        """
        self._report_lines = []
        self._add_header()
        self._add_property_summary()
        self._add_appraisal_estimate()
        self._add_price_per_sqft_analysis()
        self._add_comparable_adjustments()
        self._add_upgrade_recommendations()
        self._add_footer()

        report_text = "\n".join(self._report_lines)

        # Write to output file
        with open(self.report_output_path, "w", encoding="utf-8") as f:
            f.write(report_text)

        print(f"[OK] Appraisal report written to: {self.report_output_path}")
        return report_text

    # ---- Report Sections ----------------------------------------------------

    def _add_header(self) -> None:
        self._report_lines.extend([
            "=" * 72,
            "             RESIDENTIAL PROPERTY APPRAISAL REPORT",
            "             Gulf Coast / Mississippi Gulfport Region",
            "=" * 72,
            "",
        ])

    def _add_property_summary(self) -> None:
        subj = self.property_data
        address = subj.get("address", "Unknown Address")
        city = subj.get("city", "Gulfport")
        state = subj.get("state", "MS")
        zipcode = subj.get("zip", "39503")
        beds = subj.get("beds", "N/A")
        baths = subj.get("baths", "N/A")
        sqft = subj.get("heated_sqft", "N/A")
        lot = subj.get("lot_sqft", "N/A")
        year = subj.get("year_built", "N/A")
        condition = subj.get("condition", "Unknown")
        style = subj.get("style", "Unknown")
        parking = subj.get("parking", "Unknown")
        features = subj.get("features", {})

        lot_acres = f"{lot / 43_560:.2f} ac" if isinstance(lot, (int, float)) and lot else "N/A"

        self._report_lines.extend([
            "SECTION 1 — PROPERTY SUMMARY",
            "-" * 40,
            f"  Address    : {address}",
            f"  Location   : {city}, {state} {zipcode}",
            f"  Style      : {style}",
            f"  Year Built : {year}",
            f"  Condition  : {condition}",
            "",
            "  Interior",
            f"    Beds          : {beds}",
            f"    Baths         : {baths}",
            f"    Heated SqFt   : {sqft:,}" if isinstance(sqft, (int, float)) else f"    Heated SqFt   : {sqft}",
            "",
            "  Lot & Exterior",
            f"    Lot Size      : {lot:,} sqft ({lot_acres})" if isinstance(lot, (int, float)) else f"    Lot Size      : {lot}",
            f"    Parking       : {parking}",
            "",
            "  Key Features",
        ])
        if features:
            for feat, val in features.items():
                self._report_lines.append(f"    {feat.title()}   : {val}")
        else:
            self._report_lines.append("    (none recorded)")
        self._report_lines.append("")

    def _add_appraisal_estimate(self) -> None:
        val = self.appraisal_value
        lo, hi = self.confidence_range or (0, 0)
        comp_val = self._latest.get("comparable_value", 0)
        ppsf_val = self._latest.get("ppsf_value", 0)
        adj_val = self._latest.get("adjusted_value", 0)

        self._report_lines.extend([
            "SECTION 2 — APPRAISAL ESTIMATE",
            "-" * 40,
            "",
            f"  *** ESTIMATED APPRAISAL VALUE ***",
            f"      ${val:,.0f}" if val else "      (Insufficient data)",
            "",
            f"  Confidence Range (8%):  ${lo:,.0f}  —  ${hi:,.0f}",
            "",
            "  Method Breakdown:",
            f"    Comparable Sales Analysis  : ${comp_val:,.0f}" if comp_val else "    Comparable Sales Analysis  : N/A",
            f"    Price Per SqFt Method      : ${ppsf_val:,.0f}" if ppsf_val else "    Price Per SqFt Method        : N/A",
            f"    Adjusted Property Method   : ${adj_val:,.0f}" if adj_val else "    Adjusted Property Method     : N/A",
            "",
            "  Methodology Notes",
            "  ─────────────────",
            "  The final estimate blends three independent methods:",
            "  • Comparable Sales Analysis (50% weight) — weighted average of",
            "    recent sales, adjusted for attribute differences.",
            "  • Price Per SqFt Method (30% weight) — subject sqft × comp avg.",
            "  • Adjusted Property Method (20% weight) — median comp price",
            "    with explicit dollar adjustments for beds, baths, sqft,",
            "    lot size, and year built.",
            "  The ±8% confidence range accounts for method variance and",
            "  market fluctuation in the Gulf Coast region.",
            "",
        ])

    def _add_price_per_sqft_analysis(self) -> None:
        subj_ppsf = self._latest.get("price_per_sqft", 0)
        comp_avg_ppsf = self._latest.get("comp_avg_ppsf", 0)
        sqft = self.property_data.get("heated_sqft", 1)

        self._report_lines.extend([
            "SECTION 3 — PRICE PER SQUARE FOOT ANALYSIS",
            "-" * 40,
            f"  Subject Property SqFt    : {sqft:,}",
            f"  Subject Implied $/SqFt  : ${subj_ppsf:,.2f}" if subj_ppsf else "  Subject Implied $/SqFt  : N/A",
            f"  Comps Weighted Avg $/SqFt: ${comp_avg_ppsf:,.2f}" if comp_avg_ppsf else "  Comps Weighted Avg $/SqFt : N/A",
            "",
        ])

        if subj_ppsf and comp_avg_ppsf:
            diff = subj_ppsf - comp_avg_ppsf
            pct = (diff / comp_avg_ppsf) * 100
            pct_abs = abs(pct)
            if abs(diff) < 5:
                assessment = "IN LINE with comparable properties."
            elif diff > 0:
                assessment = f"{pct_abs:.1f}% ABOVE comps — may indicate overvaluation\n    or superior features relative to the comp set."
            else:
                assessment = f"{pct_abs:.1f}% BELOW comps — potential undervaluation or\n    inferior condition/ features vs. the comp set."
            self._report_lines.append(f"  Assessment: {assessment}")

        self._report_lines.append("")

    def _add_comparable_adjustments(self) -> None:
        comps = self.comparable_data.get("comparables", [])
        if not comps:
            return

        self._report_lines.extend([
            "SECTION 4 — COMPARABLE ADJUSTMENTS SUMMARY",
            "-" * 40,
            "  (Adjustments relative to subject property)",
            "",
            f"  {'Address':<35} {'Price':>12}  {'Adj':>10}  {'Adj $/Sqft':>10}",
            f"  {'-'*35} {'-'*12}  {'-'*10}  {'-'*10}",
        ])

        for comp in comps:
            addr = comp.get("address", "Unknown")[:34]
            price = comp.get("sale_price", 0)
            adj = self._total_adjustment(comp, self.property_data)
            sqft = comp.get("heated_sqft", 1)
            adj_ppsf = adj / sqft if sqft > 0 else 0

            adj_str = f"+${adj:,.0f}" if adj >= 0 else f"-${abs(adj):,.0f}"
            self._report_lines.append(
                f"  {addr:<35} ${price:>10,}  {adj_str:>10}  "
                f"{adj_ppsf:>+10.2f}"
            )
        self._report_lines.append("")

    def _add_upgrade_recommendations(self) -> None:
        self._report_lines.extend([
            "SECTION 5 — RECOMMENDED UPGRADES & ESTIMATED ROI",
            "-" * 40,
            "  Ranked by priority score (regional tier + ROI + condition).",
            "  Based on Gulf Coast / Mississippi Gulfport cost data.",
            "  ROI = Estimated resale value recovery ÷ project cost.",
            "",
            f"  {'Rank':<5} {'Upgrade':<32} {'Est. Cost':>11}  {'Value Rec.':>11}  {'ROI':>6}  {'Tier':>5}",
            f"  {'-'*5} {'-'*32} {'-'*11}  {'-'*11}  {'-'*6}  {'-'*5}",
        ])

        for i, u in enumerate(self.upgrades[:20], start=1):  # Top 20
            self._report_lines.append(
                f"  {i:<5} {u['name']:<32} ${u['estimated_cost']:>9,}  "
                f"${u['estimated_value_recovery']:>9,}  {u['roi']:>6.0%}  "
                f"  {u['regional_priority']}"
            )

        self._report_lines.extend([
            "",
            "  Tier 1 = Critical for Gulf Coast climate/ market.",
            "  Tier 2 = High demand among Gulf Coast buyers.",
            "  Tier 3 = Situational / neighborhood-dependent.",
            "",
            "  Disclaimer: Cost estimates include materials + labor",
            "  (Southern US regional averages). Actual costs vary by",
            "  contractor, permit fees, and material selections.",
            "  ROI estimates based on 2024 Remodeling Magazine",
            "  Cost vs. Value Report (South Atlantic Region).",
            "",
        ])

    def _add_footer(self) -> None:
        self._report_lines.extend([
            "=" * 72,
            "  End of Report",
            "  Prepared by: AppraisalEngine v1.0  |  Gulf Coast Region",
            "  Note: This report is an estimate only and should not be",
            "  used as a substitute for a licensed appraisal.",
            "=" * 72,
        ])

    # -------------------------------------------------------------------------
    # Pipeline Entry Point
    # -------------------------------------------------------------------------

    def run(self) -> dict:
        """
        Execute the full appraisal pipeline.

        Steps
        -----
        1. Load JSON data from disk.
        2. Calculate the appraisal estimate using all three methods.
        3. Generate ranked upgrade recommendations with ROI.
        4. Write the formatted report to ``self.report_output_path``.

        Returns
        -------
        dict
            A dictionary with keys ``appraisal``, ``upgrades``, and
            ``report_path`` summarizing the results.
        """
        print("--- AppraisalEngine: Starting analysis ---")

        # 1 — Load data
        self.load_data()

        # 2 — Calculate appraisal
        appraisal_result = self.calculate_appraisal()
        self._latest = appraisal_result  # Store for report generation

        # 3 — Generate upgrades
        self.generate_upgrade_recommendations()

        # 4 — Write report
        self.generate_report()

        print("--- AppraisalEngine: Complete ---")
        return {
            "appraisal": appraisal_result,
            "upgrades": self.upgrades,
            "report_path": self.report_output_path,
        }


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def _round_to_nearest(value: float, nearest: float) -> float:
    """Round a value to the nearest increment (e.g., $500)."""
    return round(value / nearest) * nearest


def _format_name(key: str) -> str:
    """Convert an upgrade key like 'minor_kitchen_remodel' → 'Minor Kitchen Remodel'."""
    return " ".join(word.title() for word in key.split("_"))


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = AppraisalEngine(
        property_data_path="/tmp/zillow_analyzer/property_data.json",
        comparable_data_path="/tmp/zillow_analyzer/comparable_analysis.json",
        report_output_path="/tmp/zillow_analyzer/appraisal_report.txt",
    )
    result = engine.run()
    print(f"\nAppraisal Value : ${result['appraisal']['appraisal_value']:,.0f}")
    print(f"Confidence Range: ${result['appraisal']['confidence_low']:,.0f}"
          f" – ${result['appraisal']['confidence_high']:,.0f}")
    print(f"Report saved to : {result['report_path']}")
