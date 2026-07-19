from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, TypedDict

from medical_desert.domain.models import CapabilityId

SOURCE_BUNDLE_ID = "virtue-dais-2026-profiled-2026-07-19"
EVIDENCE_SNAPSHOT_ID = "darbhanga-demo-core-v1"
POLICY_VERSION = "capability-policy-2026-07-19"
SCORING_VERSION = "documentary-scoring-2026-07-19"
CROSSWALK_VERSION = "district-crosswalk-demo-2026-07-19"
MACHINE_ASSESSED_AT = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)

DARbhanga_CENTER = (26.1542, 85.8918)


class DemoFacility(TypedDict):
    facility_id: str
    name: str
    city: str
    district: str
    state: str
    pin: str
    latitude: float
    longitude: float
    description: str
    source_snapshot_id: str
    observed_fields: dict[str, Any]
    geography_conflict: str | None


def _facility(
    facility_id: str,
    name: str,
    city: str,
    pin: str,
    latitude: float,
    longitude: float,
    *,
    description: str,
    observed_fields: dict[str, Any],
    geography_conflict: str | None = None,
) -> DemoFacility:
    return {
        "facility_id": facility_id,
        "name": name,
        "city": city,
        "district": "Darbhanga",
        "state": "Bihar",
        "pin": pin,
        "latitude": latitude,
        "longitude": longitude,
        "description": description,
        "source_snapshot_id": SOURCE_BUNDLE_ID,
        "observed_fields": observed_fields,
        "geography_conflict": geography_conflict,
    }


