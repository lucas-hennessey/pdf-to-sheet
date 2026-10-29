"""Parse Foundation Directory Online PDF exports into one sheet row."""
import re

import pymupdf

HEADERS = [
    "Foundation Name", "Address 1", "Address 2", "City", "State", "Zip",
    "Average Grant Amount", "Subjects", "Population Groups", "Geographic Focus",
    "Limitations", "Application Process", "Contact Name", "Contact Address 1",
    "Contact Address 2", "Contact City", "Contact State", "Contact Zip",
    "Contact Phone", "Contact Email",
]

FOOTER_RE = re.compile(r"^.*: Page \d+ of \d+$")
PROFILE_UPDATED_RE = re.compile(r"^Profile Last Updated:")
CITY_LINE_RE = re.compile(r"^(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\s*$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# Labels in the "Funding Interests" block; each is printed on one or two lines.
INTEREST_LABELS = [
    ("SUBJECTS", r"SUBJECTS"),
    ("GEOGRAPHIC FOCUS", r"GEOGRAPHIC\s*\n?\s*FOCUS"),
    ("POPULATION GROUPS", r"POPULATION\s*\n?\s*GROUPS"),
    ("SUPPORT STRATEGIES", r"SUPPORT\s*\n?\s*STRATEGIES"),
    ("TRANSACTION TYPES", r"TRANSACTION\s*\n?\s*TYPES"),
    ("ORGANIZATION TYPES", r"ORGANIZATION\s*\n?\s*TYPES"),
]


def extract_text(path):
    with pymupdf.open(path) as doc:
        text = "\n".join(page.get_text() for page in doc)
    lines = [
        l.rstrip() for l in text.splitlines()
        if not FOOTER_RE.match(l.strip()) and not PROFILE_UPDATED_RE.match(l.strip())
    ]
    return "\n".join(lines)


def _flat(s):
    return re.sub(r"\s+", " ", s).strip()


def _section(text, start_pattern, end_patterns):
    m = re.search(start_pattern, text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    end = len(rest)
    for p in end_patterns:
        e = re.search(p, rest, re.M)
        if e:
            end = min(end, e.start())
    return rest[:end]


def _interest(text, key):
    block = _section(text, r"^Funding Interests\s*$", [r"^About\s*$", r"^Other Funders to Consider"])
    pattern = dict(INTEREST_LABELS)[key]
    m = re.search(r"^" + pattern + r"\s*$|^" + pattern + r"\s+", block, re.M)
    if not m:
        return ""
    rest = block[m.end():]
    ends = [
        re.search(r"^" + p + r"\s*$|^" + p + r"\s+", rest, re.M)
        for name, p in INTEREST_LABELS if name != key
    ]
    cut = min([e.start() for e in ends if e] + [len(rest)])
    return _flat(rest[:cut])


def _average_grant(text):
    # Table cells may come out one per line (PyMuPDF) or as one row per line.
    grants = _section(text, r"^Recipient City", [r"^Total Number of Grants"])
    amounts = [int(m.group(1).replace(",", "")) for m in
               re.finditer(r"\b(?:19|20)\d{2}[ \t]*\n?[ \t]*\$([\d,]+)[ \t]*$", grants, re.M)]
    if not amounts:
        return ""
    return round(sum(amounts) / len(amounts))


def _location(text):
    block = _section(text, r"^LOCATION\s*$", [r"^ADDITIONAL LOCATION INFORMATION", r"^CONTACT INFORMATION"])
    street, city, state, zip_ = [], "", "", ""
    for line in (l.strip() for l in block.splitlines() if l.strip()):
        m = CITY_LINE_RE.match(line)
        if m:
            city, state, zip_ = m.groups()
            break
        street.append(line)
    return street, city, state, zip_


def _contact(text):
    block = _section(text, r"^CONTACT INFORMATION\s*$", [r"^https://fconline", r"^Copyright"])
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    out = {k: "" for k in ("name", "a1", "a2", "city", "state", "zip", "phone", "email")}
    street = []
    for line in lines:
        if line.startswith("Contact:"):
            out["name"] = line[len("Contact:"):].split(",")[0].strip()
        elif line.startswith("Telephone:"):
            out["phone"] = line[len("Telephone:"):].strip()
        elif line.startswith("Email:") or EMAIL_RE.search(line):
            m = EMAIL_RE.search(line)
            out["email"] = m.group(0) if m else ""
        elif m := CITY_LINE_RE.match(line):
            out["city"], out["state"], out["zip"] = m.groups()
        elif not re.match(r"^(URL|Fax|Contact|Telephone|Email):?", line) and not out["city"] \
                and re.match(r"^\d", line):
            street.append(line)
    if street:
        out["a1"], out["a2"] = street[0], " ".join(street[1:])
    return out


def _application(text):
    block = _section(text, r"^Applications/RFPs\s*$", [r"^[^\n]+\nDeadline:", r"^Current RFPs", r"^Financials\s*$"])
    return _flat(block)


def _limitations(text):
    m = re.search(r"^Limitations:?\s*\n?(.*?)(?=^[A-Z][A-Za-z/ ]+:?\s*$|^Financials|\Z)", text, re.M | re.S)
    return _flat(m.group(1)) if m else ""


def parse_pdf(path):
    """Return (row_dict, warnings). Missing fields are left blank and warned about."""
    text = extract_text(path)
    name = next((l.strip() for l in text.splitlines() if l.strip()), "")
    street, city, state, zip_ = _location(text)
    contact = _contact(text)
    row = {
        "Foundation Name": name,
        "Address 1": street[0] if street else "",
        "Address 2": " ".join(street[1:]),
        "City": city, "State": state, "Zip": zip_,
        "Average Grant Amount": _average_grant(text),
        "Subjects": _interest(text, "SUBJECTS"),
        "Population Groups": _interest(text, "POPULATION GROUPS"),
        "Geographic Focus": _interest(text, "GEOGRAPHIC FOCUS"),
        "Limitations": _limitations(text),
        "Application Process": _application(text),
        "Contact Name": contact["name"],
        "Contact Address 1": contact["a1"], "Contact Address 2": contact["a2"],
        "Contact City": contact["city"], "Contact State": contact["state"],
        "Contact Zip": contact["zip"], "Contact Phone": contact["phone"],
        "Contact Email": contact["email"],
    }
    optional = {"Address 2", "Limitations", "Contact Address 1", "Contact Address 2",
                "Contact City", "Contact State", "Contact Zip"}
    warnings = [f"{h} not found" for h in HEADERS if row[h] == "" and h not in optional]
    return row, warnings
