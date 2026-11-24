from __future__ import annotations

"""Render a legal requisition as print-ready HTML (planversionalpha.md D.3).

Built with the same escaped-f-string approach as ``report_builder.py`` rather
than a template engine, to stay consistent with the codebase and to avoid
adding a dependency for eight documents.

Three rules every template follows:

* Until it is approved it carries a visible **DRAFT** watermark, so a printed
  draft can never be mistaken for a signed requisition.
* The signature block is left for the approving officer. PARAKH does not
  render a signature, a seal or an officer's name as if they had signed.
* Anything the system could not confirm (a ported mobile number, a UPI
  handle's sponsor bank) is printed as a "confirm before dispatch" line
  rather than silently asserted.
"""

from datetime import datetime, timezone
from html import escape

from app.data.approval_policy import policy_for
from app.schemas import CaseDetail

_STYLE = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #111827; font-size: 12pt; line-height: 1.55; margin: 0; }
.sheet { max-width: 760px; margin: 0 auto; padding: 24px; position: relative; }
.watermark { position: fixed; top: 42%; left: 50%; transform: translate(-50%, -50%) rotate(-28deg);
  font-size: 84pt; font-weight: 800; color: rgba(220, 38, 38, 0.10); letter-spacing: 6px;
  pointer-events: none; z-index: 0; }
