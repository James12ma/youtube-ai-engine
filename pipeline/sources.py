"""Bounded, allowlisted HTTPS source retrieval for public research documents.

No cookies, credentials, automatic redirects or user-supplied arbitrary domains.
Untrusted HTML is parsed as text; scripts, styles and hidden boilerplate omitted.
DNS rebinding remains a general concern for untrusted domains, therefore
explicit trusted-domain allowlisting is required. For stronger network isolation,
run fetching in a restricted network environment.
"""
from __future__ import annotations
import hashlib
import html
import ipaddress
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional, Protocol, Collection
from urllib.parse import urlparse
import httpx
from pipeline.models import Source

MAX_TEXT_CHARS=8_000
MAX_BYTES=150_000
_WS_RE=re.compile(r'\s+')

class SourceFetcher(Protocol):
    def fetch(self, url: str) -> Source: ...

class _TextExtractor(HTMLParser):
    OMIT={'script','style','noscript','svg','nav','footer','form','iframe'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip=0
        self._parts=[]
        self._in_title=False
        self.title=[]
    def handle_starttag(self,tag,attrs):
        if tag in self.OMIT: self._skip+=1
        if tag=='title':self._in_title=True
    def handle_endtag(self,tag):
        if tag in self.OMIT and self._skip:self._skip-=1
        if tag=='title':self._in_title=False
    def handle_data(self,data):
        if self._skip:return
        if self._in_title:self.title.append(data)
        else:self._parts.append(data)
    @property
    def text(self):return ' '.join(self._parts)

def _normalize_text(raw:str)->str:
    return _WS_RE.sub(' ',html.unescape(raw)).strip()[:MAX_TEXT_CHARS]

def _source_id(url:str)->str:
    return hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]

class HttpSourceFetcher:
    """Fetch only explicitly trusted HTTPS hosts. No redirects or URL auth."""
    def __init__(self,*,client:Optional[httpx.Client]=None,
                 allowed_hosts:Optional[Collection[str]]=None,
                 user_agent:str='RouterV3-Research/1.0 (owner-operated)',
                 timeout:float=20.0)->None:
        self._client=client if client is not None else httpx.Client(follow_redirects=False,trust_env=False)
        self._allowed_hosts={h.rstrip('.').lower() for h in (allowed_hosts or ())}
        self._user_agent=user_agent
        self._timeout=timeout

    def fetch(self,url:str)->Source:
        parsed=urlparse(url)
        host=(parsed.hostname or '').rstrip('.').lower()
        if parsed.scheme!='https' or not host or parsed.username or parsed.password or parsed.port not in (None,443):
            raise ValueError('Only safe HTTPS URLs without credentials or custom ports are permitted')
        if host not in self._allowed_hosts:
            raise ValueError('Source hostname is not explicitly allowlisted: '+host)
        try:
            ipaddress.ip_address(host)
            raise ValueError('IP-address source hosts are not permitted')
        except ValueError as exc:
            if str(exc)=='IP-address source hosts are not permitted':raise
        if host=='localhost' or host.endswith('.local') or host.endswith('.internal'):
            raise ValueError('Local/internal hosts are not permitted')
        # Non-following redirects prevents a trusted domain from taking us to
        # file://, http://, private networks, or a non-allowlisted hostname.
        with self._client.stream('GET',url,follow_redirects=False,
                    headers={'User-Agent':self._user_agent,'Accept':'text/html,text/plain'},
                    timeout=self._timeout) as response:
            if 300<=response.status_code<400:
                raise ValueError('Redirects are disabled for research sources')
            if response.status_code>=400:
                raise RuntimeError(f'Fetch failed {response.status_code} for {url}')
            content_type=response.headers.get('content-type','text/html').split(';',1)[0].lower()
            if content_type not in ('text/html','text/plain','application/xhtml+xml'):
                raise ValueError('Unsupported source content type: '+content_type)
            declared=response.headers.get('content-length')
            if declared and declared.isdigit() and int(declared)>MAX_BYTES:
                raise ValueError('Source is too large')
            chunks=[];received=0
            for chunk in response.iter_bytes():
                received+=len(chunk)
                if received>MAX_BYTES:raise ValueError('Source size limit exceeded')
                chunks.append(chunk)
            raw=b''.join(chunks).decode(response.encoding or 'utf-8',errors='replace')
        if content_type=='text/plain':
            title=url;text=_normalize_text(raw)
        else:
            parser=_TextExtractor();parser.feed(raw)
            title=_normalize_text(' '.join(parser.title)) or url
            text=_normalize_text(parser.text)
        if not text:raise ValueError('Empty source text')
        return Source(source_id=_source_id(url),url=url,title=title,retrieved_at=datetime.now(timezone.utc).isoformat(),text=text)
