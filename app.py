"""
FastAPI dashboard for the Florida University P3 Opportunity Agent System.

Designed for Replit: click Run, open the web preview, and use the dashboard.
The app only generates documents for CEO review. It never submits proposals.
"""

from __future__ import annotations

import os
import zipfile
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from p3_agent_system import build_master, load_config


ROOT = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Florida University P3 Opportunity Agent")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")


def _has_search_key() -> bool:
    return bool(
        os.getenv("TAVILY_API_KEY")
        or os.getenv("PERPLEXITY_API_KEY")
        or os.getenv("SERPAPI_API_KEY")
        or os.getenv("BING_SEARCH_API_KEY")
    )


def _report_dirs() -> list[Path]:
    return sorted([p for p in OUTPUTS_DIR.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)


def _latest_report_dir() -> Optional[Path]:
    reports = _report_dirs()
    return reports[0] if reports else None


def _safe_report_dir(run_id: str) -> Path:
    if not re_match_run_id(run_id):
        raise HTTPException(status_code=404, detail="Report not found")
    report_dir = OUTPUTS_DIR / run_id
    if not report_dir.exists() or not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="Report not found")
    return report_dir


def re_match_run_id(run_id: str) -> bool:
    return bool(run_id) and all(char.isalnum() or char in {"_", "-"} for char in run_id)


def _render_page(body: str, notice: str = "") -> HTMLResponse:
    notice_html = f'<div class="notice">{escape(notice)}</div>' if notice else ""
    return HTMLResponse(
        f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Florida University P3 Agent</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      background: #f7f8fa;
      color: #1f2933;
    }}
    body {{
      margin: 0;
      padding: 32px;
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
      background: white;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 28px;
      box-shadow: 0 10px 28px rgba(31, 41, 51, 0.08);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    h2 {{
      margin-top: 28px;
      font-size: 20px;
    }}
    .subtle {{
      color: #5f6c7b;
      margin: 0 0 24px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 22px 0;
    }}
    button, .button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 0 16px;
      border-radius: 6px;
      border: 1px solid #1f5fbf;
      background: #1f5fbf;
      color: white;
      text-decoration: none;
      font-weight: 700;
      cursor: pointer;
      font-size: 14px;
    }}
    .button.secondary, button.secondary {{
      background: white;
      color: #1f5fbf;
    }}
    .notice {{
      border: 1px solid #f2c46d;
      background: #fff8e8;
      border-radius: 6px;
      padding: 12px 14px;
      margin: 18px 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 10px;
      border-bottom: 1px solid #e4e8ef;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #f1f4f8;
    }}
    code {{
      background: #eef2f7;
      padding: 2px 5px;
      border-radius: 4px;
    }}
    .risk {{
      margin-top: 24px;
      color: #6b3d00;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Florida University P3 Opportunity Agent</h1>
    <p class="subtle">Generate CEO-review reports for university P3 opportunities. This app never submits proposals.</p>
    {notice_html}
    {body}
    <p class="risk">Legal/procurement caution: all outputs are drafts for CEO review only. Counsel must review before any outreach or submission.</p>
  </main>
</body>
</html>
        """
    )


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    latest = _latest_report_dir()
    latest_text = f"Latest report folder: {latest.name}" if latest else "No reports generated yet."
    provider = os.getenv("P3_SEARCH_PROVIDER", "auto")
    search_status = "search key configured" if _has_search_key() else "no search key configured; demo fixture data will be used"
    body = f"""
    <div class="actions">
      <form action="/run" method="post">
        <button type="submit">Run University P3 Agent</button>
      </form>
      <a class="button secondary" href="/reports">View Past Reports</a>
      <a class="button secondary" href="/download/latest">Download Latest Report</a>
    </div>
    <p>{escape(latest_text)}</p>
    <p class="subtle">Search provider: <code>{escape(provider)}</code>; {escape(search_status)}.</p>
    """
    return _render_page(body)


@app.post("/run")
def run_agent() -> RedirectResponse:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUTS_DIR / run_id
    use_fixture = os.getenv("P3_USE_FIXTURE_DATA", "").lower() in {"1", "true", "yes"} or not _has_search_key()
    config = load_config(use_fixture_data=use_fixture, output_dir=str(output_dir))
    build_master(config).run()
    return RedirectResponse(url=f"/reports/{run_id}", status_code=303)


@app.get("/reports", response_class=HTMLResponse)
def reports() -> HTMLResponse:
    rows = []
    for report_dir in _report_dirs():
        files = sorted([p.name for p in report_dir.iterdir() if p.is_file()])
        file_links = "<br>".join(
            f'<a href="/outputs/{escape(report_dir.name)}/{escape(name)}">{escape(name)}</a>' for name in files
        )
        rows.append(
            f"""
            <tr>
              <td><a href="/reports/{escape(report_dir.name)}">{escape(report_dir.name)}</a></td>
              <td>{file_links}</td>
              <td><a href="/download/{escape(report_dir.name)}">Download ZIP</a></td>
            </tr>
            """
        )
    table = (
        "<p>No reports generated yet.</p>"
        if not rows
        else f"""
        <table>
          <thead><tr><th>Run</th><th>Files</th><th>Download</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        """
    )
    body = f"""
    <div class="actions">
      <a class="button secondary" href="/">Dashboard</a>
      <a class="button secondary" href="/download/latest">Download Latest Report</a>
    </div>
    <h2>Past Reports</h2>
    {table}
    """
    return _render_page(body)


@app.get("/reports/{run_id}", response_class=HTMLResponse)
def report_detail(run_id: str) -> HTMLResponse:
    report_dir = _safe_report_dir(run_id)

    files = sorted([p.name for p in report_dir.iterdir() if p.is_file()])
    links = "".join(f'<li><a href="/outputs/{escape(run_id)}/{escape(name)}">{escape(name)}</a></li>' for name in files)
    body = f"""
    <div class="actions">
      <a class="button secondary" href="/">Dashboard</a>
      <a class="button secondary" href="/reports">View Past Reports</a>
      <a class="button" href="/download/{escape(run_id)}">Download This Report</a>
    </div>
    <h2>Report: {escape(run_id)}</h2>
    <ul>{links}</ul>
    """
    notice = "Report generated successfully. Documents are stored in the outputs folder."
    return _render_page(body, notice=notice)


@app.get("/download/latest")
def download_latest() -> FileResponse:
    latest = _latest_report_dir()
    if not latest:
        raise HTTPException(status_code=404, detail="No reports have been generated yet")
    return _zip_report(latest)


@app.get("/download/{run_id}")
def download_report(run_id: str) -> FileResponse:
    return _zip_report(_safe_report_dir(run_id))


def _zip_report(report_dir: Path) -> FileResponse:
    zip_path = report_dir / f"{report_dir.name}_university_p3_report_package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file_path in sorted(report_dir.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() != ".zip":
                bundle.write(file_path, arcname=file_path.name)
    return FileResponse(path=str(zip_path), filename=zip_path.name, media_type="application/zip")