FACILITIES: list[DemoFacility] = [
    _facility(
        "73aa5a82-8247-4f4d-83d6-f0b512c279d4",
        "Benipur Sub-Divisional Hospital",
        "Benipur",
        "847103",
        26.0597725,
        86.1518250,
        description="Sub-divisional hospital with documented staffing and resource limitations.",
        observed_fields={
            "specialties": ["internalMedicine", "pediatrics", "orthopedicSurgery"],
            "capabilities": ["Emergency and inpatient care are not directly documented."],
        },
    ),
    _facility(
        "3dd77c71-8a4f-4030-be7d-a1058b035d49",
        "Darbhanga Children Hospital",
        "Darbhanga",
        "846001",
        25.9792519,
        85.9570770,
        description="Pediatric and neonatal hospital with a 24/7 emergency claim.",
        observed_fields={
            "specialties": ["pediatrics", "emergencyMedicine", "gynecologyAndObstetrics"],
            "capabilities": ["Has 24/7 emergency care", "Provides newborn intensive care"],
        },
    ),
    _facility(
        "b69b988a-1179-44df-8349-e0d632ebfb83",
        "Darbhanga Medical College",
        "Laheriasarai",
        "846003",
        26.1700020,
        85.8999939,
        description="Government medical college and hospital in Darbhanga.",
        observed_fields={
            "specialties": [
                "emergencyMedicine",
                "generalSurgery",
                "gynecologyAndObstetrics",
                "radiology",
            ],
            "procedures": [
                "Performs surgical procedures in major and minor operation theatres",
                "Provides CT imaging services using City Scan facilities",
            ],
            "equipment": ["CT scanner", "MRI scanner", "On-site Blood Bank"],
            "capabilities": [
                "Emergency services are available",
                "Radiology department is available",
            ],
        },
    ),
    _facility(
        "7ada90ef-2c08-442f-ad2f-283360f27582",
        "Dr. Global Healthcare & Diabetes Centre (Dr. Naween Kumar)",
        "Darbhanga",
        "846004",
        26.1626968,
        85.8975067,
        description="Diabetes specialty centre with outpatient and diagnostic claims.",
        observed_fields={
            "specialties": ["cardiology", "endocrinologyAndDiabetesAndMetabolism"],
            "equipment": ["ICU facility", "Trauma care facility"],
        },
    ),
    _facility(
        "144d7908-e83b-45de-99f9-c52779fd8d38",
        "I.B.Smriti Arogya Sadan",
        "Darbhanga",
        "846004",
        26.1517239,
        85.9033508,
        description="Maternal, pediatric, neonatal, and general surgery claims.",
        observed_fields={
            "specialties": ["generalSurgery", "gynecologyAndObstetrics", "radiology"],
            "procedures": ["Provides laparoscopic surgery", "Provides ultrasound imaging"],
            "capabilities": ["Emergency department available", "Maternity specialization"],
        },
    ),
    _facility(
        "d5e1df16-5ee9-4ac3-a124-663d2b787f2f",
        "Lifecare Hospital",
        "Siwan",
        "846001",
        26.1954556,
        84.3446960,
        description="Source record names Siwan while its PIN joins to the Darbhanga demo slice.",
        observed_fields={
            "specialties": ["radiology", "internalMedicine"],
            "capabilities": [
                "Located in Civil Lines Amlori, Siwan",
                "Provides 24/7 healthcare services",
            ],
            "quality_signals": [
                {
                    "code": "pin_coordinate_city_conflict",
                    "severity": "high",
                    "detail": (
                        "City is Siwan and longitude is 84.3447, inconsistent with the "
                        "Darbhanga PIN-derived assignment."
                    ),
                }
            ],
        },
        geography_conflict=(
            "PIN 846001 maps into the selected Darbhanga slice, but the source city is Siwan "
            "and coordinates are 26.1955, 84.3447. Excluded from distance aggregation."
        ),
    ),
    _facility(
        "9ae85ea5-e395-4b40-a2fc-5b880afc00a1",
        "Panna Uro & ENT Hospital",
        "Laheriasarai",
        "846003",
        26.1268997,
        85.9041290,
        description="Urology and ENT hospital with laparoscopic and general surgery claims.",
        observed_fields={
            "specialties": ["urology", "otolaryngology", "generalSurgery"],
            "procedures": ["Offers laparoscopic surgery services"],
        },
    ),
    _facility(
        "b668392a-bc18-4bee-b17e-0155f07e966a",
        "Paras Global Darbhanga",
        "Darbhanga",
        "846003",
        26.1364288,
        85.9082489,
        description="Multispecialty hospital with emergency surgery and advanced imaging claims.",
        observed_fields={
            "specialties": ["emergencyMedicine", "generalSurgery", "radiology"],
            "procedures": [
                "Provides 24/7 emergency and trauma care",
                "Emergency surgeries are offered at Paras Health, Darbhanga",
            ],
            "equipment": ["MRI scanner", "CT scanner", "PET-CT scanner on-site"],
        },
    ),
    _facility(
        "50cc6772-eaaa-4463-a3de-47e2b95be1c2",
        "Parmarthi Dental Clinic",
        "Laheriasarai",
        "846004",
        26.1627083,
        85.8975067,
        description="Dental clinic.",
        observed_fields={
            "specialties": ["dentistry"],
            "procedures": ["Performs root canal therapy"],
        },
    ),
    _facility(
        "5e0b96cf-e221-4e1f-bd1f-e9b49d3eca7e",
        "R. B. Memorial Hospital",
        "Darbhanga",
        "846003",
        26.1272755,
        85.9038086,
        description="Private multispecialty hospital with emergency and general surgery evidence.",
        observed_fields={
            "specialties": ["generalSurgery", "emergencyMedicine", "gynecologyAndObstetrics"],
            "procedures": [
                "General surgery procedures are offered",
                "Emergency medical interventions are provided as part of 24x7 emergency care",
            ],
            "equipment": ["Modern Operation Theatre", "ICU facilities", "NICU facilities"],
        },
    ),
    _facility(
        "bb81f856-5599-4d07-a475-8134981cbedd",
        "Sarjug Dental College & Hospital",
        "Laheriasarai",
        "846003",
        26.1199780,
        85.9002686,
        description="Dental college and hospital.",
        observed_fields={"specialties": ["dentistry", "oralAndMaxillofacialSurgery"]},
    ),
    _facility(
        "b3796a39-9013-49fe-9068-e36c933fc49f",
        "Shyama Surgical Sansthan",
        "Darbhanga",
        "846004",
        26.1571598,
        85.8993988,
        description="Surgical hospital with emergency and inpatient service claims.",
        observed_fields={
            "specialties": ["generalSurgery", "orthopedicSurgery"],
            "procedures": ["Orthopaedic and general surgery procedures are offered"],
            "capabilities": ["Offers emergency and inpatient services"],
        },
    ),
    _facility(
        "4ddde88c-fb72-4ed5-bfa0-8bf647bb3044",
        "Skin Hair Laser Clinic",
        "Purnea",
        "846004",
        25.7816124,
        87.4887695,
        description="Source record names Purnea while its PIN joins to the Darbhanga demo slice.",
        observed_fields={
            "specialties": ["dermatology", "gynecologyAndObstetrics"],
            "capabilities": ["Specializes in obstetrics, gynecology, and women's health"],
            "quality_signals": [
                {
                    "code": "pin_coordinate_city_conflict",
                    "severity": "high",
                    "detail": (
                        "City is Purnea and coordinates are 25.7816, 87.4888, inconsistent "
                        "with the Darbhanga PIN-derived assignment."
                    ),
                }
            ],
        },
        geography_conflict=(
            "PIN 846004 maps into the selected Darbhanga slice, but the source city is Purnea "
            "and coordinates are 25.7816, 87.4888. Excluded from distance aggregation."
        ),
    ),
    _facility(
        "e6bdef2d-60e2-4732-bfd1-e736f7a8e5a8",
        "Smile Dental Clinic",
        "Darbhanga",
        "846001",
        26.1276054,
        85.8922348,
        description="Dental clinic with dental X-ray evidence.",
        observed_fields={
            "specialties": ["dentistry"],
            "procedures": ["Offers X-ray imaging services"],
        },
    ),
    _facility(
        "2805f221-586d-4921-b330-08f44ffc4eb1",
        "Soni Child Care Centre",
        "Darbhanga",
        "846003",
        26.1290035,
        85.9052429,
        description="Child care centre with a documented seven-bed NICU claim.",
        observed_fields={
            "specialties": ["pediatrics", "neonatologyPerinatalMedicine"],
            "equipment": ["Neonatal incubator", "NICU bed labeled 'NICU BED-7'"],
        },
    ),
]

