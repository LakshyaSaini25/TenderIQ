"""
Source Discovery Service
Discovers relevant tender sources for a given Indian state/city using:
1. A curated database of ~80+ known Indian tender portals (government + PSU + sector)
2. DuckDuckGo Instant Answer API for supplemental live results (free, no API key)
"""
import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import urlparse, quote_plus

import httpx

logger = logging.getLogger(__name__)


# ─── Curated Portal Database ────────────────────────────────────────────────

CURATED_PORTALS = [
    # ── National / Central Government ──────────────────────────────────────
    {
        "name": "CPPP — Central Public Procurement Portal",
        "url": "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata",
        "type": "GOVERNMENT",
        "description": "Central Government's unified tender portal for all ministries and departments. Largest source of government tenders in India.",
        "tags": ["national", "central government", "all states", "all sectors"],
        "states": [],  # empty = all states
        "relevance_base": 90,
    },
    {
        "name": "GeM — Government e-Marketplace",
        "url": "https://bidplus.gem.gov.in/all-bids",
        "type": "GOVERNMENT",
        "description": "Government e-Marketplace for procurement of goods and services by government buyers. Covers all states.",
        "tags": ["national", "goods", "services", "government"],
        "states": [],
        "relevance_base": 88,
    },
    {
        "name": "eProcure India — NIC National Portal",
        "url": "https://eprocure.gov.in/eprocure/app",
        "type": "GOVERNMENT",
        "description": "NIC's national e-procurement system used by central ministries and many state agencies.",
        "tags": ["national", "NIC", "all sectors"],
        "states": [],
        "relevance_base": 85,
    },
    {
        "name": "eTenders India — Government Tenders",
        "url": "https://etenders.gov.in/eprocure/app",
        "type": "GOVERNMENT",
        "description": "Another national NIC portal for central government procurement and tenders.",
        "tags": ["national", "NIC", "government"],
        "states": [],
        "relevance_base": 82,
    },
    {
        "name": "TPDDL Tenders",
        "url": "https://www.tpddl.com/tenders.aspx",
        "type": "COMPANY_WEBSITE",
        "description": "Tata Power Delhi Distribution tenders.",
        "tags": ["power", "electricity", "Delhi"],
        "states": ["Delhi"],
        "relevance_base": 60,
    },

    # ── Railways ────────────────────────────────────────────────────────────
    {
        "name": "Indian Railways e-Procurement",
        "url": "https://www.ireps.gov.in",
        "type": "GOVERNMENT",
        "description": "Indian Railways' e-procurement system. Covers all railway zones across India.",
        "tags": ["railways", "national", "engineering", "civil"],
        "states": [],
        "relevance_base": 80,
    },
    {
        "name": "RITES Tenders",
        "url": "https://rites.com/web/index.php/tender",
        "type": "COMPANY_WEBSITE",
        "description": "RITES Limited (Railways subsidiary) tender notices for infrastructure and consultancy.",
        "tags": ["railways", "infrastructure", "consultancy"],
        "states": [],
        "relevance_base": 72,
    },

    # ── PSU Portals ─────────────────────────────────────────────────────────
    {
        "name": "NTPC e-Procurement",
        "url": "https://eprocurentpc.nic.in/nicgep/app",
        "type": "COMPANY_WEBSITE",
        "description": "NTPC Limited's tender portal for power plant construction, O&M, and supplies.",
        "tags": ["power", "energy", "PSU", "construction"],
        "states": ["Uttar Pradesh", "Bihar", "Jharkhand", "Chhattisgarh", "Madhya Pradesh", "Rajasthan", "Odisha", "West Bengal"],
        "relevance_base": 75,
    },
    {
        "name": "BHEL e-Procurement",
        "url": "https://eprocurebhel.co.in/nicgep/app",
        "type": "COMPANY_WEBSITE",
        "description": "Bharat Heavy Electricals Limited tender portal — power, industrial equipment.",
        "tags": ["manufacturing", "power", "PSU", "heavy industry"],
        "states": ["Uttar Pradesh", "Karnataka", "Tamil Nadu", "Andhra Pradesh", "Madhya Pradesh", "Telangana"],
        "relevance_base": 73,
    },
    {
        "name": "Coal India Limited Tenders",
        "url": "https://coalindiatenders.nic.in/nicgep/app",
        "type": "COMPANY_WEBSITE",
        "description": "Coal India Limited e-procurement for mining, civil, and supply contracts.",
        "tags": ["mining", "coal", "PSU", "civil"],
        "states": ["Jharkhand", "Odisha", "West Bengal", "Chhattisgarh", "Madhya Pradesh", "Assam", "Meghalaya"],
        "relevance_base": 74,
    },
    {
        "name": "BPCL Tenders",
        "url": "https://www.bpcleindia.com/bpcltenders/tenderlist.aspx",
        "type": "COMPANY_WEBSITE",
        "description": "Bharat Petroleum Corporation Limited tenders for petroleum, refinery, retail.",
        "tags": ["petroleum", "oil", "PSU", "refinery"],
        "states": ["Maharashtra", "Kerala", "Karnataka", "Uttar Pradesh", "Delhi", "Madhya Pradesh"],
        "relevance_base": 70,
    },
    {
        "name": "ONGC Tenders",
        "url": "https://etender.ongc.co.in",
        "type": "COMPANY_WEBSITE",
        "description": "Oil and Natural Gas Corporation tender portal.",
        "tags": ["oil", "gas", "PSU", "offshore", "drilling"],
        "states": ["Gujarat", "Rajasthan", "Assam", "Andhra Pradesh", "Tamil Nadu", "Maharashtra"],
        "relevance_base": 71,
    },
    {
        "name": "NHAI e-Procurement",
        "url": "https://tender.nhai.org",
        "type": "GOVERNMENT",
        "description": "National Highways Authority of India — highway construction and maintenance tenders.",
        "tags": ["highway", "road", "infrastructure", "civil"],
        "states": [],
        "relevance_base": 78,
    },
    {
        "name": "HAL Tenders",
        "url": "https://hal-india.co.in/tenders",
        "type": "COMPANY_WEBSITE",
        "description": "Hindustan Aeronautics Limited tenders — aerospace, defence manufacturing.",
        "tags": ["aerospace", "defence", "manufacturing", "PSU"],
        "states": ["Karnataka", "Uttar Pradesh", "Odisha", "Rajasthan", "Telangana"],
        "relevance_base": 68,
    },
    {
        "name": "SAIL Tenders",
        "url": "https://sailonline.org/tenderss",
        "type": "COMPANY_WEBSITE",
        "description": "Steel Authority of India Limited tenders — steel plants, mining, construction.",
        "tags": ["steel", "manufacturing", "PSU", "mining"],
        "states": ["Jharkhand", "Chhattisgarh", "West Bengal", "Odisha", "Karnataka"],
        "relevance_base": 67,
    },
    {
        "name": "GAIL Tenders",
        "url": "https://www.gail.nic.in/tenders.html",
        "type": "COMPANY_WEBSITE",
        "description": "GAIL India — natural gas pipeline construction and O&M tenders.",
        "tags": ["gas", "pipeline", "energy", "PSU"],
        "states": ["Uttar Pradesh", "Madhya Pradesh", "Gujarat", "Rajasthan", "Andhra Pradesh"],
        "relevance_base": 66,
    },
    {
        "name": "NMDC Tenders",
        "url": "https://www.nmdc.co.in/tenders",
        "type": "COMPANY_WEBSITE",
        "description": "National Mineral Development Corporation — iron ore, mining tenders.",
        "tags": ["mining", "iron ore", "PSU"],
        "states": ["Chhattisgarh", "Karnataka", "Jharkhand", "Telangana"],
        "relevance_base": 65,
    },

    # ── State Government Portals ────────────────────────────────────────────
    {
        "name": "UP e-Procurement Portal",
        "url": "https://etender.up.nic.in",
        "type": "GOVERNMENT",
        "description": "Uttar Pradesh government e-procurement system for PWD, housing, irrigation and all departments.",
        "tags": ["state", "civil", "infrastructure", "UP"],
        "states": ["Uttar Pradesh"],
        "relevance_base": 92,
    },
    {
        "name": "Maharashtra e-Tendering",
        "url": "https://mahatenders.gov.in",
        "type": "GOVERNMENT",
        "description": "Maharashtra state government tender portal — PWD, MSRDC, municipal corporations.",
        "tags": ["state", "civil", "Maharashtra"],
        "states": ["Maharashtra"],
        "relevance_base": 92,
    },
    {
        "name": "Rajasthan e-Procurement",
        "url": "https://sppp.rajasthan.gov.in",
        "type": "GOVERNMENT",
        "description": "Rajasthan government's State Public Procurement Portal for all departments.",
        "tags": ["state", "Rajasthan", "government"],
        "states": ["Rajasthan"],
        "relevance_base": 92,
    },
    {
        "name": "Karnataka e-Procurement",
        "url": "https://eproc.karnataka.gov.in",
        "type": "GOVERNMENT",
        "description": "Karnataka state government e-procurement for PWD, BBMP, water, energy.",
        "tags": ["state", "Karnataka", "civil"],
        "states": ["Karnataka"],
        "relevance_base": 92,
    },
    {
        "name": "Tamil Nadu e-Procurement",
        "url": "https://tntenders.gov.in",
        "type": "GOVERNMENT",
        "description": "Tamil Nadu government procurement portal covering all state departments.",
        "tags": ["state", "Tamil Nadu", "government"],
        "states": ["Tamil Nadu"],
        "relevance_base": 92,
    },
    {
        "name": "Gujarat e-Procurement",
        "url": "https://tender.gujarat.gov.in",
        "type": "GOVERNMENT",
        "description": "Gujarat state e-tendering for all government departments and corporations.",
        "tags": ["state", "Gujarat", "government"],
        "states": ["Gujarat"],
        "relevance_base": 92,
    },
    {
        "name": "Telangana e-Procurement",
        "url": "https://tender.telangana.gov.in",
        "type": "GOVERNMENT",
        "description": "Telangana state e-procurement covering TSRTC, HMDA, housing and all departments.",
        "tags": ["state", "Telangana", "government"],
        "states": ["Telangana"],
        "relevance_base": 92,
    },
    {
        "name": "Andhra Pradesh e-Procurement",
        "url": "https://tender.apeprocurement.gov.in",
        "type": "GOVERNMENT",
        "description": "Andhra Pradesh government procurement portal.",
        "tags": ["state", "Andhra Pradesh", "government"],
        "states": ["Andhra Pradesh"],
        "relevance_base": 92,
    },
    {
        "name": "Madhya Pradesh e-Procurement",
        "url": "https://eproc.mp.gov.in",
        "type": "GOVERNMENT",
        "description": "Madhya Pradesh state procurement portal for all departments.",
        "tags": ["state", "Madhya Pradesh", "civil"],
        "states": ["Madhya Pradesh"],
        "relevance_base": 92,
    },
    {
        "name": "West Bengal e-Procurement",
        "url": "https://wbtenders.gov.in",
        "type": "GOVERNMENT",
        "description": "West Bengal state tender portal — WBPWD, housing, irrigation departments.",
        "tags": ["state", "West Bengal", "government"],
        "states": ["West Bengal"],
        "relevance_base": 92,
    },
    {
        "name": "Kerala e-Procurement",
        "url": "https://etenders.kerala.gov.in",
        "type": "GOVERNMENT",
        "description": "Kerala Infrastructure and Technology for Education (KITE) and PWD e-procurement.",
        "tags": ["state", "Kerala", "infrastructure"],
        "states": ["Kerala"],
        "relevance_base": 92,
    },
    {
        "name": "Bihar e-Procurement",
        "url": "https://eproc.bihar.gov.in",
        "type": "GOVERNMENT",
        "description": "Bihar government e-procurement — road construction, rural development.",
        "tags": ["state", "Bihar", "civil"],
        "states": ["Bihar"],
        "relevance_base": 92,
    },
    {
        "name": "Odisha e-Procurement",
        "url": "https://tendersodisha.gov.in",
        "type": "GOVERNMENT",
        "description": "Odisha state procurement portal for PWD, housing, water resources.",
        "tags": ["state", "Odisha", "government"],
        "states": ["Odisha"],
        "relevance_base": 92,
    },
    {
        "name": "Punjab e-Procurement",
        "url": "https://eproc.punjab.gov.in",
        "type": "GOVERNMENT",
        "description": "Punjab state e-tendering for all government departments.",
        "tags": ["state", "Punjab", "government"],
        "states": ["Punjab"],
        "relevance_base": 92,
    },
    {
        "name": "Haryana e-Procurement",
        "url": "https://etenders.hry.nic.in",
        "type": "GOVERNMENT",
        "description": "Haryana government e-procurement for PWD, HUDA, HSIIDC and departments.",
        "tags": ["state", "Haryana", "civil"],
        "states": ["Haryana"],
        "relevance_base": 92,
    },
    {
        "name": "Assam e-Procurement",
        "url": "https://assamtenders.gov.in",
        "type": "GOVERNMENT",
        "description": "Assam government tender portal for infrastructure and development.",
        "tags": ["state", "Assam", "Northeast"],
        "states": ["Assam"],
        "relevance_base": 92,
    },
    {
        "name": "Jharkhand e-Procurement",
        "url": "https://jharkhandtenders.gov.in",
        "type": "GOVERNMENT",
        "description": "Jharkhand state procurement for mining, roads, housing.",
        "tags": ["state", "Jharkhand", "mining", "civil"],
        "states": ["Jharkhand"],
        "relevance_base": 92,
    },
    {
        "name": "Chhattisgarh e-Procurement",
        "url": "https://eproc.cgstate.gov.in",
        "type": "GOVERNMENT",
        "description": "Chhattisgarh state e-procurement for all departments.",
        "tags": ["state", "Chhattisgarh", "mining"],
        "states": ["Chhattisgarh"],
        "relevance_base": 92,
    },
    {
        "name": "Uttarakhand e-Procurement",
        "url": "https://uktenders.gov.in",
        "type": "GOVERNMENT",
        "description": "Uttarakhand government procurement portal.",
        "tags": ["state", "Uttarakhand", "infrastructure"],
        "states": ["Uttarakhand"],
        "relevance_base": 92,
    },
    {
        "name": "Himachal Pradesh e-Procurement",
        "url": "https://hptenders.gov.in",
        "type": "GOVERNMENT",
        "description": "Himachal Pradesh state procurement for roads, power, tourism.",
        "tags": ["state", "Himachal Pradesh", "infrastructure"],
        "states": ["Himachal Pradesh"],
        "relevance_base": 92,
    },
    {
        "name": "Goa e-Procurement",
        "url": "https://goatenders.gov.in",
        "type": "GOVERNMENT",
        "description": "Goa state government tender portal.",
        "tags": ["state", "Goa", "coastal"],
        "states": ["Goa"],
        "relevance_base": 92,
    },
    {
        "name": "Delhi e-Procurement",
        "url": "https://govtprocurement.delhi.gov.in",
        "type": "GOVERNMENT",
        "description": "Delhi government procurement portal — PWD, DDA, DUSIB, MCD tenders.",
        "tags": ["state", "Delhi", "urban", "civil"],
        "states": ["Delhi"],
        "relevance_base": 92,
    },

    # ── Healthcare / Hospital Tenders ───────────────────────────────────────
    {
        "name": "AIIMS Tenders",
        "url": "https://www.aiims.edu/en/notices.html?layout=blog",
        "type": "GOVERNMENT",
        "description": "All India Institute of Medical Sciences tender notices — medical equipment, civil, supplies.",
        "tags": ["hospital", "healthcare", "medical equipment", "AIIMS"],
        "states": [],
        "relevance_base": 70,
    },
    {
        "name": "ESIC e-Procurement",
        "url": "https://esic.nic.in/tenders",
        "type": "GOVERNMENT",
        "description": "Employees' State Insurance Corporation tenders for hospital construction and supplies.",
        "tags": ["hospital", "healthcare", "insurance", "national"],
        "states": [],
        "relevance_base": 68,
    },
    {
        "name": "CGHS Tenders",
        "url": "https://cghs.gov.in/",
        "type": "GOVERNMENT",
        "description": "Central Government Health Scheme tenders for empanelment and medical supplies.",
        "tags": ["healthcare", "government employees", "medical"],
        "states": [],
        "relevance_base": 65,
    },

    # ── Construction / Infrastructure ───────────────────────────────────────
    {
        "name": "CPWD Tenders",
        "url": "https://cpwd.gov.in/tendersnew.aspx",
        "type": "GOVERNMENT",
        "description": "Central Public Works Department — largest civil construction agency in India.",
        "tags": ["civil", "construction", "buildings", "national"],
        "states": [],
        "relevance_base": 82,
    },
    {
        "name": "NBCC Tenders",
        "url": "https://www.nbccindia.com/tenders",
        "type": "COMPANY_WEBSITE",
        "description": "National Buildings Construction Corporation tenders for housing, commercial.",
        "tags": ["construction", "housing", "PSU", "civil"],
        "states": [],
        "relevance_base": 72,
    },
    {
        "name": "HUDCO Tenders",
        "url": "https://www.hudco.org/tenders",
        "type": "GOVERNMENT",
        "description": "Housing and Urban Development Corporation — housing finance and urban tenders.",
        "tags": ["housing", "urban", "civil"],
        "states": [],
        "relevance_base": 68,
    },

    # ── Defence ─────────────────────────────────────────────────────────────
    {
        "name": "Ministry of Defence — Defence Procurement",
        "url": "https://mod.gov.in/deptsindefmin/dfa/tenders",
        "type": "GOVERNMENT",
        "description": "Ministry of Defence tender notices — defence procurement, equipment.",
        "tags": ["defence", "military", "equipment", "national"],
        "states": [],
        "relevance_base": 72,
    },
    {
        "name": "BEL Tenders",
        "url": "https://bel-india.in/tenders",
        "type": "COMPANY_WEBSITE",
        "description": "Bharat Electronics Limited — defence electronics and systems tenders.",
        "tags": ["electronics", "defence", "PSU"],
        "states": ["Karnataka", "Uttar Pradesh", "Telangana", "Pune"],
        "relevance_base": 65,
    },

    # ── Water / Irrigation ──────────────────────────────────────────────────
    {
        "name": "NMCG Tenders (Namami Gange)",
        "url": "https://nmcg.nic.in/tenders.aspx",
        "type": "GOVERNMENT",
        "description": "National Mission for Clean Ganga — river cleaning, sewage treatment plant tenders.",
        "tags": ["water", "environment", "sewage", "Ganga"],
        "states": ["Uttar Pradesh", "Uttarakhand", "Bihar", "West Bengal", "Jharkhand"],
        "relevance_base": 70,
    },

    # ── Private Tender Aggregators ──────────────────────────────────────────
    {
        "name": "Tender Tiger — India's Largest Tender Portal",
        "url": "https://www.tendertiger.com/free_tenders.asp",
        "type": "TENDER_PORTAL",
        "description": "Comprehensive private aggregator of government and private sector tenders across all states and sectors.",
        "tags": ["aggregator", "private", "government", "all sectors", "all states"],
        "states": [],
        "relevance_base": 78,
    },
    {
        "name": "BidAssist — Tender Search Portal",
        "url": "https://www.bidassist.com/tenders",
        "type": "TENDER_PORTAL",
        "description": "AI-powered tender search portal covering 50,000+ tenders daily from all government sources.",
        "tags": ["aggregator", "AI", "all sectors", "all states"],
        "states": [],
        "relevance_base": 76,
    },
    {
        "name": "Tender Detail — Free Government Tenders",
        "url": "https://www.tenderdetail.com/",
        "type": "TENDER_PORTAL",
        "description": "Free tender information service covering all Indian states with category filtering.",
        "tags": ["aggregator", "free", "all states"],
        "states": [],
        "relevance_base": 72,
    },
    {
        "name": "TradeIndia Tenders",
        "url": "https://www.tradeindia.com/tenders/",
        "type": "TENDER_PORTAL",
        "description": "Business-to-business tender listings including private sector and government.",
        "tags": ["B2B", "private", "trade", "all sectors"],
        "states": [],
        "relevance_base": 68,
    },
    {
        "name": "e-Tender India",
        "url": "https://www.etenderindia.com",
        "type": "TENDER_PORTAL",
        "description": "Private tender portal aggregating state and central government tenders by sector.",
        "tags": ["aggregator", "private", "all sectors"],
        "states": [],
        "relevance_base": 65,
    },
]


