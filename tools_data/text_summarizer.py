def summarize(text: str, max_sentences: int = 3) -> str:
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if len(s.strip()) > 5]
    return '. '.join(sentences[:max_sentences]) + ('.' if sentences else '')
