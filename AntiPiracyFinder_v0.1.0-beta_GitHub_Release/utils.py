import re
from urllib.parse import urlparse, parse_qs, unquote

def clean_text(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def host(url):
    try:
        h = (urlparse(url).hostname or "").lower().rstrip(".")
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""

def domain_matches(h, d):
    h, d = (h or "").lower().rstrip("."), d.lower().rstrip(".")
    return h == d or h.endswith("." + d)

def in_domains(h, domains):
    return any(domain_matches(h, d) for d in domains)

def safe_name(name):
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip() or "result"

def unwrap_url(url):
    try:
        p = urlparse(url)
        qs = parse_qs(p.query)
        for key in ("url", "q", "target", "u", "uddg"):
            if qs.get(key):
                v = unquote(qs[key][0])
                if v.startswith(("http://", "https://")):
                    return v
    except Exception:
        pass
    return url