FACILITY_BY_ID = {facility["facility_id"]: facility for facility in FACILITIES}

SUPPORTED: dict[CapabilityId, set[str]] = {
    CapabilityId.MATERNAL_EMERGENCY: set(),
    CapabilityId.EMERGENCY_SURGERY: {
        "b69b988a-1179-44df-8349-e0d632ebfb83",
        "b668392a-bc18-4bee-b17e-0155f07e966a",
        "5e0b96cf-e221-4e1f-bd1f-e9b49d3eca7e",
    },
    CapabilityId.ADVANCED_IMAGING: {
        "b69b988a-1179-44df-8349-e0d632ebfb83",
        "b668392a-bc18-4bee-b17e-0155f07e966a",
    },
}

GEOGRAPHIES: list[dict[str, Any]] = [
    {
        "geography_id": "state:br",
        "geography_type": "state",
        "name": "Bihar",
        "state": "Bihar",
        "metadata": {"demo_scope": True},
    },
    {
        "geography_id": "district:br:darbhanga",
        "geography_type": "district",
        "name": "Darbhanga",
        "state": "Bihar",
        "district": "Darbhanga",
        "metadata": {
            "analysis_origin_type": "postal_reference_point",
            "postal_reference_method": "versioned median of valid post-office coordinates",
        },
    },
    *[
        {
            "geography_id": f"pin:{pin}",
            "geography_type": "pin",
            "name": pin,
            "state": "Bihar",
            "district": "Darbhanga",
            "pin": pin,
            "metadata": {
                "analysis_origin_type": "postal_reference_point",
                "not_a_centroid": True,
            },
        }
        for pin in sorted({str(facility["pin"]) for facility in FACILITIES})
    ],
    {
        "geography_id": "city:darbhanga",
        "geography_type": "city",
        "name": "Darbhanga",
        "state": "Bihar",
        "district": "Darbhanga",
        "selectable": False,
        "unavailable_reason": "City normalization quality has not passed the G1 activation gate.",
        "metadata": {},
    },
]