# ─── Scoring Logic ────────────────────────────────────────────────────────────

def _score_portal(portal: dict, state: str, city: str) -> int:
    """Returns relevance score 0-100 for a portal given a state/city filter."""
    score = portal["relevance_base"]

    portal_states = [s.lower() for s in portal.get("states", [])]
    portal_tags = [t.lower() for t in portal.get("tags", [])]
    state_lower = state.lower()
    city_lower = city.lower() if city else ""

    # All-India portal (empty states list): full base score
    if not portal_states:
        return score

    # State match: boost to near base score
    if state_lower in portal_states:
        return score + 8

    # City match in tags
    if city_lower and city_lower in portal_tags:
        return score + 5

    # State mentioned in tags
    if state_lower in portal_tags:
        return score + 4

    # Non-matching state-specific portal: lower score but still show
    return max(score - 30, 10)


# ─── DuckDuckGo Search ────────────────────────────────────────────────────────

DDG_URL = "https://api.duckduckgo.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TenderMate/1.0; +https://tendermate.app)",
    "Accept": "application/json",
}


async def _ddg_search(query: str, client: httpx.AsyncClient) -> List[dict]:
    """Hits DuckDuckGo Instant Answer API and extracts result URLs."""
    results = []
    try:
        resp = await client.get(
            DDG_URL,
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code != 200:
            return results
        data = resp.json()

        # Extract from RelatedTopics
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict):
                url = topic.get("FirstURL", "")
                text = topic.get("Text", "")
                if url and text and _is_valid_tender_url(url):
                    results.append({"url": url, "title": text[:120]})

        # Abstract URL
        abs_url = data.get("AbstractURL", "")
        abs_text = data.get("AbstractText", "")
        if abs_url and _is_valid_tender_url(abs_url):
            results.append({"url": abs_url, "title": abs_text[:120] or abs_url})

    except Exception as e:
        logger.debug(f"DuckDuckGo search error for '{query}': {e}")
    return results


