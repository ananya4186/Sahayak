import pytest
from fastapi import HTTPException

from backend.main import (
    GOAL_TO_SCHEME_IDS,
    SUPPORTED_OPERATORS,
    Profile,
    evaluate_scheme,
    load_schemes,
    recommend_schemes,
)


def scheme_by_id(scheme_id):
    for scheme in load_schemes():
        if scheme["id"] == scheme_id:
            return scheme
    raise AssertionError(f"Scheme {scheme_id} not found in schemes.json")


# ---------- PM-USP CSSS ----------


def csss_profile(**changes):
    values = {
        "goal": "education",
        "class12_percentile": 90,
        "is_student": True,
        "regular_degree_course": True,
        "institution_recognized": True,
        "annual_family_income": 200000,
        "receives_other_scholarship": False,
    }
    values.update(changes)
    return Profile(**values)


def test_csss_eligible_when_all_conditions_met():
    result = evaluate_scheme(scheme_by_id("pm-usp-csss"), csss_profile())
    assert result["status"] == "Eligible"
    assert result["failed_conditions"] == []
    assert result["missing_information"] == []


def test_csss_not_eligible_when_income_too_high():
    result = evaluate_scheme(
        scheme_by_id("pm-usp-csss"), csss_profile(annual_family_income=500000)
    )
    assert result["status"] == "Not Eligible"
    assert len(result["failed_conditions"]) == 1


def test_csss_income_exactly_4_5_lakh_is_accepted():
    result = evaluate_scheme(
        scheme_by_id("pm-usp-csss"), csss_profile(annual_family_income=450000)
    )
    assert result["status"] == "Eligible"


def test_csss_percentile_80_is_not_above_80():
    result = evaluate_scheme(
        scheme_by_id("pm-usp-csss"), csss_profile(class12_percentile=80)
    )
    assert result["status"] == "Not Eligible"


def test_csss_other_scholarship_fails():
    result = evaluate_scheme(
        scheme_by_id("pm-usp-csss"),
        csss_profile(receives_other_scholarship=True),
    )
    assert result["status"] == "Not Eligible"


def test_csss_empty_profile_is_potential_match_not_not_eligible():
    result = evaluate_scheme(
        scheme_by_id("pm-usp-csss"), Profile(goal="education")
    )
    assert result["status"] == "Potential Match"
    assert result["failed_conditions"] == []
    assert len(result["missing_information"]) == 6


def test_missing_answer_does_not_hide_a_failed_condition():
    result = evaluate_scheme(
        scheme_by_id("pm-usp-csss"),
        Profile(goal="education", annual_family_income=900000),
    )
    assert result["status"] == "Not Eligible"
    assert len(result["missing_information"]) == 5


# ---------- PM-DAKSH ----------


def daksh_profile(**changes):
    values = {
        "goal": "skills",
        "age": 25,
        "social_category": "SC",
        "aadhaar_linked_bank_account": True,
        "course_role_requirements_met": True,
    }
    values.update(changes)
    return Profile(**values)


def test_daksh_sc_applicant_needs_no_income_check():
    result = evaluate_scheme(scheme_by_id("pm-daksh"), daksh_profile())
    assert result["status"] == "Eligible"


def test_daksh_obc_below_income_limit_is_eligible():
    result = evaluate_scheme(
        scheme_by_id("pm-daksh"),
        daksh_profile(social_category="obc", annual_family_income=250000),
    )
    assert result["status"] == "Eligible"


def test_daksh_obc_without_income_is_potential_match():
    result = evaluate_scheme(
        scheme_by_id("pm-daksh"), daksh_profile(social_category="OBC")
    )
    assert result["status"] == "Potential Match"
    assert len(result["missing_information"]) == 1


def test_daksh_ews_income_3_lakh_fails_because_limit_is_below_3_lakh():
    result = evaluate_scheme(
        scheme_by_id("pm-daksh"),
        daksh_profile(social_category="EWS", annual_family_income=300000),
    )
    assert result["status"] == "Not Eligible"


def test_daksh_category_not_listed_fails():
    result = evaluate_scheme(
        scheme_by_id("pm-daksh"), daksh_profile(social_category="General")
    )
    assert result["status"] == "Not Eligible"


def test_daksh_age_limits():
    scheme = scheme_by_id("pm-daksh")
    assert evaluate_scheme(scheme, daksh_profile(age=18))["status"] == "Eligible"
    assert evaluate_scheme(scheme, daksh_profile(age=45))["status"] == "Eligible"
    assert evaluate_scheme(scheme, daksh_profile(age=46))["status"] == "Not Eligible"
    assert evaluate_scheme(scheme, daksh_profile(age=17))["status"] == "Not Eligible"


