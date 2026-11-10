import re
def extract_keywords(text: str) -> list:
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stopwords = {'with', 'this', 'that', 'from', 'have', 'were', 'which'}
    filtered = [w for w in words if w not in stopwords]
    counts = {}
    for w in filtered:
        counts[w] = counts.get(w, 0) + 1
    return sorted(counts.keys(), key=lambda x: counts[x], reverse=True)[:10]