def _is_valid_tender_url(url: str) -> bool:
    """Filter out social media, Wikipedia, etc."""
    blocklist = ["wikipedia.org", "facebook.com", "twitter.com", "youtube.com",
                 "instagram.com", "linkedin.com", "amazon.com", "flipkart.com"]
    url_lower = url.lower()
    return not any(b in url_lower for b in blocklist) and url.startswith("http")


def _extract_source_name(url: str, title: str) -> str:
    """Derive a clean source name from URL and title."""
    domain = urlparse(url).netloc.replace("www.", "").replace(".gov.in", " (Govt)").replace(".nic.in", " (NIC)").replace(".co.in", "").replace(".com", "")
    if title and len(title) > 5:
        # Truncate title to a reasonable source name
        words = title.split()[:6]
        return " ".join(words)
    return domain.title()


def _infer_source_type(url: str) -> str:
    """Infer SourceType from URL pattern."""
    url_lower = url.lower()
    if any(x in url_lower for x in ["gov.in", "nic.in", "gov.nic", "eprocure", "gem.gov"]):
        return "GOVERNMENT"
    if any(x in url_lower for x in ["tender", "bid", "eproc", "procurement"]):
        return "TENDER_PORTAL"
    if any(x in url_lower for x in ["hospital", "medical", "health", "aiims", "esic"]):
        return "COMPANY_WEBSITE"
    return "OTHER"


