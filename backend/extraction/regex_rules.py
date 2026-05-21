"""
Deterministic regex extractors for engineering parameters.
Returns list of raw match dicts: {entity, parameter_name, value_raw, unit, source_text, page, confidence}

Design rule: regex runs FIRST. High-confidence numeric values should never go through LLM.
The LLM normalizer only sees what regex couldn't fully classify.
"""

import re
from dataclasses import dataclass


@dataclass
class RegexMatch:
    entity: str
    parameter_name: str
    value_raw: str
    unit: str | None
    source_text: str
    confidence: float


PATTERNS: list[tuple[str, str, re.Pattern, str | None]] = [
    ("power_kw", "Power Output (kW)",
     re.compile(r'(?P<val>\d[\d,]*\.?\d*)\s*kW\b', re.IGNORECASE), "kW"),

    ("power_ekw", "Power Output (ekW)",
     re.compile(r'(?P<val>\d[\d,]*\.?\d*)\s*ekW\b', re.IGNORECASE), "ekW"),

    ("power_kva", "Apparent Power (kVA)",
     re.compile(r'(?P<val>\d[\d,]*\.?\d*)\s*kVA\b', re.IGNORECASE), "kVA"),

    ("voltage", "Voltage",
     re.compile(r'(?P<val>\d[\d,]*\.?\d*)\s*[Vv](?:olts?)?\b'), "V"),

    ("frequency", "Frequency",
     re.compile(r'(?P<val>\d+\.?\d*)\s*[Hh][Zz]\b'), "Hz"),

    ("engine_speed_rpm", "Engine Speed",
     re.compile(r'(?P<val>\d[\d,]*)\s*[Rr][Pp][Mm]\b'), "RPM"),

    ("power_factor", "Power Factor",
     re.compile(r'[Pp]ower\s+[Ff]actor[:\s]+(?P<val>0\.\d+|\.\d+|\d+\.?\d*)\b'), None),

    ("runtime_minutes", "Minimum Runtime",
     re.compile(r'(?P<val>\d+)\s*(?:minute|min)s?\b', re.IGNORECASE), "min"),

    ("fuel_type", "Fuel Type",
     re.compile(r'\b(?P<val>diesel|natural\s+gas|propane|LP\s+gas|gasoline)\b', re.IGNORECASE), None),
]

STANDARDS_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("UL 2200",    re.compile(r'\bUL\s*2200\b')),
    ("UL 508A",    re.compile(r'\bUL\s*508A\b', re.IGNORECASE)),
    ("UL 489",     re.compile(r'\bUL\s*489\b')),
    ("NFPA 110",   re.compile(r'\bNFPA\s*110\b')),
    ("NFPA 70",    re.compile(r'\bNFPA\s*70\b|NEC\b')),
    ("IEEE",       re.compile(r'\bIEEE\b')),
    ("OSHA",       re.compile(r'\bOSHA\b')),
    ("IEC 61511",  re.compile(r'\bIEC\s*61511\b')),
    ("ISA-84",     re.compile(r'\bISA-?84\b')),
    ("ASME",       re.compile(r'\bASME\b')),
    ("ISO 8528",   re.compile(r'\bISO\s*8528\b')),
]

ENUM_PATTERNS: list[tuple[str, str, re.Pattern, str]] = [
    ("generator_rating_type", "Rating Type",
     re.compile(r'\bstandby\s+(?:power\s+)?(?:rating|rated|generator|set)?\b', re.IGNORECASE), "STANDBY"),

    ("generator_rating_type", "Rating Type",
     re.compile(r'\bprime\s+(?:power\s+)?(?:rating|rated)?\b', re.IGNORECASE), "PRIME"),

    ("generator_rating_type", "Rating Type",
     re.compile(r'\bcontinuous\s+(?:power\s+)?(?:rating|rated|duty)?\b|rating\s+type\s*:\s*continuous\b', re.IGNORECASE), "CONTINUOUS"),

    ("enclosure_type", "Enclosure Type",
     re.compile(r'\boutdoor\s+(?:enclosure|rated|housing|package)\b', re.IGNORECASE), "OUTDOOR"),

    ("enclosure_type", "Enclosure Type",
     re.compile(r'\bindoor\s+(?:enclosure|rated|installation)\b', re.IGNORECASE), "INDOOR"),

    ("operation_mode", "Operation Mode",
     re.compile(r'\bautomatic\s+(?:start|transfer|operation)\b|\bauto[-\s]start\b', re.IGNORECASE), "AUTOMATIC"),

    ("operation_mode", "Operation Mode",
     re.compile(r'\bmanual\s+(?:start|operation|control)\b', re.IGNORECASE), "MANUAL"),

    ("control_location", "Control Location",
     re.compile(r'\bremote\s+(?:control|monitoring|emergency\s+stop)\b', re.IGNORECASE), "REMOTE"),

    ("control_location", "Control Location",
     re.compile(r'\blocal\s+(?:control|panel|only)\b', re.IGNORECASE), "LOCAL"),
]

