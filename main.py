"""
Replit startup file for the Florida University P3 Opportunity Agent.

Replit looks for a top-level main.py in many Python projects. This file exposes
the FastAPI app and can also start Uvicorn directly when run with Python.
"""

from __future__ import annotations

import os

import uvicorn

from app import app


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
