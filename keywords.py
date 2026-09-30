"""The three requested topics, searched only in arXiv titles and abstracts."""


def any_phrase(*phrases):
    """Match any complete phrase in either the title or the abstract."""
    return "(" + " OR ".join(
        '(ti:"{0}" OR abs:"{0}")'.format(phrase) for phrase in phrases
    ) + ")"


TOPIC_QUERIES = {
    # 业务逻辑漏洞: require business logic plus a security flaw term.
    "Business Logic Vulnerabilities": (
        any_phrase("business logic", "business-logic")
        + " AND "
        + any_phrase("vulnerability", "vulnerabilities", "flaw", "flaws", "bug", "bugs")
    ),
    # 漏洞挖掘 agent: neither a vulnerability nor an agent alone is sufficient.
    "Vulnerability Discovery Agents": (
        any_phrase(
            "vulnerability discovery", "vulnerability detection",
            "vulnerability finding", "vulnerability mining",
            "vulnerability hunting", "bug hunting", "bug finding",
        )
        + " AND "
        + any_phrase("agent", "agents", "agentic")
    ),
    # 多 agent: include common hyphenated, spaced and joined spellings.
    "Multi-Agent Systems": any_phrase("multi-agent", "multi agent", "multiagent"),
}
