#!/usr/bin/env python3
"""
HTML Content Quality Validator - Detects trash/garbage HTML from API fallbacks.

Firecrawl and similar services often return HTML that is structurally "full"
(nav, footer, scripts, cookie banners, ad containers) but contains zero
actual event content. This validator detects such pages so fallbacks can
continue to the next method instead of accepting trash.

Usage: Call validate_html_content(html) after fetching. Returns (is_valid, reason).
"""

import re
from typing import Tuple
from bs4 import BeautifulSoup

# Minimum meaningful content threshold
MIN_BODY_TEXT_LENGTH = 200
MIN_EVENT_KEYWORDS = 2
MAX_BOILERPLATE_RATIO = 0.85

# Keywords that indicate actual event content (not boilerplate)
EVENT_CONTENT_KEYWORDS = [
    "event",
    "party",
    "concert",
    "show",
    "live",
    "venue",
    "ticket",
    "date",
    "time",
    "location",
    "address",
    "performer",
    "artist",
    "dj",
    "set",
    "lineup",
    "doors open",
    "start time",
    "end time",
    "price",
    "free",
    "rsvp",
    "register",
    "buy ticket",
    "get ticket",
    "tonight",
    "tomorrow",
    "friday",
    "saturday",
    "sunday",
    "weekend",
    "club",
    "bar",
    "festival",
    "gig",
    "night",
    "music",
    "dance",
    "underground",
    "warehouse",
    "pop-up",
    "popup",
]

# Boilerplate indicators (nav, footer, ads, legal, cookie banners)
BOILERPLATE_SELECTORS = [
    "nav",
    "footer",
    "header",
    "aside",
    ".cookie-banner",
    ".cookie-consent",
    ".gdpr",
    ".ad",
    ".advertisement",
    ".sponsored",
    ".sidebar",
    ".menu",
    ".navigation",
    ".breadcrumb",
    ".pagination",
    ".search-form",
    ".login-form",
    ".signup",
    ".newsletter",
    ".social-share",
    ".related-posts",
    ".recommended",
    "script",
    "style",
    "noscript",
    "iframe[src*='google-analytics']",
    "iframe[src*='ads']",
    "iframe[src*='doubleclick']",
]


def _get_text_length(soup: BeautifulSoup) -> int:
    """Get length of body text excluding scripts and styles."""
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()
    return len(soup.get_text(separator=" ", strip=True))


def _get_boilerplate_ratio(soup: BeautifulSoup) -> float:
    """Calculate what fraction of text is boilerplate vs content."""
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    body_text = soup.get_text(separator=" ", strip=True)
    if not body_text:
        return 1.0

    boilerplate_text = ""
    for selector in BOILERPLATE_SELECTORS:
        try:
            elements = soup.select(selector)
            for elem in elements:
                boilerplate_text += " " + elem.get_text(separator=" ", strip=True)
        except Exception:
            continue

    boilerplate_text = boilerplate_text.strip()
    if not boilerplate_text:
        return 0.0

    return len(boilerplate_text) / max(len(body_text), 1)


def _count_event_keywords(text: str) -> int:
    """Count how many event-related keywords appear in text."""
    text_lower = text.lower()
    return sum(1 for kw in EVENT_CONTENT_KEYWORDS if kw in text_lower)


def _has_event_structure(soup: BeautifulSoup) -> bool:
    """Check if HTML contains event-like structural elements."""
    event_indicators = [
        ("h1", None),
        ("h2", None),
        ("h3", None),
        ("time", None),
        ("a", {"href": re.compile(r"/event|/e/|/events/|/party|/show")}),
        ("div", {"class": re.compile(r"event|card|listing|venue|ticket", re.I)}),
        ("article", None),
        ("li", {"class": re.compile(r"event|item|card|listing", re.I)}),
    ]

    for tag, attrs in event_indicators:
        try:
            if attrs:
                if soup.find_all(tag, attrs=attrs):
                    return True
            else:
                if soup.find_all(tag):
                    return True
        except Exception:
            continue

    return False


def validate_html_content(html: str) -> Tuple[bool, str]:
    """
    Validate that HTML contains actual event content, not just boilerplate.

    Returns:
        (is_valid, reason) - is_valid=True means content is acceptable
    """
    if not html or not html.strip():
        return False, "empty"

    if len(html.strip()) < 500:
        return False, "too_short"

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return False, "parse_error"

    # Check body text length
    body_text = soup.get_text(separator=" ", strip=True)
    if len(body_text) < MIN_BODY_TEXT_LENGTH:
        return False, f"body_text_too_short({len(body_text)})"

    # Check boilerplate ratio
    boilerplate_ratio = _get_boilerplate_ratio(soup)
    if boilerplate_ratio > MAX_BOILERPLATE_RATIO:
        return False, f"too_much_boilerplate({boilerplate_ratio:.0%})"

    # Check event keywords
    keyword_count = _count_event_keywords(body_text)
    if keyword_count < MIN_EVENT_KEYWORDS:
        return False, f"no_event_keywords({keyword_count})"

    # Check event structure
    if not _has_event_structure(soup):
        return False, "no_event_structure"

    return True, "valid"


def validate_and_clean(html: str) -> Tuple[bool, str]:
    """
    Validate HTML and optionally clean it of boilerplate for parsing.

    Returns:
        (is_valid, cleaned_html_or_reason)
    """
    is_valid, reason = validate_html_content(html)

    if not is_valid:
        return False, reason

    # Clean the HTML of boilerplate for better parsing
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, noscript
        for tag in soup.find_all(["script", "style", "noscript", "iframe"]):
            tag.decompose()

        # Remove common boilerplate containers
        for selector in [
            ".cookie-banner", ".cookie-consent", ".gdpr",
            ".ad", ".advertisement", ".sponsored",
            ".sidebar", ".menu", ".navigation",
            ".social-share", ".newsletter",
        ]:
            try:
                for elem in soup.select(selector):
                    elem.decompose()
            except Exception:
                continue

        return True, str(soup)

    except Exception as e:
        return True, html
