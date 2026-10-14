"""Conservative provenance hints, NOT a truth oracle."""
from __future__ import annotations
from urllib.parse import urlparse
from ipaddress import ip_address
from .models import CredibilityAssessment

TIER_SCORES = {'A': 0.95, 'B': 0.80, 'C': 0.55, 'D': 0.30, 'suspicious': 0.10}
_A_DOMAINS = frozenset({'who.int', 'worldbank.org', 'oecd.org', 'europa.eu', 'un.org', 'nih.gov', 'cdc.gov', 'bls.gov', 'census.gov', 'nist.gov', 'nber.org'})
_B_DOMAINS = frozenset({'reuters.com', 'apnews.com', 'bbc.com', 'ft.com', 'wsj.com', 'nature.com', 'science.org', 'acm.org', 'ieee.org', 'hbr.org', 'mckinsey.com', 'gartner.com', 'pewresearch.org'})
_C_DOMAINS = frozenset({'medium.com', 'substack.com', 'dev.to', 'blogspot.com', 'wordpress.com', 'ghost.io', 'hashnode.dev', 'notion.site'})
_D_DOMAINS = frozenset({'facebook.com', 'twitter.com', 'x.com', 'reddit.com', 'quora.com', 'pinterest.com', 'tiktok.com', 'instagram.com', 'linkedin.com'})
_SHORTENER_DOMAINS = frozenset({'bit.ly','tinyurl.com','t.co','rebrand.ly'})

def _base_domain(host: str, candidates: set[str] | frozenset[str]) -> str | None:
    for domain in candidates:
        if host == domain or host.endswith('.'+domain):
            return domain
    return None

def independent_domain(url: str) -> str:
    host = urlparse(url).hostname or ''
    host = host.lower().rstrip('.')
    return _base_domain(host, _A_DOMAINS | _B_DOMAINS | _C_DOMAINS | _D_DOMAINS | _SHORTENER_DOMAINS) or host

def assess(source_id: str, url: str) -> CredibilityAssessment:
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower().rstrip('.')
    valid = parsed.scheme == 'https' and bool(host) and not parsed.username and not parsed.password
    try:
        ip_address(host)
        valid = False
    except ValueError:
        pass
    if not valid:
        tier = 'suspicious'; signal = 'unsafe or invalid source URL'
    elif _base_domain(host, _SHORTENER_DOMAINS):
        tier = 'suspicious'; signal = 'URL shortener (destination unknown)'
    elif host.endswith(('.gov', '.mil', '.edu')) or _base_domain(host, _A_DOMAINS):
        tier = 'A'; signal = 'institutional domain heuristic; content still unverified'
    elif _base_domain(host, _B_DOMAINS):
        tier = 'B'; signal = 'known publisher domain heuristic; content still unverified'
    elif _base_domain(host, _D_DOMAINS):
        tier = 'D'; signal = 'user-generated platform'
    elif _base_domain(host, _C_DOMAINS):
        tier = 'C'; signal = 'self-published platform'
    else:
        tier = 'C'; signal = 'unclassified domain; credibility unestablished'
    return CredibilityAssessment(source_id=source_id, domain=host, tier=tier,
                                 score=TIER_SCORES[tier], signals=[signal])

def assess_all(pairs: list[tuple[str,str]]) -> list[CredibilityAssessment]:
    return [assess(sid,url) for sid,url in pairs]