NFHS_CONTEXT = {
    "district_id": "district:br:darbhanga",
    "district": "Darbhanga",
    "state": "Bihar",
    "survey_context_availability": "matched",
    "crosswalk_version": CROSSWALK_VERSION,
    "limitations": [
        "NFHS-5 values are district survey estimates, not facility evidence.",
        "Survey sample counts are not district population denominators.",
        "These indicators do not change documentary support or regional classification.",
    ],
    "indicators": [
        {
            "indicator_id": "four_plus_anc",
            "label": "Mothers with at least four antenatal care visits",
            "raw_value": "24.9",
            "numeric_value": 24.9,
            "qualifier": "standard",
        },
        {
            "indicator_id": "institutional_births",
            "label": "Institutional births",
            "raw_value": "69.9",
            "numeric_value": 69.9,
            "qualifier": "standard",
        },
        {
            "indicator_id": "women_anaemia",
            "label": "Women age 15-49 with anaemia",
            "raw_value": "60.8",
            "numeric_value": 60.8,
            "qualifier": "standard",
        },
    ],
}


def evidence_id(facility_id: str, capability_id: CapabilityId, ordinal: int) -> str:
    return f"ev-{sha256(f'{facility_id}:{capability_id}:{ordinal}'.encode()).hexdigest()[:16]}"


def evidence_texts(facility: DemoFacility, capability_id: CapabilityId) -> list[tuple[str, str]]:
    fields = facility["observed_fields"]
    if capability_id == CapabilityId.EMERGENCY_SURGERY:
        values = [
            *(
                ("specialties", value)
                for value in fields.get("specialties", [])
                if value in {"emergencyMedicine", "generalSurgery"}
            ),
            *(
                ("procedures", value)
                for value in fields.get("procedures", [])
                if "emergency" in value.lower() or "general surgery" in value.lower()
            ),
        ]
        return values[:4]
    if capability_id == CapabilityId.ADVANCED_IMAGING:
        return [
            ("equipment", value)
            for value in fields.get("equipment", [])
            if "ct scanner" in value.lower() or "mri scanner" in value.lower()
        ][:4]
    return [
        ("specialties", value)
        for value in fields.get("specialties", [])
        if value == "gynecologyAndObstetrics"
    ][:2]


def default_geography_review_items() -> list[dict[str, Any]]:
    return [
        {
            "facility_id": facility["facility_id"],
            "capability_id": CapabilityId.MATERNAL_EMERGENCY,
            "question": "Resolve high-severity PIN, city, and coordinate conflict.",
            "why_it_matters": facility["geography_conflict"],
            "affected_region_ids": ["district:br:darbhanga"],
            "affected_scenario_ids": [],
            "classification_flip_potential": 0.8,
            "map_cells_or_regions_affected": 0.8,
            "active_scenario_references": 0.2,
            "evidence_staleness": 0.3,
            "unresolved_contradiction_severity": 1.0,
            "evidence_ids": [],
            "recommended_action": (
                "Confirm the facility identity and authoritative coordinates before allowing "
                "the record into distance or district aggregation."
            ),
        }
        for facility in FACILITIES
        if facility["geography_conflict"] is not None
    ]
