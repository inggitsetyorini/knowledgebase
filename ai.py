def ai_summary(texts, max_sent=3):
    sentences = []
    for t in texts:
        sentences += t.split(". ")
    sentences = [s.strip() for s in sentences if len(s) > 30]
    sentences.sort(key=len, reverse=True)
    return ". ".join(sentences[:max_sent]) + "."