# ─── Main Discovery Function ──────────────────────────────────────────────────

async def discover_sources(state: str, city: Optional[str] = None) -> List[dict]:
    """
    Discovers and scores relevant tender sources for the given Indian state/city.
    Returns list of RecommendedSource dicts sorted by relevance score.
    """
    city = city or ""

    # 1. Score all curated portals
    scored_curated = []
    for portal in CURATED_PORTALS:
        score = _score_portal(portal, state, city)
        scored_curated.append({
            "name": portal["name"],
            "url": portal["url"],
            "type": portal["type"],
            "description": portal["description"],
            "tags": portal["tags"],
            "relevance_score": score,
            "is_curated": True,
        })

    # 2. Live DuckDuckGo search for supplemental results
    live_results = []
    location_str = f"{city} {state}".strip() if city else state

    search_queries = [
        f"{location_str} government tender portal e-procurement",
        f"{location_str} tender notice procurement site:gov.in",
        f"{state} state procurement e-tender portal official",
    ]
    if city:
        search_queries.append(f"{city} municipal corporation tender procurement")
        search_queries.append(f"{city} hospital medical equipment tender")

    try:
        transport = httpx.AsyncHTTPTransport(retries=1, verify=True)
        async with httpx.AsyncClient(transport=transport, timeout=12.0, follow_redirects=True) as client:
            tasks = [_ddg_search(q, client) for q in search_queries]
            search_results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls = {p["url"] for p in CURATED_PORTALS}
        for result_list in search_results:
            if isinstance(result_list, Exception):
                continue
            for item in result_list:
                clean_url = item["url"].rstrip("/")
                # Normalize to root domain if it's a deep URL
                parsed = urlparse(clean_url)
                root_url = f"{parsed.scheme}://{parsed.netloc}"
                if root_url not in seen_urls and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    name = _extract_source_name(clean_url, item.get("title", ""))
                    src_type = _infer_source_type(clean_url)
                    live_results.append({
                        "name": name,
                        "url": clean_url,
                        "type": src_type,
                        "description": item.get("title", f"Tender portal found via search for {location_str}"),
                        "tags": [state.lower(), city.lower() if city else "", "search result"],
                        "relevance_score": 55,
                        "is_curated": False,
                    })
    except Exception as e:
        logger.warning(f"Live search error: {e}")

    # 3. Merge and sort
    all_results = scored_curated + live_results
    all_results.sort(key=lambda x: x["relevance_score"], reverse=True)

    # 4. Return top 30 results
    return all_results[:30]

