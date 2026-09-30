"""Offline regressions: python -m unittest discover -v."""
import re
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from easydict import EasyDict

from keywords import TOPIC_QUERIES
import utils


def matches(query, title="", abstract=""):
    """Evaluate our AND/OR phrase expressions against small local fixtures."""
    fields = {"ti": title.lower(), "abs": abstract.lower()}
    expression = re.sub(
        r'(ti|abs):"([^"]+)"',
        lambda match: str(bool(re.search(
            r"(?<!\w)" + re.escape(match[2]) + r"(?!\w)", fields[match[1]]))),
        query,
    ).replace(" AND ", " and ").replace(" OR ", " or ")
    return eval(expression, {"__builtins__": {}}, {})


class KeywordTests(unittest.TestCase):
    def test_only_requested_topics(self):
        self.assertEqual(list(TOPIC_QUERIES), [
            "Business Logic Vulnerabilities", "Vulnerability Discovery Agents",
            "Multi-Agent Systems",
        ])

    def test_business_logic_requires_flaw(self):
        query = TOPIC_QUERIES["Business Logic Vulnerabilities"]
        self.assertTrue(matches(query, "Business-logic flaws in web apps"))
        self.assertTrue(matches(query, "Business logic analysis", "Detect vulnerabilities"))
        self.assertFalse(matches(query, "Business logic optimization"))
        self.assertFalse(matches(query, "Memory corruption vulnerabilities"))

    def test_discovery_requires_agents(self):
        query = TOPIC_QUERIES["Vulnerability Discovery Agents"]
        for agent in ["agent", "agents", "agentic"]:
            self.assertTrue(matches(query, "Vulnerability discovery", agent))
        self.assertTrue(matches(query, "Agentic vulnerability detection"))
        self.assertFalse(matches(query, "Vulnerability discovery with static analysis"))
        self.assertFalse(matches(query, "Agents for business process optimization"))
        self.assertFalse(matches(query, "Agent vulnerabilities and robustness"))

    def test_multi_agent_variants(self):
        query = TOPIC_QUERIES["Multi-Agent Systems"]
        for variant in ["Multi-Agent", "multi agent", "multiagent"]:
            self.assertTrue(matches(query, variant + " collaboration"))
        self.assertFalse(matches(query, "Single agent reinforcement learning"))

    def test_removed_topics_do_not_match_alone(self):
        for title in ["Binary Code Similarity Detection", "LLM for Security", "Decompile", "Compiler"]:
            self.assertFalse(any(matches(query, title) for query in TOPIC_QUERIES.values()))

    @patch("utils.feedparser.parse", return_value=EasyDict(entries=[]))
    @patch("utils.urllib.request.urlopen")
    def test_query_is_encoded_without_quoting_whole_expression(self, urlopen, parse):
        urlopen.return_value.read.return_value = b"<feed/>"
        for query in TOPIC_QUERIES.values():
            utils.request_paper_with_arXiv_api("label", 100, search_query=query)
            url = urlparse(urlopen.call_args.args[0])
            params = parse_qs(url.query)
            self.assertEqual(url.scheme, "https")
            self.assertEqual(params["search_query"], [query])
            self.assertEqual(params["max_results"], ["100"])
            self.assertEqual(params["sortBy"], ["lastUpdatedDate"])

    @patch("utils.feedparser.parse", return_value=EasyDict(entries=[]))
    @patch("utils.urllib.request.urlopen")
    def test_legacy_keyword_call(self, urlopen, parse):
        urlopen.return_value.read.return_value = b"<feed/>"
        utils.request_paper_with_arXiv_api("legacy phrase", 5, "AND")
        params = parse_qs(urlparse(urlopen.call_args.args[0]).query)
        self.assertEqual(params["search_query"], ['ti:"legacy phrase" AND abs:"legacy phrase"'])

    @patch("utils.request_paper_with_arXiv_api")
    def test_query_reaches_api_and_category_filter_is_preserved(self, request):
        request.return_value = [
            EasyDict(Title="CS paper", Tags=["cs.CR"]),
            EasyDict(Title="Stats paper", Tags=["stat.ML"]),
            EasyDict(Title="Physics paper", Tags=["physics.gen-ph"]),
        ]
        query = TOPIC_QUERIES["Vulnerability Discovery Agents"]
        result = utils.get_daily_papers_by_keyword_with_retries(
            "label", ["Title"], 100, search_query=query)
        self.assertEqual(result, [{"Title": "CS paper"}, {"Title": "Stats paper"}])
        request.assert_called_once_with("label", 100, "OR", search_query=query)

    def test_main_writes_exactly_three_sections(self):
        import os
        script = Path(__file__).with_name("main.py")
        paper = {"Title": "Paper", "Link": "https://arxiv.org/abs/example",
                 "Abstract": "Abstract", "Date": "2026-09-30T00:00:00Z", "Comment": ""}
        previous_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                Path(".github").mkdir()
                Path("README.md").write_text("Last update: 2026-09-29\n")
                Path(".github/ISSUE_TEMPLATE.md").write_text("Old issue template")
                with patch("utils.get_daily_papers_by_keyword_with_retries", return_value=[paper]) as get, patch("time.sleep"):
                    runpy.run_path(str(script))
                self.assertEqual(get.call_count, 3)
                for call, (label, query) in zip(get.call_args_list, TOPIC_QUERIES.items()):
                    self.assertEqual(call.args[0], label)
                    self.assertEqual(call.kwargs, {"search_query": query})
                for filename in ["README.md", ".github/ISSUE_TEMPLATE.md"]:
                    headings = re.findall(r"^## (.+)$", Path(filename).read_text(), re.M)
                    self.assertEqual(headings, list(TOPIC_QUERIES))
            finally:
                os.chdir(previous_directory)


if __name__ == "__main__":
    unittest.main()
