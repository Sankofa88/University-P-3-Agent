"""
Florida University P3 Opportunity Agent System.

This module powers the FastAPI dashboard. It generates CEO-review documents only;
it does not submit proposals, contact universities, or provide legal advice.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class AgentConfig:
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    model: str = "gpt-4.1"
    temperature: float = 0.2
    output_dir: str = "./outputs"
    ceo_name: str = "CEO"
    use_fixture_data: bool = False
    search_provider: str = "auto"
    tavily_api_key: str = ""
    perplexity_api_key: str = ""
    serpapi_api_key: str = ""
    bing_api_key: str = ""


def load_config(use_fixture_data: bool = False, output_dir: Optional[str] = None) -> AgentConfig:
    return AgentConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
        output_dir=output_dir or os.getenv("P3_OUTPUT_DIR", "./outputs"),
        ceo_name=os.getenv("CEO_NAME", "CEO"),
        use_fixture_data=use_fixture_data,
        search_provider=os.getenv("P3_SEARCH_PROVIDER", "auto").lower(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY", ""),
        serpapi_api_key=os.getenv("SERPAPI_API_KEY", ""),
        bing_api_key=os.getenv("BING_SEARCH_API_KEY", ""),
    )


@dataclass
class Institution:
    name: str
    institution_type: str
    city: str
    county: str
    website: Optional[str] = None


@dataclass
class PropertyCandidate:
    institution_name: str
    owner_name: str
    parcel_id: Optional[str]
    address: Optional[str]
    city: Optional[str]
    county: Optional[str]
    acreage: Optional[float]
    current_use: Optional[str]
    improvement_value: Optional[float]
    land_value: Optional[float]
    building_sqft: Optional[float]
    source_urls: list[str] = field(default_factory=list)
    suspected_underutilization_reason: Optional[str] = None
    possible_uses: list[str] = field(default_factory=list)
    entitlement_notes: Optional[str] = None


@dataclass
class DemandAnalysis:
    institution_name: str
    property_address: Optional[str]
    recommended_use: str
    student_housing_score: float
    faculty_housing_score: float
    student_activity_center_score: float
    demand_summary: str
    key_metrics: dict[str, Any]
    risks: list[str]
    sources: list[str]


@dataclass
class FinancingComplianceAnalysis:
    institution_name: str
    property_address: Optional[str]
    financing_options: list[str]
    likely_p3_structure: str
    required_procurement_steps: list[str]
    unsolicited_proposal_requirements: list[str]
    statutory_notes: list[str]
    university_specific_requirements: list[str]
    risks: list[str]
    sources: list[str]


@dataclass
class OpportunityReport:
    generated_at: str
    institution_name: str
    property_candidate: PropertyCandidate
    demand_analysis: DemandAnalysis
    financing_analysis: FinancingComplianceAnalysis
    overall_score: float
    recommendation: str
    ceo_action_items: list[str]


def _http_json(url: str, method: str = "GET", headers: Optional[dict[str, str]] = None, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"User-Agent": "FloridaUniversityP3Agent/1.0", **(headers or {})}
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


class SearchTool:
    """Search wrapper for Replit secrets: Tavily, Perplexity, SerpAPI, or Bing."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.provider = self._select_provider()

    def _select_provider(self) -> str:
        requested = self.config.search_provider
        if requested != "auto":
            return requested
        if self.config.tavily_api_key:
            return "tavily"
        if self.config.perplexity_api_key:
            return "perplexity"
        if self.config.serpapi_api_key:
            return "serpapi"
        if self.config.bing_api_key:
            return "bing"
        return "none"

    def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        print(f"[SearchTool:{self.provider}] {query}")
        try:
            if self.provider == "tavily" and self.config.tavily_api_key:
                data = _http_json(
                    "https://api.tavily.com/search",
                    method="POST",
                    headers={"Authorization": f"Bearer {self.config.tavily_api_key}"},
                    payload={"query": query, "max_results": max_results, "search_depth": "basic"},
                )
                return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", ""), "source": "tavily"} for r in data.get("results", [])]
            if self.provider == "perplexity" and self.config.perplexity_api_key:
                data = _http_json(
                    "https://api.perplexity.ai/search",
                    method="POST",
                    headers={"Authorization": f"Bearer {self.config.perplexity_api_key}"},
                    payload={"query": query, "max_results": max_results},
                )
                results = data.get("results") or data.get("web_results") or []
                return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "") or r.get("content", ""), "source": "perplexity"} for r in results]
            if self.provider == "serpapi" and self.config.serpapi_api_key:
                params = urllib.parse.urlencode({"engine": "google", "q": query, "api_key": self.config.serpapi_api_key, "num": max_results})
                data = _http_json(f"https://serpapi.com/search.json?{params}")
                return [{"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", ""), "source": "serpapi"} for r in data.get("organic_results", [])]
            if self.provider == "bing" and self.config.bing_api_key:
                params = urllib.parse.urlencode({"q": query, "count": max_results, "mkt": "en-US"})
                data = _http_json(
                    f"https://api.bing.microsoft.com/v7.0/search?{params}",
                    headers={"Ocp-Apim-Subscription-Key": self.config.bing_api_key},
                )
                return [{"title": r.get("name", ""), "url": r.get("url", ""), "snippet": r.get("snippet", ""), "source": "bing"} for r in data.get("webPages", {}).get("value", [])]
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"[SearchTool] search failed: {exc}")
        return []


