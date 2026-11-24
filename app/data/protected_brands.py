from __future__ import annotations

"""Brands and government services whose names are impersonated in Indian fraud.

Each entry lists the **official** registered domains and the **tokens** worth
protecting. A token match is only a signal when the domain is not itself
official (planversionalpha.md B.4).

Two rules keep this list honest:

* Only domains that are genuinely operated by the organisation are listed. An
  entry here is used to *clear* a domain, so a wrong entry would hide a scam.
* Tokens are specific enough to be worth protecting. Generic words such as
  "gov", "bank" or "pay" are deliberately absent: they would flag ordinary
  sites such as ``govtjobsalert.in`` or ``pineapple.com``.

``.gov.in`` and ``.nic.in`` registrations are restricted to government bodies,
so any registered domain under them is trusted without being listed.
"""

from dataclasses import dataclass

# Public suffixes that only a government body can register under.
TRUSTED_SUFFIXES: tuple[str, ...] = (".gov.in", ".nic.in", ".gov", ".edu.in", ".ac.in", ".mil.in")


@dataclass(frozen=True)
class ProtectedBrand:
    name: str
    domains: tuple[str, ...]
    tokens: tuple[str, ...]
    category: str


PROTECTED_BRANDS: tuple[ProtectedBrand, ...] = (
    # --- banks ---------------------------------------------------------------
    ProtectedBrand("State Bank of India", ("sbi.co.in", "onlinesbi.sbi", "sbicard.com", "sbiyono.sbi", "bank.sbi"), ("sbi", "onlinesbi", "yono", "sbicard"), "bank"),
    ProtectedBrand("HDFC Bank", ("hdfcbank.com", "hdfc.com", "hdfcsec.com"), ("hdfc", "hdfcbank"), "bank"),
    ProtectedBrand("ICICI Bank", ("icicibank.com", "icicidirect.com"), ("icici", "icicibank", "imobile"), "bank"),
    ProtectedBrand("Axis Bank", ("axisbank.com", "axisbank.co.in"), ("axisbank",), "bank"),
    ProtectedBrand("Kotak Mahindra Bank", ("kotak.com",), ("kotak",), "bank"),
    ProtectedBrand("Punjab National Bank", ("pnbindia.in", "pnbnet.org.in"), ("pnb", "pnbindia"), "bank"),
    ProtectedBrand("Bank of Baroda", ("bankofbaroda.in", "bobworld.com"), ("bankofbaroda", "bobworld"), "bank"),
    ProtectedBrand("Canara Bank", ("canarabank.com", "canarabank.in"), ("canarabank",), "bank"),
    ProtectedBrand("Union Bank of India", ("unionbankofindia.co.in",), ("unionbankofindia",), "bank"),
    ProtectedBrand("Bank of India", ("bankofindia.co.in",), ("bankofindia",), "bank"),
    ProtectedBrand("IndusInd Bank", ("indusind.com",), ("indusind",), "bank"),
    ProtectedBrand("Yes Bank", ("yesbank.in",), ("yesbank",), "bank"),
    ProtectedBrand("IDFC First Bank", ("idfcfirstbank.com",), ("idfcfirst", "idfcfirstbank"), "bank"),
    ProtectedBrand("Bandhan Bank", ("bandhanbank.com",), ("bandhanbank",), "bank"),
    ProtectedBrand("Rajasthan Marudhara Gramin Bank", ("rmgb.in",), ("rmgb", "marudhara"), "bank"),
    ProtectedBrand("Baroda Rajasthan Kshetriya Gramin Bank", ("brkgb.com",), ("brkgb",), "bank"),

    # --- payment service providers -------------------------------------------
    ProtectedBrand("Paytm", ("paytm.com", "paytmbank.com", "paytmmall.com"), ("paytm",), "psp"),
    ProtectedBrand("PhonePe", ("phonepe.com",), ("phonepe",), "psp"),
    ProtectedBrand("Google Pay", ("pay.google.com", "google.com"), ("googlepay", "gpay"), "psp"),
    ProtectedBrand("BHIM / NPCI", ("npci.org.in", "bhimupi.org.in"), ("bhimupi", "npci"), "psp"),
    ProtectedBrand("Amazon Pay", ("amazon.in", "amazon.com", "amazonpay.in"), ("amazonpay",), "psp"),
    ProtectedBrand("Mobikwik", ("mobikwik.com",), ("mobikwik",), "psp"),
    ProtectedBrand("Freecharge", ("freecharge.in",), ("freecharge",), "psp"),

    # --- Rajasthan government services ---------------------------------------
    ProtectedBrand("Government of Rajasthan", ("rajasthan.gov.in",), ("rajasthan",), "govt"),
    ProtectedBrand("Rajasthan SSO", ("sso.rajasthan.gov.in",), ("ssorajasthan",), "govt"),
    ProtectedBrand("Jan Aadhaar", ("janaadhaar.rajasthan.gov.in",), ("janaadhaar", "janadhaar"), "govt"),
    ProtectedBrand("e-Mitra", ("emitra.rajasthan.gov.in",), ("emitra",), "govt"),
    ProtectedBrand("Rajasthan Police", ("police.rajasthan.gov.in",), ("rajasthanpolice",), "govt"),
    ProtectedBrand("Bhamashah", ("bhamashah.rajasthan.gov.in",), ("bhamashah",), "govt"),

    # --- Rajasthan electricity distribution companies ------------------------
    ProtectedBrand("Jaipur Vidyut Vitran Nigam", ("jvvnl.in", "jvvnl.org", "energy.rajasthan.gov.in"), ("jvvnl",), "discom"),
    ProtectedBrand("Ajmer Vidyut Vitran Nigam", ("avvnl.com", "avvnl.co.in"), ("avvnl",), "discom"),
    ProtectedBrand("Jodhpur Vidyut Vitran Nigam", ("jdvvnl.com", "jdvvnl.co.in"), ("jdvvnl",), "discom"),
    ProtectedBrand("Bharatpur Electricity Services", ("besl.co.in",), ("besl",), "discom"),

    # --- central government services -----------------------------------------
    ProtectedBrand("Parivahan / e-Challan", ("parivahan.gov.in", "echallan.parivahan.gov.in", "morth.nic.in"), ("parivahan", "echallan", "mparivahan"), "govt"),
    ProtectedBrand("Income Tax Department", ("incometax.gov.in", "incometaxindia.gov.in", "tin-nsdl.com"), ("incometax", "incometaxindia"), "govt"),
    ProtectedBrand("UIDAI / Aadhaar", ("uidai.gov.in", "myaadhaar.uidai.gov.in"), ("uidai", "aadhaar", "adhaar"), "govt"),
    ProtectedBrand("EPFO", ("epfindia.gov.in", "unifiedportal-mem.epfindia.gov.in"), ("epfindia", "epfo"), "govt"),
    ProtectedBrand("National Cyber Crime Reporting Portal", ("cybercrime.gov.in",), ("cybercrime",), "govt"),
    ProtectedBrand("Reserve Bank of India", ("rbi.org.in", "sachet.rbi.org.in"), ("rbi", "reservebank"), "govt"),
    ProtectedBrand("SEBI", ("sebi.gov.in", "scores.sebi.gov.in"), ("sebi",), "govt"),
    ProtectedBrand("PM Kisan", ("pmkisan.gov.in",), ("pmkisan",), "govt"),
    ProtectedBrand("DigiLocker", ("digilocker.gov.in",), ("digilocker",), "govt"),
    ProtectedBrand("Sanchar Saathi / DoT", ("sancharsaathi.gov.in", "dot.gov.in"), ("sancharsaathi",), "govt"),
    ProtectedBrand("GST portal", ("gst.gov.in",), ("gstportal",), "govt"),

    # --- telecom -------------------------------------------------------------
    ProtectedBrand("Airtel", ("airtel.in", "airtel.com"), ("airtel",), "telecom"),
    ProtectedBrand("Jio", ("jio.com", "jiofiber.com"), ("jio", "reliancejio"), "telecom"),
    ProtectedBrand("Vodafone Idea", ("myvi.in", "vodafoneidea.com"), ("vodafoneidea", "myvi"), "telecom"),
    ProtectedBrand("BSNL", ("bsnl.co.in", "bsnl.in"), ("bsnl",), "telecom"),

    # --- commerce, delivery and large platforms ------------------------------
    ProtectedBrand("Amazon", ("amazon.in", "amazon.com"), ("amazon",), "commerce"),
    ProtectedBrand("Flipkart", ("flipkart.com",), ("flipkart",), "commerce"),
    ProtectedBrand("Myntra", ("myntra.com",), ("myntra",), "commerce"),
    ProtectedBrand("Blue Dart", ("bluedart.com",), ("bluedart",), "courier"),
    ProtectedBrand("India Post", ("indiapost.gov.in",), ("indiapost",), "courier"),
    ProtectedBrand("DTDC", ("dtdc.in", "dtdc.com"), ("dtdc",), "courier"),
    ProtectedBrand("FedEx", ("fedex.com",), ("fedex",), "courier"),
    ProtectedBrand("DHL", ("dhl.com", "dhl.co.in"), ("dhl",), "courier"),
    ProtectedBrand("Delhivery", ("delhivery.com",), ("delhivery",), "courier"),
    ProtectedBrand("Microsoft", ("microsoft.com", "live.com", "office.com"), ("microsoft",), "platform"),
    ProtectedBrand("Apple", ("apple.com", "icloud.com"), ("appleid", "icloud"), "platform"),
    ProtectedBrand("WhatsApp", ("whatsapp.com", "wa.me"), ("whatsapp",), "platform"),
    ProtectedBrand("Instagram", ("instagram.com",), ("instagram",), "platform"),
    ProtectedBrand("Facebook / Meta", ("facebook.com", "meta.com"), ("facebook",), "platform"),
    ProtectedBrand("Netflix", ("netflix.com",), ("netflix",), "platform"),
    ProtectedBrand("PayPal", ("paypal.com",), ("paypal",), "platform"),
    ProtectedBrand("OLX", ("olx.in", "olx.com"), ("olx",), "platform"),
    ProtectedBrand("IRCTC", ("irctc.co.in", "indianrail.gov.in"), ("irctc",), "govt"),
)

