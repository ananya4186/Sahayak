import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator

app = FastAPI(title="Sahayak API")

# CORS is only needed when the page is opened with Live Server (port 5500)
# while the API runs on port 8000. When the app is deployed, the backend
# serves the page itself, so the page and the API share one address.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
SCHEMES_FILE = BASE_DIR / "schemes.json"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

GOAL_TO_SCHEME_IDS = {
    "education": {"pm-usp-csss"},
    "business": {"pmegp"},
    "skills": {"pm-daksh"},
    "pension": {"pm-sym"},
}

GOAL_LABELS = {
    "education": "Education and scholarships",
    "business": "Business and self-employment",
    "skills": "Skill development and training",
    "pension": "Pension and social security",
}

# Rule operators that schemes.json is allowed to use.
SUPPORTED_OPERATORS = {
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "is_true",
    "is_false",
    "in",
}


def load_schemes():
    with SCHEMES_FILE.open(encoding="utf-8") as file:
        return json.load(file)


class Profile(BaseModel):
    goal: Optional[str] = None

    age: Optional[int] = Field(None, ge=0)
    state: Optional[str] = None
    is_student: Optional[bool] = None
    education_level: Optional[str] = None
    annual_family_income: Optional[float] = Field(None, ge=0)
    employment_status: Optional[str] = None
    social_category: Optional[str] = None

    # PM-USP CSSS
    class12_percentile: Optional[float] = Field(None, ge=0, le=100)
    regular_degree_course: Optional[bool] = None
    institution_recognized: Optional[bool] = None
    receives_other_scholarship: Optional[bool] = None

    # PM-DAKSH
    aadhaar_linked_bank_account: Optional[bool] = None
    course_role_requirements_met: Optional[bool] = None

    # PM-SYM
    monthly_income: Optional[float] = Field(None, ge=0)
    is_unorganised_worker: Optional[bool] = None
    epfo_covered: Optional[bool] = None
    esic_covered: Optional[bool] = None
    nps_covered: Optional[bool] = None
    income_tax_payer: Optional[bool] = None

    @validator("goal")
    def goal_must_be_supported(cls, value):
        if value is not None and value not in GOAL_TO_SCHEME_IDS:
            raise ValueError(
                "goal must be education, business, skills, or pension"
            )
        return value

    @validator(
        "state",
        "education_level",
        "employment_status",
        "social_category",
    )
    def text_must_not_be_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("This field cannot be blank")
        return value


# ---------------------------------------------------------------------------
# Rule engine: every scheme's rules live in schemes.json, and this one
# evaluator reads them. To change a rule, edit schemes.json, not this file.
# ---------------------------------------------------------------------------


def get_field(profile, field):
    """Read a profile field. Text is trimmed and lower-cased so that
    'OBC' and 'obc' compare equal. Blank text counts as missing."""
    value = getattr(profile, field, None)
    if isinstance(value, str):
        value = value.strip().lower() or None
    return value


def rule_applies(rule, profile):
    """A rule can carry applies_when, for example 'only for OBC or EWS'.
    If the field it depends on is missing, the rule is skipped, because
    that field is already reported as missing information by its own rule."""
    condition = rule.get("applies_when")
    if not condition:
        return True
    value = get_field(profile, condition["field"])
    return value is not None and value in condition["in"]


def check_rule(value, rule):
    operator = rule["operator"]
    target = rule.get("value")

    if operator == "gt":
        return value > target
    if operator == "gte":
        return value >= target
    if operator == "lt":
        return value < target
    if operator == "lte":
        return value <= target
    if operator == "between":
        return target[0] <= value <= target[1]
    if operator == "is_true":
        return value is True
    if operator == "is_false":
        return value is False
    if operator == "in":
        return value in target

    raise ValueError(f"Unsupported rule operator: {operator}")


def assess_rules(rules, profile):
    matched = []
    failed = []
    missing = []

    for rule in rules:
        if not rule_applies(rule, profile):
            continue

        value = get_field(profile, rule["field"])
        label = rule["label"]

        if value is None:
            missing.append(label)
        elif check_rule(value, rule):
            matched.append(label)
        else:
            failed.append(label)

    if failed:
        status = "Not Eligible"
    elif missing:
        status = "Potential Match"
    else:
        status = "Eligible"

    return {
        "status": status,
        "matched_conditions": matched,
        "failed_conditions": failed,
        "missing_information": missing,
    }


def evaluate_scheme(scheme, profile):
    # A scheme marked assessable: false is shown with its information,
    # but Sahayak makes no eligibility call for it.
    if not scheme.get("assessable", False):
        return {
            "status": "Not Assessed",
            "matched_conditions": [],
            "failed_conditions": [],
            "missing_information": [],
            "explanation": scheme.get(
                "not_assessed_reason",
                "Sahayak does not assess this scheme. Confirm the requirements on the official portal.",
            ),
        }

    result = assess_rules(scheme.get("rules", []), profile)
    result["explanation"] = scheme.get("explanation", "")
    return result


def build_recommendation(scheme, profile):
    recommendation = {
        "id": scheme["id"],
        "name": scheme["name"],
        "category": scheme["category"],
        "description": scheme.get("description", ""),
        "official_source_url": scheme["official_source_url"],
        "official_apply_url": scheme.get(
            "official_apply_url", scheme["official_source_url"]
        ),
        "last_verified": scheme["last_verified"],
        "status_notice": scheme.get("status_notice"),
        "benefits": scheme.get("benefits", []),
        "documents": scheme.get(
            "documents", {"mandatory": [], "conditional": []}
        ),
        "application_steps": scheme.get("application_steps", []),
        "sources": scheme.get("sources", []),
    }
    recommendation.update(evaluate_scheme(scheme, profile))
    return recommendation


@app.get("/health")
def health():
    return {"message": "Sahayak API is running"}


@app.get("/api/schemes")
def list_schemes():
    return load_schemes()


@app.get("/api/schemes/{scheme_id}")
def get_scheme(scheme_id: str):
    for scheme in load_schemes():
        if scheme["id"] == scheme_id:
            return scheme
    raise HTTPException(status_code=404, detail="Scheme not found")


@app.post("/api/profile/validate")
def validate_profile(profile: Profile):
    return profile.dict(exclude_none=True)


@app.post("/api/schemes/recommend")
def recommend_schemes(profile: Profile):
    if profile.goal is None:
        raise HTTPException(
            status_code=422,
            detail="Choose what type of support you are looking for.",
        )

    allowed_ids = GOAL_TO_SCHEME_IDS[profile.goal]
    selected_schemes = [
        scheme
        for scheme in load_schemes()
        if scheme["id"] in allowed_ids
    ]

    return {
        "selected_goal": profile.goal,
        "goal_label": GOAL_LABELS[profile.goal],
        "recommendations": [
            build_recommendation(scheme, profile)
            for scheme in selected_schemes
        ],
    }


# Serve the frontend (index.html, app.js, style.css) from the same server.
# This must stay at the very END of the file, after every API route,
# so that /api/... requests are matched by the routes above first.
if FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend",
    )