header { border-bottom: 2px solid #1d4ed8; padding-bottom: 10px; margin-bottom: 18px; }
.force { font-size: 15pt; font-weight: 700; color: #1e3a8a; }
.unit { font-size: 11pt; color: #374151; }
.meta { display: flex; justify-content: space-between; font-size: 10.5pt; color: #374151; margin-top: 8px; }
h1 { font-size: 13.5pt; text-align: center; text-transform: uppercase; letter-spacing: .5px; margin: 18px 0 4px; }
.legal { text-align: center; font-size: 10.5pt; color: #4b5563; margin-bottom: 18px; }
.to { margin: 14px 0; }
.to .label { font-weight: 700; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10.5pt; }
th, td { border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #eef2ff; font-weight: 600; }
.mono { font-family: 'Consolas', 'Courier New', monospace; word-break: break-all; }
ol.requests { margin: 10px 0 10px 18px; padding: 0; }
ol.requests li { margin-bottom: 6px; }
.caution { border-left: 4px solid #d97706; background: #fffbeb; padding: 10px 12px; margin: 14px 0; font-size: 10.5pt; }
.sample { border-left: 4px solid #6b7280; background: #f9fafb; padding: 8px 12px; margin: 10px 0; font-size: 10pt; color: #374151; }
.sign { margin-top: 34px; display: flex; justify-content: flex-end; }
.sign .box { width: 290px; border-top: 1px solid #111827; padding-top: 6px; font-size: 10.5pt; }
footer { margin-top: 26px; border-top: 1px solid #e5e7eb; padding-top: 8px; font-size: 9.5pt; color: #6b7280; }
"""


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%d %B %Y")


def _identifier_rows(identifiers: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{index}</td><td>{escape(item.get('type', ''))}</td>"
        f"<td class='mono'>{escape(item.get('value', ''))}</td>"
        f"<td>{escape(item.get('context', '') or '')[:160]}</td></tr>"
        for index, item in enumerate(identifiers, start=1)
    )
    return (
        "<table><thead><tr><th>#</th><th>Type</th><th>Identifier</th>"
        f"<th>Where it appeared</th></tr></thead><tbody>{rows}</tbody></table>"
    )


def _evidence_rows(detail: CaseDetail) -> str:
    rows = [
        f"<tr><td>Case record</td><td class='mono'>{escape(detail.case_id)}</td>"
        f"<td class='mono'>{escape(detail.details.get('content_sha256') or detail.details.get('sha256') or '-')}</td></tr>"
    ]
    raw_hash = detail.details.get("raw_sha256")
    if raw_hash:
        rows.append(f"<tr><td>Fetched page (raw bytes)</td><td>-</td><td class='mono'>{escape(str(raw_hash))}</td></tr>")
    apk_hash = detail.details.get("sha256")
    if apk_hash and detail.artifact_type.value == "APK":
        rows.append(
            f"<tr><td>Application file</td><td class='mono'>{escape(str(detail.details.get('filename') or 'app.apk'))}</td>"
            f"<td class='mono'>{escape(str(apk_hash))}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Item</th><th>Reference</th><th>SHA-256</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _header(unit_name: str, doc_no: str, case_id: str) -> str:
    return f"""
    <header>
      <div class="force">RAJASTHAN POLICE</div>
      <div class="unit">{escape(unit_name)}</div>
      <div class="meta">
        <span>No.: <strong class="mono">{escape(doc_no)}</strong></span>
        <span>Case: <strong class="mono">{escape(case_id)}</strong></span>
        <span>Date: <strong>{_today()}</strong></span>
      </div>
    </header>
    """


def _signature(officer: dict) -> str:
    name = escape(str(officer.get("display_name") or officer.get("username") or ""))
    rank = escape(str(officer.get("rank") or ""))
    unit = escape(str(officer.get("unit") or ""))
    return f"""
    <div class="sign"><div class="box">
      <div>(Signature)</div>
      <div><strong>{name}</strong></div>
      <div>{rank}</div>
      <div>{unit}</div>
      <div style="margin-top:6px;color:#6b7280">Seal of the office</div>
    </div></div>
    """


def _caution(resolution_notes: list[str], is_sample: bool, addressee_contact: str) -> str:
    blocks = []
    if is_sample:
        blocks.append(
            "<div class='sample'><strong>Addressee to be completed.</strong> PARAKH does not store "
            f"nodal-officer contact details. Replace with the current official address. ({escape(addressee_contact)})</div>"
        )
    notes = [note for note in resolution_notes if note]
    if notes:
        items = "".join(f"<li>{escape(note)}</li>" for note in dict.fromkeys(notes))
        blocks.append(f"<div class='caution'><strong>Confirm before dispatch:</strong><ul>{items}</ul></div>")
    return "".join(blocks)


_REQUESTS: dict[str, tuple[str, ...]] = {
    "BANK_PRODUCE_94": (
        "Complete KYC records of the account or virtual payment address listed below, including "
        "photograph, identity and address proof, and the mobile number and email registered.",
        "Account statement for the period stated above, showing all credits and debits.",
        "Details of all accounts linked to the same KYC, customer identification number or mobile number.",
        "Device, IP address and login logs for the account, with timestamps in IST.",
        "Beneficiary details for every onward transfer of the disputed amount, including the "
        "beneficiary bank, account number and IFSC.",
    ),
    "BANK_FREEZE_106": (
        "Place an immediate hold or lien on the disputed amount lying in the account or virtual "
        "payment address listed below, to the extent of the amount stated.",
        "Confirm in writing the balance held and the exact amount placed on hold.",
        "Trace and place a hold on the same amount in any account to which it has already been "
        "transferred, and report those accounts.",
        "Do not permit closure of the account until this office communicates further.",
    ),
    "TELECOM_CAF_CDR": (
        "Customer Application Form (CAF) with the identity and address proof submitted, and the "
        "date and point of sale of activation.",
        "Call Detail Records for the period stated above, including the IMEI of every handset used.",
        "Details of all other mobile numbers activated on the same identity document.",
        "Cell tower location records for the period stated above.",
    ),
    "DOT_CHAKSHU_REPORT": (
        "Examine the number reported below for use in financial fraud.",
        "Consider disconnection of the connection and the handset where the records support it.",
        "Share the outcome with this office for the case record.",
    ),
    "REGISTRAR_TAKEDOWN": (
        "Suspend resolution of the domain listed below, which is being used to defraud members "
        "of the public.",
        "Preserve and disclose the registrant's name, address, email, phone number and the "
        "payment instrument used for registration and renewal.",
        "Preserve all access and change logs for the registration.",
    ),
    "HOSTING_ABUSE": (
        "Remove or disable access to the content hosted at the address listed below.",
        "Preserve and disclose the subscriber details of the account that hosts it.",
        "Preserve server access logs for the period stated above.",
    ),
    "INTERMEDIARY_79_3B": (
        "Remove or disable access to the channel, group, account or application listed below, "
        "which is being used to commit financial fraud.",
        "Preserve and disclose the subscriber information of the operator, including the "
        "registered mobile number, email, IP addresses and device identifiers used.",
        "Preserve all content and logs associated with it pending further directions.",
    ),
    "BSA_63_CERT": (
        "The electronic records listed in the annexure were produced by the PARAKH analysis "
        "system operating in the ordinary course of the activities of this office.",
        "The computer output was produced by a system that was operating properly at the "
        "material time, and the information was regularly fed into it in the ordinary course.",
        "The SHA-256 values listed in the annexure were computed at the time of capture and "
        "identify the records produced.",
    ),
}


def render(
    *,
    doc_type: str,
    doc_no: str,
    detail: CaseDetail,
    unit_name: str,
    officer: dict,
    addressee_display: str,
    addressee_contact: str,
    addressee_is_sample: bool,
    identifiers: list[dict],
    resolution_notes: list[str],
    approved: bool = False,
    period_from: str | None = None,
    period_to: str | None = None,
) -> str:
    """One requisition as a self-contained A4 HTML page."""

    policy = policy_for(doc_type)
    watermark = "" if approved else "<div class='watermark'>DRAFT</div>"
    requests = "".join(f"<li>{escape(text)}</li>" for text in _REQUESTS.get(doc_type, ()))
    period = (
        f"{escape(period_from)} to {escape(period_to)}"
        if period_from and period_to
        else "the period of the offence, and the six months preceding it"
    )

    if doc_type == "BSA_63_CERT":
        subject_block = (
            "<h2 style='font-size:11.5pt;margin-top:18px'>Annexure - electronic records produced</h2>"
            + _evidence_rows(detail)
        )
        intro = (
            "I, the officer named below, state as follows in respect of the electronic records "
            "produced in this case:"
        )
        closing = (
            "<p>Part B of this certificate, to be completed by the person in charge of the computer "
            "or communication device, is left blank for the expert to complete.</p>"
        )
    else:
        subject_block = (
            "<h2 style='font-size:11.5pt;margin-top:18px'>Subject identifiers</h2>"
            + _identifier_rows(identifiers)
        )
        intro = (
            f"A case of cyber financial fraud is under investigation at this office. "
            f"You are required to furnish the following in respect of the identifiers listed below, "
            f"for {period}."
        )
        closing = (
            "<p>The information is required for the purposes of investigation. Kindly treat this as "
            "urgent and acknowledge receipt by return.</p>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{escape(doc_no)} - {escape(policy.title)}</title>
<style>{_STYLE}</style></head>
<body>{watermark}
<div class="sheet">
  {_header(unit_name, doc_no, detail.case_id)}
  <h1>{escape(policy.title)}</h1>
  <div class="legal">Under {escape(policy.legal_basis)}</div>

  <div class="to">
    <div class="label">To,</div>
    <div>{escape(addressee_display)}</div>
  </div>

  {_caution(resolution_notes, addressee_is_sample, addressee_contact)}

  <p>{escape(intro)}</p>
  <ol class="requests">{requests}</ol>

  {subject_block}
  {closing}

  {_signature(officer)}

  <footer>
    Generated by PARAKH from case {escape(detail.case_id)}. Automated analysis produces
    investigative indicators, not proof of criminal conduct; the contents are to be verified by the
    investigating officer before dispatch.
  </footer>
</div>
</body></html>"""


__all__ = ["render"]