CHECKLIST_ITEMS: dict[str, list[str]] = {
    "remote_emergency_stop": [
        r'\bremote\s+emergency\s+stop\b',
        r'\bremote\s+stop\b',
        r'\bemergency\s+stop.*remote\b',
    ],
    "battery_low_alarm": [
        r'\bbattery\s+(?:low|charge|charging)\s+alarm\b',
        r'\blow\s+battery\s+alarm\b',
        r'\bbattery\s+fail\b',
    ],
    "generator_fail_contact": [
        r'\bgenerator\s+fail(?:ure)?\s+(?:contact|relay|alarm)\b',
        r'\bgen(?:erator)?\s+fail\b',
        r'\bcommon\s+alarm\s+contact\b',
    ],
    "fault_alarm_historian": [
        r'\bfault\s+historian\b',
        r'\balarm\s+hist(?:orian|ory)\b',
        r'\bevent\s+log\b',
        r'\bfault\s+log\b',
    ],
    "auto_start_on_power_loss": [
        r'\bauto(?:matic)?\s*[-\s]?start\b',
        r'\bstart\s+on\s+(?:power\s+)?loss\b',
        r'\bautomatic\s+transfer\b',
    ],
    "overcurrent_protection": [
        r'\bovercurrent\s+protection\b',
        r'\bbreaker\b',
        r'\bcircuit\s+breaker\b',
        r'\boverload\s+protection\b',
    ],
    "load_testing_requirement": [
        r'\bload\s+test(?:ing)?\b',
        r'\bacceptance\s+test(?:ing)?\b',
        r'\bfinal\s+acceptance\b',
        r'\bfactory\s+test(?:ing)?\b',
    ],
}


def extract_regex_claims(page_text: str, page_number: int, document_id: str) -> list[dict]:
    """Run all regex patterns against page text. Returns list of raw claim dicts."""
    claims = []
    seen_entities: set[str] = set()

    for entity, param_name, pattern, unit in PATTERNS:
        for m in pattern.finditer(page_text):
            val = m.group("val").replace(",", "")
            start = max(0, m.start() - 100)
            end = min(len(page_text), m.end() + 100)
            snippet = page_text[start:end].strip().replace("\n", " ")

            claims.append({
                "document_id": document_id,
                "page_number": page_number,
                "claim_type": "parameter",
                "entity": entity,
                "parameter_name": param_name,
                "value_raw": m.group(0),
                "value_normalized": val,
                "unit": unit,
                "condition": None,
                "source_text": snippet,
                "extraction_method": "regex",
                "confidence": 0.95,
            })

    for std_name, pattern in STANDARDS_PATTERNS:
        if pattern.search(page_text):
            m = pattern.search(page_text)
            start = max(0, m.start() - 100)
            end = min(len(page_text), m.end() + 100)
            snippet = page_text[start:end].strip().replace("\n", " ")

            key = f"ref_{std_name}"
            if key not in seen_entities:
                seen_entities.add(key)
                claims.append({
                    "document_id": document_id,
                    "page_number": page_number,
                    "claim_type": "reference",
                    "entity": f"standard_{std_name.lower().replace(' ', '_').replace('-', '_')}",
                    "parameter_name": std_name,
                    "value_raw": m.group(0),
                    "value_normalized": std_name,
                    "unit": None,
                    "condition": None,
                    "source_text": snippet,
                    "extraction_method": "regex",
                    "confidence": 0.99,
                })

    for entity, param_name, pattern, normalized in ENUM_PATTERNS:
        m = pattern.search(page_text)
        if m:
            key = f"enum_{entity}_{normalized}"
            if key not in seen_entities:
                seen_entities.add(key)
                start = max(0, m.start() - 120)
                end = min(len(page_text), m.end() + 120)
                snippet = page_text[start:end].strip().replace("\n", " ")

                claims.append({
                    "document_id": document_id,
                    "page_number": page_number,
                    "claim_type": "assumption",
                    "entity": entity,
                    "parameter_name": param_name,
                    "value_raw": m.group(0),
                    "value_normalized": normalized,
                    "unit": None,
                    "condition": None,
                    "source_text": snippet,
                    "extraction_method": "regex",
                    "confidence": 0.92,
                })

    for item_id, patterns_list in CHECKLIST_ITEMS.items():
        for pat_str in patterns_list:
            m = re.search(pat_str, page_text, re.IGNORECASE)
            if m:
                key = f"checklist_{item_id}"
                if key not in seen_entities:
                    seen_entities.add(key)
                    start = max(0, m.start() - 100)
                    end = min(len(page_text), m.end() + 100)
                    snippet = page_text[start:end].strip().replace("\n", " ")

                    claims.append({
                        "document_id": document_id,
                        "page_number": page_number,
                        "claim_type": "checklist",
                        "entity": f"checklist_{item_id}",
                        "parameter_name": item_id.replace("_", " ").title(),
                        "value_raw": m.group(0),
                        "value_normalized": "PRESENT",
                        "unit": None,
                        "condition": None,
                        "source_text": snippet,
                        "extraction_method": "regex",
                        "confidence": 0.90,
                    })
                break

    return claims