OFFICIAL_DOMAINS: frozenset[str] = frozenset(domain for brand in PROTECTED_BRANDS for domain in brand.domains)

# token -> brand name. A token belongs to exactly one brand entry; duplicates
# would make the "which brand is impersonated" message ambiguous.
BRAND_TOKENS: dict[str, str] = {}
for _brand in PROTECTED_BRANDS:
    for _token in _brand.tokens:
        BRAND_TOKENS.setdefault(_token, _brand.name)

# Labels used for edit-distance (typosquatting) comparison: the first label of
# each official domain, plus the protected tokens. Short labels are excluded
# because a 1-character edit on a 3-letter word matches far too much.
PROTECTED_LABELS: dict[str, str] = {}
for _brand in PROTECTED_BRANDS:
    for _domain in _brand.domains:
        _label = _domain.split(".")[0]
        if len(_label) >= 3:
            PROTECTED_LABELS.setdefault(_label, _brand.name)
    for _token in _brand.tokens:
        if len(_token) >= 3:
            PROTECTED_LABELS.setdefault(_token, _brand.name)


def brand_for_domain(registered_domain: str) -> ProtectedBrand | None:
    domain = registered_domain.lower().removeprefix("www.")
    for brand in PROTECTED_BRANDS:
        if domain in brand.domains:
            return brand
    return None


def is_official_domain(host_or_domain: str) -> bool:
    """True for a government suffix or a listed official domain (also as a subdomain)."""

    value = host_or_domain.lower().rstrip(".").removeprefix("www.")
    if value.endswith(TRUSTED_SUFFIXES):
        return True
    if value in OFFICIAL_DOMAINS:
        return True
    return any(value.endswith("." + domain) for domain in OFFICIAL_DOMAINS)


__all__ = [
    "ProtectedBrand",
    "PROTECTED_BRANDS",
    "OFFICIAL_DOMAINS",
    "BRAND_TOKENS",
    "PROTECTED_LABELS",
    "TRUSTED_SUFFIXES",
    "brand_for_domain",
    "is_official_domain",
]
