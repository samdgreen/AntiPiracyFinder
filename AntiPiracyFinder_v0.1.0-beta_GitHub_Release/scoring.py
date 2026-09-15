from config import OFFICIAL_DOMAINS
from utils import in_domains

HINTS = ("最新章节","全文","免费阅读","无弹窗","章节列表","目录","txt","小说阅读")

def score(book, author, title, snippet, domain):
    text = f"{title} {snippet}".lower()
    if domain and in_domains(domain, OFFICIAL_DOMAINS):
        return "OFFICIAL", -100
    s = 0
    if book.lower() in text: s += 40
    if author and author.lower() in text: s += 25
    s += min(30, sum(10 for h in HINTS if h.lower() in text))
    return "DISCOVERED", s
