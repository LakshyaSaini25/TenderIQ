"""
Rule definitions, keyword patterns, and regex constants for deterministic Opportunity Processing.
"""

# Primary Keywords for Opportunity Detection & Classification
TENDER_KEYWORDS = [
    "tender", "bid", "bidding", "rfp", "rfq", "eoi", "nit",
    "notice inviting tender", "notice inviting bid", "work order",
    "request for proposal", "request for quotation", "expression of interest",
    "procurement notice", "invitation to bid", "invitation for bid"
]

PROJECT_KEYWORDS = [
    "project", "construction", "development", "installation",
    "infrastructure", "civil works", "expansion", "plant",
    "smart city", "highway", "building construction", "pipeline"
]

PROCUREMENT_KEYWORDS = [
    "procurement", "quotation", "supply", "purchase", "equipment",
    "materials", "vendor", "rate contract", "supply of", "procurement of"
]

CONSULTANCY_KEYWORDS = [
    "consultancy", "consultant", "advisory", "detailed project report",
    "dpr", "feasibility study", "project management consultant", "pmc"
]

# Exclusion / Non-Opportunity Indicators
NON_OPPORTUNITY_INDICATORS = [
    "about us", "privacy policy", "terms of use", "terms of service",
    "contact us", "login to your account", "forgot password",
    "all rights reserved", "copyright 202"
]

# Standard Categories Tree Initial Data
INITIAL_CATEGORIES = [
    {
        "name": "Construction",
        "children": [
            "Building Construction",
            "Road & Highway",
            "Infrastructure",
            "Civil Works"
        ]
    },
    {
        "name": "Procurement",
        "children": [
            "Equipment",
            "Materials",
            "IT",
            "Services"
        ]
    },
    {
        "name": "Consultancy",
        "children": [
            "Architecture",
            "Engineering",
            "Project Management",
            "Other"
        ]
    }
]

# Standard Locations Initial Data (Focusing on India states & key cities for normalization)
INITIAL_LOCATIONS = [
    {
        "country": "India",
        "states": [
            {"state": "Uttar Pradesh", "cities": ["Noida", "Greater Noida", "Lucknow", "Kanpur", "Meerut", "Varanasi", "Agra"]},
            {"state": "Delhi", "cities": ["New Delhi", "Delhi NCR"]},
            {"state": "Maharashtra", "cities": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik"]},
            {"state": "Karnataka", "cities": ["Bengaluru", "Bangalore", "Mysuru", "Hubballi"]},
            {"state": "Tamil Nadu", "cities": ["Chennai", "Coimbatore", "Madurai"]},
            {"state": "Telangana", "cities": ["Hyderabad", "Secunderabad"]},
            {"state": "Gujarat", "cities": ["Ahmedabad", "Surat", "Vadodara", "Gandhinagar"]},
            {"state": "West Bengal", "cities": ["Kolkata", "Howrah", "Siliguri"]},
            {"state": "Rajasthan", "cities": ["Jaipur", "Jodhpur", "Udaipur"]},
            {"state": "Haryana", "cities": ["Gurugram", "Gurgaon", "Faridabad", "Panchkula"]}
        ]
    }
]