# ---------- PM-SYM ----------


def sym_profile(**changes):
    values = {
        "goal": "pension",
        "age": 30,
        "monthly_income": 12000,
        "is_unorganised_worker": True,
        "epfo_covered": False,
        "esic_covered": False,
        "nps_covered": False,
        "income_tax_payer": False,
    }
    values.update(changes)
    return Profile(**values)


def test_sym_eligible_when_all_conditions_met():
    result = evaluate_scheme(scheme_by_id("pm-sym"), sym_profile())
    assert result["status"] == "Eligible"


@pytest.mark.parametrize(
    "field",
    ["epfo_covered", "esic_covered", "nps_covered", "income_tax_payer"],
)
def test_sym_fails_when_covered_or_tax_payer(field):
    result = evaluate_scheme(scheme_by_id("pm-sym"), sym_profile(**{field: True}))
    assert result["status"] == "Not Eligible"
    assert len(result["failed_conditions"]) == 1


def test_sym_age_and_income_limits():
    scheme = scheme_by_id("pm-sym")
    assert evaluate_scheme(scheme, sym_profile(age=40))["status"] == "Eligible"
    assert evaluate_scheme(scheme, sym_profile(age=41))["status"] == "Not Eligible"
    assert (
        evaluate_scheme(scheme, sym_profile(monthly_income=15000))["status"]
        == "Eligible"
    )
    assert (
        evaluate_scheme(scheme, sym_profile(monthly_income=15001))["status"]
        == "Not Eligible"
    )


# ---------- PMEGP ----------


def test_pmegp_is_never_assessed():
    result = evaluate_scheme(scheme_by_id("pmegp"), Profile(goal="business", age=30))
    assert result["status"] == "Not Assessed"
    assert result["matched_conditions"] == []
    assert result["failed_conditions"] == []


# ---------- Goal filtering and the recommend endpoint ----------


@pytest.mark.parametrize("goal", sorted(GOAL_TO_SCHEME_IDS))
def test_goal_returns_only_its_own_scheme(goal):
    response = recommend_schemes(Profile(goal=goal))
    returned_ids = {item["id"] for item in response["recommendations"]}
    assert returned_ids == GOAL_TO_SCHEME_IDS[goal]


def test_recommend_requires_a_goal():
    with pytest.raises(HTTPException) as error:
        recommend_schemes(Profile())
    assert error.value.status_code == 422


def test_recommendation_includes_documents_benefits_and_steps():
    response = recommend_schemes(Profile(goal="education"))
    item = response["recommendations"][0]
    assert item["documents"]["mandatory"]
    assert item["benefits"]
    assert item["application_steps"]
    assert item["official_apply_url"].startswith("https://")


# ---------- Integrity of schemes.json ----------


def profile_field_names():
    fields = getattr(Profile, "model_fields", None) or Profile.__fields__
    return set(fields)


@pytest.mark.parametrize("scheme", load_schemes(), ids=lambda s: s["id"])
def test_scheme_has_required_fields(scheme):
    for key in (
        "id",
        "name",
        "category",
        "official_source_url",
        "last_verified",
        "benefits",
        "documents",
        "application_steps",
        "sources",
    ):
        assert scheme.get(key), f"{scheme['id']} is missing {key}"

    assert "mandatory" in scheme["documents"]
    assert "conditional" in scheme["documents"]


@pytest.mark.parametrize("scheme", load_schemes(), ids=lambda s: s["id"])
def test_scheme_rules_are_well_formed(scheme):
    fields = profile_field_names()

    if scheme.get("assessable", False):
        assert scheme["rules"], f"{scheme['id']} is assessable but has no rules"
        assert scheme.get("explanation")
    else:
        assert scheme["rules"] == []
        assert scheme.get("not_assessed_reason")

    for rule in scheme["rules"]:
        assert rule["operator"] in SUPPORTED_OPERATORS
        assert rule["field"] in fields
        assert rule["label"].strip()

        if rule["operator"] == "between":
            assert len(rule["value"]) == 2
        if rule["operator"] in {"gt", "gte", "lt", "lte"}:
            assert isinstance(rule["value"], (int, float))
        if rule["operator"] == "in":
            assert all(v == v.lower() for v in rule["value"])

        condition = rule.get("applies_when")
        if condition:
            assert condition["field"] in fields
            assert all(v == v.lower() for v in condition["in"])


def test_every_goal_maps_to_schemes_that_exist():
    existing_ids = {scheme["id"] for scheme in load_schemes()}
    for goal, ids in GOAL_TO_SCHEME_IDS.items():
        assert ids <= existing_ids, f"Goal {goal} points to a missing scheme"
