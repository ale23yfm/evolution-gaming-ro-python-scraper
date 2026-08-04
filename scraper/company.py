"""
Company Validation Module

Cross-validates company data from ANAF with the Peviitor API.
"""

from .anaf import get_company_from_anaf_with_fallback
from .config import company_config

_ACTIVE_STATUSES = {"activ", "inregistrat", "inregistrat din data"}


def get_company_data(cif=None, cached=None):
    """Fetches company data via ANAF (with cache fallback)."""
    cif = cif or company_config["id"]
    return get_company_from_anaf_with_fallback(cif, cached=cached)


def _is_active(status):
    if not status:
        return True
    status_lower = status.lower().strip()
    for active in _ACTIVE_STATUSES:
        if status_lower.startswith(active):
            return True
    return False


def validate_and_get_company(cif=None, cached=None):
    """Validates company status via ANAF and returns normalized data.

    Falls back to the committed company config when both ANAF APIs are
    unreachable, so scheduled scrapes do not fail on network hiccups.
    """
    cif = cif or company_config["id"]
    try:
        company = get_company_data(cif, cached=cached)
    except RuntimeError:
        company = {
            "cif": cif,
            "denumire": company_config["company"],
            "adresa": ", ".join(company_config.get("location") or []),
            "stareInregistrare": "INREGISTRAT" if company_config["status"] == "activ" else "INACTIV",
        }

    company_name = company.get("denumire")
    if not company_name:
        raise RuntimeError("ANAF returned no company name")

    address = company.get("adresa") or None
    status_raw = company.get("stareInregistrare") or ""
    status = "active" if _is_active(status_raw) else "inactive"

    return {
        "company": company_name,
        "cif": str(cif),
        "address": address,
        "status": status,
    }
