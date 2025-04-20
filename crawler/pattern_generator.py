import json
import re
import yaml
from urllib.parse import urlparse
from collections import Counter

def tokenize_path(url):
    path = urlparse(url).path
    return [segment for segment in path.strip("/").split("/") if segment]

def generalize_urls(urls):
    filtered = [url for url in urls if len(tokenize_path(url)) >= 2]
    tokenized = [tokenize_path(url) for url in filtered]
    if not tokenized:
        return ""

    max_len = max(len(toks) for toks in tokenized)
    pattern_parts = []
    for i in range(max_len):
        segment_counts = Counter()
        for tokens in tokenized:
            if i < len(tokens):
                segment_counts[tokens[i]] += 1
        if segment_counts:
            most_common, _ = segment_counts.most_common(1)[0]
            wildcard = most_common if len(segment_counts) == 1 else "*"
            pattern_parts.append(wildcard)

    return "/" + "/".join(pattern_parts)

def suggest_patterns(data):
    suggestions = {}
    for domain, urls in data.items():
        if not urls:
            continue
        pattern = generalize_urls(list(urls))
        if pattern:
            suggestions[domain] = pattern

    return suggestions