class DocumentWriter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, filename: str, data: Any) -> str:
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return str(path)

    def write_markdown(self, filename: str, content: str) -> str:
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return str(path)

    def write_csv(self, filename: str, rows: list[dict[str, Any]]) -> str:
        path = self.output_dir / filename
        if not rows:
            path.write_text("", encoding="utf-8")
            return str(path)
        fieldnames = sorted(set().union(*(row.keys() for row in rows)))
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    def write_excel(self, filename: str, rows: list[dict[str, Any]]) -> str:
        path = self.output_dir / filename
        import pandas as pd

        frame = pd.DataFrame(rows)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name="Ranked Sites")
            sheet = writer.sheets["Ranked Sites"]
            sheet.freeze_panes = "A2"
            if not frame.empty:
                sheet.auto_filter.ref = sheet.dimensions
        return str(path)


class LLMClient:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = None
        if config.openai_api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=config.openai_api_key)
            except Exception as exc:
                print(f"[LLMClient] OpenAI unavailable; using fallbacks: {exc}")

    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        if not self.client:
            return "{}" if json_mode else ""
        try:
            response = self.client.responses.create(
                model=self.config.model,
                temperature=self.config.temperature,
                input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            )
            return (getattr(response, "output_text", "") or "").strip()
        except Exception as exc:
            print(f"[LLMClient] call failed; using fallback: {exc}")
            return "{}" if json_mode else ""


