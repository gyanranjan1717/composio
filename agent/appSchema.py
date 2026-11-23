"""The fixed record shape every research pass must produce, and its validator."""

AUTH_METHODS = ("oauth2", "apiKey", "basic", "jwt", "other", "none")
ACCESS_LEVELS = (
    "selfServeFree",
    "selfServeTrial",
    "paidPlan",
    "adminApproval",
    "partnerGated",
    "noPublicApi",
)
API_TYPES = ("rest", "graphql", "restAndGraphql", "cliOnly", "other", "none")
API_BREADTHS = ("narrow", "medium", "broad", "none")
MCP_STATUSES = ("official", "community", "none")
BUILDABLE_VERDICTS = ("yes", "partial", "no")
BLOCKERS = (
    "none",
    "partnerOrSalesGate",
    "paidPlanRequired",
    "appReviewRequired",
    "adminApprovalRequired",
    "noPublicApi",
    "notAnApi",
    "thinOrMissingDocs",
    "narrowApi",
    "other",
)

# Fields scored against the gold sample. Free-text fields are excluded on purpose:
# they cannot be compared mechanically.
SCORED_FIELDS = (
    "authMethods",
    "accessLevel",
    "apiType",
    "existingMcp",
    "buildable",
    "mainBlocker",
)
# Every scored field must be backed by at least one evidence entry.
EVIDENCE_FIELDS = ("authMethods", "accessLevel", "apiType", "existingMcp")

ENUM_FIELDS = {
    "accessLevel": ACCESS_LEVELS,
    "apiType": API_TYPES,
    "apiBreadth": API_BREADTHS,
    "existingMcp": MCP_STATUSES,
    "buildable": BUILDABLE_VERDICTS,
    "mainBlocker": BLOCKERS,
}
TEXT_FIELDS = ("oneLiner", "verdictReason")

RECORD_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "oneLiner",
        "authMethods",
        "oauthAppReviewRequired",
        "accessLevel",
        "apiType",
        "apiBreadth",
        "existingMcp",
        "mcpUrl",
        "buildable",
        "mainBlocker",
        "verdictReason",
        "evidence",
    ],
    "properties": {
        "oneLiner": {"type": "string"},
        "authMethods": {
            "type": "array",
            "items": {"type": "string", "enum": list(AUTH_METHODS)},
        },
        "oauthAppReviewRequired": {"type": "boolean"},
        "accessLevel": {"type": "string", "enum": list(ACCESS_LEVELS)},
        "apiType": {"type": "string", "enum": list(API_TYPES)},
        "apiBreadth": {"type": "string", "enum": list(API_BREADTHS)},
        "existingMcp": {"type": "string", "enum": list(MCP_STATUSES)},
        "mcpUrl": {"type": "string"},
        "buildable": {"type": "string", "enum": list(BUILDABLE_VERDICTS)},
        "mainBlocker": {"type": "string", "enum": list(BLOCKERS)},
        "verdictReason": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "url", "quote"],
                "properties": {
                    "field": {"type": "string", "enum": list(EVIDENCE_FIELDS)},
                    "url": {"type": "string"},
                    "quote": {"type": "string"},
                },
            },
        },
    },
}


def validateRecord(record):
    """Return a list of problems; an empty list means the record is well-formed."""
    problems = []
    for fieldName, allowed in ENUM_FIELDS.items():
        if record[fieldName] not in allowed:
            problems.append(f"{fieldName}: '{record[fieldName]}' not in {allowed}")
    for fieldName in TEXT_FIELDS:
        if not record[fieldName].strip():
            problems.append(f"{fieldName}: empty")
    problems.extend(findAuthProblems(record["authMethods"]))
    problems.extend(findEvidenceProblems(record["evidence"]))
    return problems


def findAuthProblems(authMethods):
    if not authMethods:
        return ["authMethods: empty list"]
    return [
        f"authMethods: '{method}' not in {AUTH_METHODS}"
        for method in authMethods
        if method not in AUTH_METHODS
    ]


def findEvidenceProblems(evidence):
    problems = []
    coveredFields = {entry["field"] for entry in evidence}
    for fieldName in EVIDENCE_FIELDS:
        if fieldName not in coveredFields:
            problems.append(f"evidence: nothing cited for {fieldName}")
    for entry in evidence:
        if not entry["url"].startswith("http"):
            problems.append(f"evidence: bad url for {entry['field']}")
        if not entry["quote"].strip():
            problems.append(f"evidence: empty quote for {entry['field']}")
    return problems
