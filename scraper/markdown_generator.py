"""
Markdown Generator Module

Generates docs/jobs.md after each scrape with company info and current jobs.
"""

import datetime

_OPTIONAL_COMPANY_FIELDS = ("brand", "website", "career", "scraperFile")


def _iso_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_jobs_markdown(company, jobs, generated_at=None):
    """Generates a markdown report with company info and all current jobs."""
    lines = []
    lines.append(f"# {company.get('company', '')}\n")

    lines.append("## Company Info\n")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| CIF | {company.get('id', '')} |")
    for field in _OPTIONAL_COMPANY_FIELDS:
        value = company.get(field)
        if not value:
            continue
        if isinstance(value, list):
            value = value[0]
        lines.append(f"| {field.capitalize()} | {value} |")
    lines.append(f"| LastScraped | {company.get('lastScraped', '')} |")
    lines.append("")

    lines.append(f"## Jobs ({len(jobs)})\n")

    if not jobs:
        lines.append("_No jobs found._\n")

    for job in jobs:
        lines.append(f"### {job.get('title', '')}\n")
        lines.append(f"- **URL**: [{job.get('url', '')}]({job.get('url', '')})")
        if job.get("location"):
            lines.append(f"- **Location**: {', '.join(job['location'])}")
        if job.get("workmode"):
            lines.append(f"- **Work Mode**: {job.get('workmode')}")
        if job.get("tags"):
            lines.append(f"- **Tags**: {', '.join(job['tags'])}")
        if job.get("status"):
            lines.append(f"- **Status**: {job.get('status')}")
        lines.append("")

    lines.append("---")
    lines.append(f"_Generated at {generated_at or _iso_timestamp()}_")
    return "\n".join(lines)