class MasterAgent:
    def __init__(self, config: AgentConfig, llm: LLMClient, search_tool: SearchTool, writer: DocumentWriter):
        self.config = config
        self.llm = llm
        self.search_tool = search_tool
        self.writer = writer

    def run(self, institutions: Optional[list[Institution]] = None) -> dict[str, str]:
        print("[MasterAgent] Starting Florida university P3 opportunity workflow.")
        candidates = self._discover_candidates(institutions)
        reports = [self._build_report(candidate) for candidate in candidates]
        ranked = sorted(reports, key=lambda r: r.overall_score, reverse=True)
        rows = [self._flatten(r) for r in ranked]
        return {
            "json_report": self.writer.write_json("university_p3_opportunity_reports.json", [asdict(r) for r in ranked]),
            "csv_ranked_sites": self.writer.write_csv("ranked_university_p3_sites.csv", rows),
            "excel_ranked_sites": self.writer.write_excel("ranked_university_p3_sites.xlsx", rows),
            "ceo_markdown_report": self.writer.write_markdown("CEO_university_p3_opportunity_report.md", self._ceo_report(ranked)),
            "draft_unsolicited_proposal_package": self.writer.write_markdown("draft_unsolicited_proposal_package.md", self._proposal_package(ranked[:5])),
        }

    def _discover_candidates(self, institutions: Optional[list[Institution]]) -> list[PropertyCandidate]:
        if self.config.use_fixture_data:
            return self._fixture_candidates()
        institutions = institutions or [
            Institution("University of Florida", "state university", "Gainesville", "Alachua"),
            Institution("University of Central Florida", "state university", "Orlando", "Orange"),
            Institution("University of South Florida", "state university", "Tampa", "Hillsborough"),
            Institution("Florida International University", "state university", "Miami", "Miami-Dade"),
            Institution("Florida Atlantic University", "state university", "Boca Raton", "Palm Beach"),
        ]
        candidates: list[PropertyCandidate] = []
        for inst in institutions:
            results = []
            for query in [
                f"{inst.name} campus master plan student housing P3",
                f"{inst.name} surplus land foundation real estate Florida",
                f"{inst.name} board of trustees student housing development",
            ]:
                results.extend(self.search_tool.search(query, max_results=5))
            if results:
                candidates.append(
                    PropertyCandidate(
                        institution_name=inst.name,
                        owner_name=f"{inst.name} or affiliate - verify title",
                        parcel_id=None,
                        address="Site identified from public search results - verify parcel",
                        city=inst.city,
                        county=inst.county,
                        acreage=None,
                        current_use="Search-supported potential opportunity; requires parcel diligence",
                        improvement_value=None,
                        land_value=None,
                        building_sqft=None,
                        source_urls=[r.get("url", "") for r in results if r.get("url")][:8],
                        suspected_underutilization_reason="Public search indicates potential campus real estate, housing, or facilities opportunity; verify ownership and use.",
                        possible_uses=["student housing", "faculty/workforce housing", "student activity center"],
                    )
                )
        return candidates or self._fixture_candidates()

    def _fixture_candidates(self) -> list[PropertyCandidate]:
        return [
            PropertyCandidate(
                "University of Florida",
                "University-affiliated owner - verify title",
                "UNVERIFIED-UF-001",
                "Near main campus - exact parcel TBD",
                "Gainesville",
                "Alachua",
                3.2,
                "Surface parking / campus support use - unverified fixture",
                100000,
                900000,
                0,
                ["fixture://manual-diligence-required"],
                "surface parking redevelopment opportunity; sufficient acreage for housing or mixed-use campus support",
                ["student housing", "faculty/workforce housing", "student activity center"],
            ),
            PropertyCandidate(
                "University of Central Florida",
                "University-affiliated owner - verify title",
                "UNVERIFIED-UCF-001",
                "Near campus edge - exact parcel TBD",
                "Orlando",
                "Orange",
                5.0,
                "Vacant or low-intensity land - unverified fixture",
                0,
                1200000,
                0,
                ["fixture://manual-diligence-required"],
                "vacant land; sufficient acreage for housing or mixed-use campus support",
                ["student housing", "faculty/workforce housing", "student activity center"],
            ),
        ]

    def _build_report(self, candidate: PropertyCandidate) -> OpportunityReport:
        demand = DemandAnalysis(
            candidate.institution_name,
            candidate.address,
            "Student housing with potential faculty/workforce component",
            82 if (candidate.acreage or 0) >= 2 else 65,
            72 if (candidate.acreage or 0) >= 2 else 58,
            60,
            "Preliminary fit based on apparent underutilization, campus-support use, and likely housing demand. Requires verified enrollment, rent, transit, zoning, and campus-plan diligence.",
            {"acreage": candidate.acreage, "current_use": candidate.current_use},
            ["Demand evidence requires independent verification", "Parcel capacity and entitlement path require diligence"],
            candidate.source_urls,
        )
        financing = FinancingComplianceAnalysis(
            candidate.institution_name,
            candidate.address,
            ["Private debt and equity", "Long-term ground lease", "Revenue share or ground rent", "Potential tax-exempt/conduit bond financing subject to counsel review"],
            "Ground lease with private design-build-finance-operate-maintain delivery",
            ["Confirm institution-specific unsolicited proposal policy", "Confirm whether Fla. Stat. 255.065 applies", "Confirm board, foundation, or DSO approval path"],
            ["Prepare scope, schedule, financing plan, public benefits, and risk transfer matrix", "Obtain counsel review before submission"],
            ["Fla. Stat. 255.065 may be relevant for qualifying public-purpose P3 projects; counsel must verify applicability."],
            [],
            ["No confirmed submission path yet", "Public records, procurement, title, tax, and bond issues require counsel review"],
            candidate.source_urls,
        )
        score = self._score(candidate, demand, financing)
        return OpportunityReport(
            dt.datetime.now().isoformat(),
            candidate.institution_name,
            candidate,
            demand,
            financing,
            score,
            self._recommendation(score),
            [
                "Confirm title ownership and owner entity.",
                "Confirm official unsolicited proposal process and submission channel.",
                "Have counsel review Fla. Stat. 255.065 and university-specific procurement rules.",
                "Prepare preliminary site yield and financing model.",
                "Do not submit or lobby outside permitted procurement channels.",
            ],
        )

    def _score(self, candidate: PropertyCandidate, demand: DemandAnalysis, financing: FinancingComplianceAnalysis) -> float:
        site = 10 if candidate.source_urls else 0
        if (candidate.acreage or 0) >= 4:
            site += 20
        elif (candidate.acreage or 0) >= 2:
            site += 15
        if candidate.suspected_underutilization_reason:
            site += 15
        demand_score = max(demand.student_housing_score, demand.faculty_housing_score, demand.student_activity_center_score) * 0.4
        finance = 25 if financing.financing_options and financing.unsolicited_proposal_requirements else 10
        risk_penalty = min(len(demand.risks) + len(financing.risks), 10)
        return round(max(0, min(100, site + demand_score + finance - risk_penalty)), 2)

    def _recommendation(self, score: float) -> str:
        if score >= 80:
            return "Priority target: prepare counsel-reviewed unsolicited proposal strategy."
        if score >= 65:
            return "Strong diligence target: verify ownership, procurement path, and campus support."
        if score >= 50:
            return "Monitor / secondary target: needs more evidence before outreach."
        return "Do not pursue until additional facts materially improve."

    def _flatten(self, report: OpportunityReport) -> dict[str, Any]:
        c = report.property_candidate
        d = report.demand_analysis
        f = report.financing_analysis
        return {
            "overall_score": report.overall_score,
            "recommendation": report.recommendation,
            "institution": report.institution_name,
            "owner": c.owner_name,
            "address": c.address,
            "city": c.city,
            "county": c.county,
            "parcel_id": c.parcel_id,
            "acreage": c.acreage,
            "current_use": c.current_use,
            "underutilization_reason": c.suspected_underutilization_reason,
            "recommended_use": d.recommended_use,
            "student_housing_score": d.student_housing_score,
            "faculty_housing_score": d.faculty_housing_score,
            "student_activity_center_score": d.student_activity_center_score,
            "likely_p3_structure": f.likely_p3_structure,
            "top_financing_options": "; ".join(f.financing_options),
            "key_risks": "; ".join((d.risks + f.risks)[:8]),
            "sources": "; ".join(sorted(set(c.source_urls + d.sources + f.sources))),
        }

    def _ceo_report(self, reports: list[OpportunityReport]) -> str:
        lines = [
            "# Florida University P3 Opportunity Report",
            "",
            f"Generated: {dt.datetime.now().isoformat()}",
            "",
            "## Executive Summary",
            "",
            "This report identifies preliminary Florida university P3 opportunities for student housing, faculty/workforce housing, student activity centers, or mixed-use campus-support facilities. All facts require independent verification before outreach or submission.",
            "",
            "## Ranked Opportunity Table",
            "",
            "| Rank | Institution | Address | County | Acres | Recommended Use | Score | Recommendation |",
            "|---:|---|---|---|---:|---|---:|---|",
        ]
        for idx, report in enumerate(reports, 1):
            c = report.property_candidate
            d = report.demand_analysis
            lines.append(f"| {idx} | {report.institution_name} | {c.address or 'TBD'} | {c.county or 'TBD'} | {c.acreage or 'TBD'} | {d.recommended_use} | {report.overall_score} | {report.recommendation} |")
        lines.extend([
            "",
            "## Legal and Procurement Cautions",
            "",
            "- Treat Fla. Stat. 255.065 applicability as a diligence question, not an assumption.",
            "- Confirm institution-specific procurement rules, board approvals, and public records implications.",
            "- Do not submit any proposal until counsel reviews the target entity, project facts, submission path, and required materials.",
            "",
            "## 30-Day Action Plan",
            "",
            "1. Select top targets for title, zoning, entitlement, and procurement diligence.",
            "2. Confirm campus master plan priorities and housing demand indicators.",
            "3. Build preliminary site yield and financing model.",
        ])
        return "\n".join(lines)

    def _proposal_package(self, reports: list[OpportunityReport]) -> str:
        lines = [
            "# Draft Initial Unsolicited Proposal Package",
            "",
            "**Status:** CEO Review Draft Only - Not for Submission",
            "",
            "## Cover Letter",
            "",
            "[Date]",
            "",
            "[University President / Board of Trustees / Procurement Officer / Real Estate Office]",
            "",
            "Re: Preliminary Public-Private Partnership Concept for Campus-Support Development",
            "",
            "Dear [Recipient]:",
            "",
            "[Company Name] is pleased to submit this preliminary, non-binding concept for a potential public-private partnership involving campus-support development. This draft is subject to counsel review, university procurement procedures, board approvals, and definitive documentation.",
            "",
            "## Project Concepts",
        ]
        for report in reports:
            c = report.property_candidate
            d = report.demand_analysis
            f = report.financing_analysis
            lines.extend(["", f"### {report.institution_name} - {c.address or 'Site TBD'}", "", f"- Owner: {c.owner_name}", f"- Parcel ID: {c.parcel_id or 'TBD'}", f"- Acreage: {c.acreage or 'TBD'}", f"- Recommended use: {d.recommended_use}", f"- Preliminary P3 structure: {f.likely_p3_structure}", f"- CEO recommendation: {report.recommendation}"])
        lines.extend([
            "",
            "## Compliance Section",
            "",
            "This proposal is preliminary, non-binding, and subject to Fla. Stat. 255.065 if applicable, university-specific procurement procedures, board approvals, and counsel review.",
            "",
            "## Required Exhibits",
            "",
            "1. Site concept plan",
            "2. Conceptual budget",
            "3. Financing plan",
            "4. Development team qualifications",
            "5. Project schedule",
            "6. Public benefit statement",
            "7. Risk transfer matrix",
            "8. Operations plan",
            "9. Insurance and bonding evidence",
            "10. Legal/procurement compliance memo",
        ])
        return "\n".join(lines)


def build_master(config: AgentConfig) -> MasterAgent:
    return MasterAgent(config, LLMClient(config), SearchTool(config), DocumentWriter(config.output_dir))


def main() -> int:
    parser = argparse.ArgumentParser(description="Florida University P3 Opportunity Agent System")
    parser.add_argument("--fixture", action="store_true", help="Use built-in sample candidates.")
    parser.add_argument("--output-dir", default=None, help="Directory for generated reports.")
    args = parser.parse_args()
    config = load_config(use_fixture_data=args.fixture, output_dir=args.output_dir)
    outputs = build_master(config).run()
    print("\nGenerated files:")
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
