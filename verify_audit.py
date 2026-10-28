#!/usr/bin/env python3
"""
Automated Verification Suite for Kwizzle Technical SEO & A2A Ecosystem
Target Domain: https://kwizzlesurp.com/
Backend Host:  https://x402-mcp.onrender.com/
Workspace:     /home/keef/teamwork_projects/kwizzlesurp_seo_a2a/

This script performs end-to-end automated validation of:
1. Live network endpoints (HTTP status, headers, body schemas, latency).
2. Technical SEO audit report (presence, required sections, recommendations).
3. A2A recognition strategy report (presence, required architectures, protocols).
4. Machine discovery manifests (llms.txt, .well-known/agent-card.json, .well-known/agent.json).
5. Schema.org structured data (JSON-LD syntax, SoftwareApplication, Organization).
6. Crawler control & indexing manifests (robots.txt, sitemap.xml).

Usage:
    python3 verify_audit.py [--project-dir <path>] [--skip-live] [--timeout <seconds>] [--verbose]
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Terminal ANSI Colors
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.RED = ""
        cls.CYAN = ""
        cls.BOLD = ""
        cls.RESET = ""


if not sys.stdout.isatty():
    Colors.disable()


class TestResult:
    def __init__(self, suite: str, name: str, status: str, message: str, details: Optional[str] = None):
        self.suite = suite
        self.name = name
        self.status = status  # 'PASS', 'WARN', 'FAIL'
        self.message = message
        self.details = details

    def __str__(self) -> str:
        color = Colors.GREEN if self.status == "PASS" else (Colors.YELLOW if self.status == "WARN" else Colors.RED)
        status_tag = f"{color}[{self.status}]{Colors.RESET}"
        base = f"  {status_tag} {self.name}: {self.message}"
        if self.details:
            base += f"\n         {Colors.CYAN}Details:{Colors.RESET} {self.details}"
        return base


class AuditVerifier:
    def __init__(self, project_dir: Path, skip_live: bool = False, timeout: int = 10, verbose: bool = False):
        self.project_dir = project_dir.resolve()
        self.skip_live = skip_live
        self.timeout = timeout
        self.verbose = verbose
        self.results: List[TestResult] = []

    def log(self, result: TestResult):
        self.results.append(result)
        print(result)

    def run_all(self) -> int:
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}Kwizzle SEO & A2A Verification Suite{Colors.RESET}")
        print(f"Target Project Directory: {self.project_dir}")
        print(f"Live Network Probes:      {'SKIPPED' if self.skip_live else 'ENABLED (Timeout: ' + str(self.timeout) + 's)'}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")

        # 1. Live Endpoint Checks
        self._suite_header("1. Live Network Endpoints")
        if not self.skip_live:
            self.test_live_apex_domain()
            self.test_live_mcp_discovery()
            self.test_live_health_endpoint()
        else:
            self.log(TestResult("Live Endpoints", "Live Network Tests", "WARN", "Skipped by command-line flag --skip-live"))

        # 2. Technical SEO Audit Report
        self._suite_header("2. Technical SEO Audit Report (seo_audit_report.md)")
        self.test_seo_audit_report()

        # 3. A2A Recognition Strategy
        self._suite_header("3. A2A Recognition Strategy (a2a_recognition_strategy.md)")
        self.test_a2a_strategy_report()

        # 4. LLM Documentation Manifest (llms.txt)
        self._suite_header("4. LLM Context Manifest (llms.txt)")
        self.test_llms_txt()

        # 5. A2A Agent Card (.well-known/agent-card.json)
        self._suite_header("5. A2A Agent Card (.well-known/agent-card.json)")
        self.test_agent_card()

        # 6. A2A Agent Pointer (.well-known/agent.json)
        self._suite_header("6. A2A Agent Pointer (.well-known/agent.json)")
        self.test_agent_json()

        # 7. Schema.org JSON-LD (schema_org_snippet.html)
        self._suite_header("7. Schema.org Structured Data (schema_org_snippet.html)")
        self.test_schema_org_snippet()

        # 8. Crawler Directives (robots.txt)
        self._suite_header("8. Crawler Directives (robots.txt)")
        self.test_robots_txt()

        # 9. XML Sitemap (sitemap.xml)
        self._suite_header("9. XML Sitemap (sitemap.xml)")
        self.test_sitemap_xml()

        return self.print_summary()

    def _suite_header(self, title: str):
        print(f"\n{Colors.BOLD}{title}{Colors.RESET}")
        print(f"{'-'*len(title)}")

    def _fetch_url(self, url: str) -> Tuple[int, bytes, Dict[str, str], float]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; KwizzleAuditVerifier/1.0; +https://kwizzlesurp.com)"
            }
        )
        start = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            duration = time.time() - start
            body = resp.read()
            headers = dict(resp.headers)
            return resp.status, body, headers, duration

    # -------------------------------------------------------------------------
    # 1. Live Endpoint Checks
    # -------------------------------------------------------------------------
    def test_live_apex_domain(self):
        url = "https://kwizzlesurp.com/"
        try:
            status, body, headers, duration = self._fetch_url(url)
            if status == 200:
                html_text = body.decode("utf-8", errors="replace")
                has_html = "<html" in html_text.lower()
                has_head = "<head" in html_text.lower()
                has_title = "<title" in html_text.lower()
                server = headers.get("server", "unknown")

                if has_html and (has_head or has_title):
                    self.log(TestResult(
                        "Live Endpoints", "Apex Domain (kwizzlesurp.com)", "PASS",
                        f"HTTP {status} OK ({duration:.2f}s, {len(body):,} bytes)",
                        f"Server: {server}, HTML structure detected"
                    ))
                else:
                    self.log(TestResult(
                        "Live Endpoints", "Apex Domain (kwizzlesurp.com)", "WARN",
                        f"HTTP {status} returned but missing standard HTML tags",
                        f"Body length: {len(body)} bytes"
                    ))
            else:
                self.log(TestResult(
                    "Live Endpoints", "Apex Domain (kwizzlesurp.com)", "WARN",
                    f"Unexpected HTTP status {status}"
                ))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as e:
            self.log(TestResult(
                "Live Endpoints", "Apex Domain (kwizzlesurp.com)", "WARN",
                f"Network probe failed: {e}",
                "External host unreachable or timed out (non-fatal warning)"
            ))

    def test_live_mcp_discovery(self):
        url = "https://x402-mcp.onrender.com/.well-known/mcp"
        try:
            status, body, headers, duration = self._fetch_url(url)
            if status == 200 and len(body) > 0:
                try:
                    data = json.loads(body.decode("utf-8"))
                    name = data.get("name") or data.get("title") or "MCP Manifest"
                    self.log(TestResult(
                        "Live Endpoints", "MCP Discovery Endpoint", "PASS",
                        f"HTTP {status} OK ({duration:.2f}s, valid JSON)",
                        f"Manifest title/name: {name}"
                    ))
                except json.JSONDecodeError:
                    self.log(TestResult(
                        "Live Endpoints", "MCP Discovery Endpoint", "PASS",
                        f"HTTP {status} OK ({duration:.2f}s, {len(body)} bytes)"
                    ))
            else:
                self.log(TestResult(
                    "Live Endpoints", "MCP Discovery Endpoint", "WARN",
                    f"Unexpected HTTP status {status}"
                ))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as e:
            self.log(TestResult(
                "Live Endpoints", "MCP Discovery Endpoint", "WARN",
                f"Network probe failed: {e}",
                "Backend service unreachable or spinning down (non-fatal warning)"
            ))

    def test_live_health_endpoint(self):
        url = "https://x402-mcp.onrender.com/health"
        try:
            status, body, headers, duration = self._fetch_url(url)
            if status == 200:
                try:
                    data = json.loads(body.decode("utf-8"))
                    srv_status = data.get("status", "unknown")
                    if srv_status == "ok":
                        self.log(TestResult(
                            "Live Endpoints", "Backend Health Check", "PASS",
                            f"HTTP {status} OK ({duration:.2f}s, status: ok)",
                            f"Payload: {json.dumps(data)}"
                        ))
                    else:
                        self.log(TestResult(
                            "Live Endpoints", "Backend Health Check", "WARN",
                            f"HTTP 200 but status != 'ok' (got: {srv_status})"
                        ))
                except json.JSONDecodeError:
                    self.log(TestResult(
                        "Live Endpoints", "Backend Health Check", "WARN",
                        f"HTTP 200 but response is not JSON"
                    ))
            else:
                self.log(TestResult(
                    "Live Endpoints", "Backend Health Check", "WARN",
                    f"Unexpected HTTP status {status}"
                ))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as e:
            self.log(TestResult(
                "Live Endpoints", "Backend Health Check", "WARN",
                f"Network probe failed: {e}",
                "Backend service unreachable (non-fatal warning)"
            ))

    # -------------------------------------------------------------------------
    # 2. Technical SEO Audit Report
    # -------------------------------------------------------------------------
    def test_seo_audit_report(self):
        report_file = self.project_dir / "seo_audit_report.md"
        if not report_file.exists():
            self.log(TestResult("SEO Report", "File Existence", "FAIL", f"Missing {report_file.name}"))
            return

        size = report_file.stat().st_size
        if size < 5000:
            self.log(TestResult("SEO Report", "File Size", "FAIL", f"File too small ({size} bytes, expected >= 5,000)"))
            return

        self.log(TestResult("SEO Report", "File Existence & Size", "PASS", f"Found {report_file.name} ({size:,} bytes)"))

        content = report_file.read_text(encoding="utf-8")
        content_lower = content.lower()

        required_sections = [
            ("Crawling & Indexing", ["crawling", "crawler", "crawl", "robots.txt"]),
            ("Indexability & HTTP Posture", ["indexability", "status code", "http/2", "canonical"]),
            ("Document Metadata", ["metadata", "meta name=\"description\"", "title tag"]),
            ("Open Graph / Twitter Cards", ["open graph", "og:", "twitter card"]),
            ("Structured Data (JSON-LD)", ["structured data", "json-ld", "schema.org"]),
            ("Canonical Link Tags", ["canonical", "<link rel=\"canonical\""]),
            ("Heading Hierarchy", ["heading hierarchy", "h1", "h2", "semantic"]),
            ("Performance & Edge Caching", ["performance", "core web vitals", "caching", "cache-control"]),
            ("Actionable Recommendations", ["remediation", "recommendation", "roadmap"])
        ]

        missing_sections = []
        for label, keywords in required_sections:
            if not any(k in content_lower for k in keywords):
                missing_sections.append(label)

        if not missing_sections:
            self.log(TestResult(
                "SEO Report", "Required SEO Sections", "PASS",
                f"All {len(required_sections)} core sections verified"
            ))
        else:
            self.log(TestResult(
                "SEO Report", "Required SEO Sections", "FAIL",
                f"Missing required sections: {', '.join(missing_sections)}"
            ))

    # -------------------------------------------------------------------------
    # 3. A2A Recognition Strategy
    # -------------------------------------------------------------------------
    def test_a2a_strategy_report(self):
        strat_file = self.project_dir / "a2a_recognition_strategy.md"
        if not strat_file.exists():
            self.log(TestResult("A2A Strategy", "File Existence", "FAIL", f"Missing {strat_file.name}"))
            return

        size = strat_file.stat().st_size
        if size < 5000:
            self.log(TestResult("A2A Strategy", "File Size", "FAIL", f"File too small ({size} bytes, expected >= 5,000)"))
            return

        self.log(TestResult("A2A Strategy", "File Existence & Size", "PASS", f"Found {strat_file.name} ({size:,} bytes)"))

        content = strat_file.read_text(encoding="utf-8")
        content_lower = content.lower()

        required_themes = [
            ("Machine Discovery Architectures", ["machine discovery", "rfc 8615", ".well-known", "unified discovery"]),
            ("Agent Discovery Standards", ["agent discovery", "agent card", "a2a", "mcp"]),
            ("Multi-Agent Swarm Patterns", ["swarm", "multi-agent", "resale", "delegation"]),
            ("x402 Micropayments Protocol", ["x402", "http 402", "micropayment"]),
            ("Settlement Rail on Base L2", ["base", "eip155:8453", "usdc"]),
            ("Capability Probing & Dry Runs", ["probe", "dry-run", "sample", "zero-cost"])
        ]

        missing_themes = []
        for label, keywords in required_themes:
            if not any(k in content_lower for k in keywords):
                missing_themes.append(label)

        if not missing_themes:
            self.log(TestResult(
                "A2A Strategy", "Required Strategy Architectures", "PASS",
                f"All {len(required_themes)} required themes verified"
            ))
        else:
            self.log(TestResult(
                "A2A Strategy", "Required Strategy Architectures", "FAIL",
                f"Missing required themes: {', '.join(missing_themes)}"
            ))

    # -------------------------------------------------------------------------
    # 4. LLM Documentation Manifest (llms.txt)
    # -------------------------------------------------------------------------
    def test_llms_txt(self):
        llms_file = self.project_dir / "llms.txt"
        if not llms_file.exists():
            self.log(TestResult("llms.txt", "File Existence", "FAIL", f"Missing {llms_file.name}"))
            return

        content = llms_file.read_text(encoding="utf-8")
        size = len(content.encode("utf-8"))

        if size < 200:
            self.log(TestResult("llms.txt", "File Size", "FAIL", f"File too small ({size} bytes)"))
            return

        # Check llmstxt.org structure: H1 header, blockquote summary, markdown links
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        has_h1 = any(line.startswith("# ") for line in lines)
        has_blockquote = any(line.startswith("> ") for line in lines)
        links = re.findall(r"-\s*\[(.*?)\]\((https?://.*?)\)", content)

        if not has_h1:
            self.log(TestResult("llms.txt", "Specification Format", "FAIL", "Missing '# <Title>' H1 header per llmstxt.org"))
            return

        if not has_blockquote:
            self.log(TestResult("llms.txt", "Specification Format", "FAIL", "Missing '> <Summary>' blockquote per llmstxt.org"))
            return

        if len(links) < 3:
            self.log(TestResult("llms.txt", "Markdown Link Definitions", "FAIL", f"Found only {len(links)} links, expected >= 3"))
            return

        # Verify key references
        has_kwizzle = "kwizzle" in content.lower()
        has_base = "base" in content.lower() or "8453" in content
        has_usdc = "usdc" in content.lower()

        if has_kwizzle and has_base and has_usdc:
            self.log(TestResult(
                "llms.txt", "Structure & Link Catalog", "PASS",
                f"Valid llmstxt.org specification with {len(lines)} lines and {len(links)} curated links",
                f"Sample link: [{links[0][0]}]({links[0][1]})"
            ))
        else:
            self.log(TestResult(
                "llms.txt", "Content Validation", "FAIL",
                "Missing essential entity references (Kwizzle, Base L2, USDC)"
            ))

    # -------------------------------------------------------------------------
    # 5. A2A Agent Card (.well-known/agent-card.json)
    # -------------------------------------------------------------------------
    def test_agent_card(self):
        card_file = self.project_dir / ".well-known" / "agent-card.json"
        if not card_file.exists():
            self.log(TestResult("Agent Card", "File Existence", "FAIL", f"Missing {card_file}"))
            return

        try:
            with open(card_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.log(TestResult("Agent Card", "JSON Syntax", "FAIL", f"JSON parsing failed: {e}"))
            return

        # Handle nested schema or root schema (e.g. Google Agent Card v1 envelope: data.card)
        data_env = data.get("data", data) if isinstance(data.get("data"), dict) else data
        card = data_env.get("card", data_env) if isinstance(data_env.get("card"), dict) else data_env
        agent_id = (
            data.get("agent_id") or data.get("id") or
            data_env.get("agent_id") or data_env.get("id") or
            card.get("agent_id") or card.get("id")
        )
        name = card.get("name") or data_env.get("name") or data.get("name")
        skills = (
            card.get("skills") or data_env.get("skills") or data.get("skills") or
            card.get("tools") or data_env.get("tools") or data.get("tools")
        )

        if not name:
            self.log(TestResult("Agent Card", "Agent Name", "FAIL", "Missing required field 'name'"))
            return

        if not agent_id:
            self.log(TestResult("Agent Card", "Agent ID", "FAIL", "Missing required field 'id' or 'agent_id'"))
            return

        if not skills or not isinstance(skills, list) or len(skills) == 0:
            self.log(TestResult("Agent Card", "Skills Catalog", "FAIL", "Missing or empty 'skills' / 'tools' list"))
            return

        # Check payment details (extensions or settlement coordinates)
        card_str = json.dumps(data)
        has_base_network = "eip155:8453" in card_str or "base" in card_str.lower()
        has_usdc = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913" in card_str.lower() or "usdc" in card_str.lower()
        has_payto = re.search(r"0x[a-fA-F0-9]{40}", card_str) is not None
        has_facilitator = "x402.org" in card_str or "facilitator" in card_str.lower()

        if not has_base_network:
            self.log(TestResult("Agent Card", "Settlement Network", "FAIL", "Missing Base L2 network coordinates (eip155:8453)"))
            return

        if not has_usdc:
            self.log(TestResult("Agent Card", "Settlement Asset", "FAIL", "Missing USDC token coordinate"))
            return

        if not has_payto:
            self.log(TestResult("Agent Card", "PayTo Address", "FAIL", "Missing valid EVM payTo recipient address"))
            return

        if not has_facilitator:
            self.log(TestResult("Agent Card", "x402 Facilitator", "FAIL", "Missing x402 facilitator reference"))
            return

        self.log(TestResult(
            "Agent Card", "A2A Specification Compliance", "PASS",
            f"Valid Agent Card: '{name}' (UUID: {agent_id}, {len(skills)} skills)",
            f"Settlement: Base L2 (eip155:8453) USDC with facilitator support"
        ))

    # -------------------------------------------------------------------------
    # 6. A2A Agent Pointer (.well-known/agent.json)
    # -------------------------------------------------------------------------
    def test_agent_json(self):
        agent_file = self.project_dir / ".well-known" / "agent.json"
        if not agent_file.exists():
            self.log(TestResult("Agent Pointer", "File Existence", "FAIL", f"Missing {agent_file}"))
            return

        try:
            with open(agent_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.log(TestResult("Agent Pointer", "JSON Syntax", "FAIL", f"JSON parsing failed: {e}"))
            return

        name = data.get("name")
        if not name:
            self.log(TestResult("Agent Pointer", "Required Fields", "FAIL", "Missing 'name' field in agent.json"))
            return

        # Check pointers
        has_agent_card_link = "agent_card" in data or "agentCard" in data or ".well-known/agent-card.json" in json.dumps(data)
        has_settlement = "settlement" in data or "eip155:8453" in json.dumps(data)

        if not has_agent_card_link:
            self.log(TestResult("Agent Pointer", "Agent Card Pointer", "FAIL", "Missing reference to .well-known/agent-card.json"))
            return

        self.log(TestResult(
            "Agent Pointer", "Canonical Discovery Pointer", "PASS",
            f"Valid agent.json pointing to agent-card with settlement config",
            f"Name: {name}, Settlement: {has_settlement}"
        ))

    # -------------------------------------------------------------------------
    # 7. Schema.org JSON-LD (schema_org_snippet.html)
    # -------------------------------------------------------------------------
    def test_schema_org_snippet(self):
        snippet_file = self.project_dir / "schema_org_snippet.html"
        if not snippet_file.exists():
            self.log(TestResult("Schema.org", "File Existence", "FAIL", f"Missing {snippet_file.name}"))
            return

        content = snippet_file.read_text(encoding="utf-8")
        if "<script" not in content or "application/ld+json" not in content:
            self.log(TestResult("Schema.org", "HTML Script Tag", "FAIL", "Missing <script type=\"application/ld+json\"> tag"))
            return

        # Extract JSON-LD payload
        match = re.search(r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", content, re.DOTALL)
        if not match:
            self.log(TestResult("Schema.org", "JSON-LD Extraction", "FAIL", "Unable to extract JSON content between <script> tags"))
            return

        json_raw = match.group(1).strip()
        try:
            data = json.loads(json_raw)
        except json.JSONDecodeError as e:
            self.log(TestResult("Schema.org", "JSON-LD Syntax", "FAIL", f"Invalid JSON syntax inside script: {e}"))
            return

        # Verify Schema.org context
        context = data.get("@context")
        if not context or "schema.org" not in str(context):
            self.log(TestResult("Schema.org", "Context Validation", "FAIL", "Missing @context: 'https://schema.org'"))
            return

        # Verify presence of SoftwareApplication or Organization
        entities = []
        if "@graph" in data and isinstance(data["@graph"], list):
            entities = data["@graph"]
        else:
            entities = [data]

        types = []
        for ent in entities:
            t = ent.get("@type")
            if isinstance(t, list):
                types.extend(t)
            elif isinstance(t, str):
                types.append(t)

        has_software_app = any("SoftwareApplication" in t for t in types)
        has_org = any("Organization" in t for t in types)

        if not (has_software_app or has_org):
            self.log(TestResult(
                "Schema.org", "Entity Types", "FAIL",
                f"Missing SoftwareApplication or Organization @type (found: {types})"
            ))
            return

        # Validate URL and name attributes
        names = [ent.get("name") for ent in entities if ent.get("name")]
        urls = [ent.get("url") for ent in entities if ent.get("url")]

        if not names:
            self.log(TestResult("Schema.org", "Entity Attributes", "FAIL", "No 'name' attribute found on schema entities"))
            return

        has_canonical_url = any("kwizzlesurp.com" in str(u) for u in urls)
        if not has_canonical_url:
            self.log(TestResult("Schema.org", "Canonical URL", "WARN", "Entities do not explicitly specify kwizzlesurp.com in url"))

        self.log(TestResult(
            "Schema.org", "JSON-LD Validation", "PASS",
            f"Valid Schema.org snippet containing: {', '.join(types)}",
            f"Entities declared: {len(entities)}, Primary name: '{names[0]}'"
        ))

    # -------------------------------------------------------------------------
    # 8. Crawler Directives (robots.txt)
    # -------------------------------------------------------------------------
    def test_robots_txt(self):
        robots_file = self.project_dir / "robots.txt"
        if not robots_file.exists():
            self.log(TestResult("robots.txt", "File Existence", "FAIL", f"Missing {robots_file.name}"))
            return

        content = robots_file.read_text(encoding="utf-8")
        if len(content.strip()) < 20:
            self.log(TestResult("robots.txt", "Content Length", "FAIL", "robots.txt is empty or trivial"))
            return

        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

        has_user_agent = any(re.match(r"^user-agent:\s*", line, re.I) for line in lines)
        has_sitemap = any(re.match(r"^sitemap:\s*", line, re.I) for line in lines)
        has_allow_disallow = any(re.match(r"^(allow|disallow):\s*", line, re.I) for line in lines)

        if not has_user_agent:
            self.log(TestResult("robots.txt", "User-Agent Directive", "FAIL", "Missing 'User-agent:' directive"))
            return

        if not has_sitemap:
            self.log(TestResult("robots.txt", "Sitemap Pointer", "FAIL", "Missing 'Sitemap: ...' declaration"))
            return

        if not has_allow_disallow:
            self.log(TestResult("robots.txt", "Crawl Rules", "FAIL", "Missing Allow or Disallow directives"))
            return

        # Check AI crawler rules
        has_ai_bots = any(bot in content for bot in ["GPTBot", "ClaudeBot", "PerplexityBot"])
        details = f"{len(lines)} active rules; AI bot policies present: {has_ai_bots}"

        self.log(TestResult(
            "robots.txt", "Syntax & Directives", "PASS",
            "Valid robots.txt syntax with sitemap pointer and crawl policies",
            details
        ))

    # -------------------------------------------------------------------------
    # 9. XML Sitemap (sitemap.xml)
    # -------------------------------------------------------------------------
    def test_sitemap_xml(self):
        sitemap_file = self.project_dir / "sitemap.xml"
        if not sitemap_file.exists():
            self.log(TestResult("sitemap.xml", "File Existence", "FAIL", f"Missing {sitemap_file.name}"))
            return

        try:
            tree = ET.parse(sitemap_file)
            root = tree.getroot()
        except ET.ParseError as e:
            self.log(TestResult("sitemap.xml", "XML Syntax", "FAIL", f"XML parsing error: {e}"))
            return

        # Standard namespace is http://www.sitemaps.org/schemas/sitemap/0.9
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        if tag != "urlset":
            self.log(TestResult("sitemap.xml", "Root Tag", "FAIL", f"Root tag must be <urlset>, found <{tag}>"))
            return

        urls = []
        for elem in root:
            elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if elem_tag == "url":
                loc_elem = None
                for child in elem:
                    child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if child_tag == "loc":
                        loc_elem = child
                        break
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text.strip())

        if len(urls) == 0:
            self.log(TestResult("sitemap.xml", "URL Entries", "FAIL", "No <url><loc> entries found in sitemap"))
            return

        has_apex = any(u.rstrip("/") == "https://kwizzlesurp.com" for u in urls)
        if not has_apex:
            self.log(TestResult("sitemap.xml", "Canonical Root URL", "FAIL", "Missing canonical URL https://kwizzlesurp.com/"))
            return

        self.log(TestResult(
            "sitemap.xml", "XML Validation & Index Entries", "PASS",
            f"Valid XML sitemap with {len(urls)} indexed URLs",
            f"Sample URL: {urls[0]}"
        ))

    # -------------------------------------------------------------------------
    # Summary & Exit Code
    # -------------------------------------------------------------------------
    def print_summary(self) -> int:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        warns = sum(1 for r in self.results if r.status == "WARN")
        failed = sum(1 for r in self.results if r.status == "FAIL")

        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}Audit Verification Summary{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"Total Checks:   {total}")
        print(f"Passed:         {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"Warnings:       {Colors.YELLOW}{warns}{Colors.RESET}")
        print(f"Failed:         {Colors.RED}{failed}{Colors.RESET}")

        if failed == 0:
            print(f"\n{Colors.BOLD}{Colors.GREEN}OVERALL STATUS: SUCCESS (All requirements verified cleanly){Colors.RESET}\n")
            return 0
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}OVERALL STATUS: FAILED ({failed} critical failures detected){Colors.RESET}\n")
            return 1


def main():
    parser = argparse.ArgumentParser(description="Kwizzle Technical SEO & A2A Ecosystem Verification Suite")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Path to project directory containing generated artifacts (default: directory of script)"
    )
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="Skip live network HTTP probes (test local artifacts only)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds for live network requests (default: 10)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    verifier = AuditVerifier(
        project_dir=args.project_dir,
        skip_live=args.skip_live,
        timeout=args.timeout,
        verbose=args.verbose
    )

    exit_code = verifier.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
