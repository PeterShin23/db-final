#!/usr/bin/env python3
"""Generate deterministic synthetic data for the Patient Signal Workbench POC.

The output is intentionally small enough for Databricks Free Edition while still
containing a visible business pattern. All people and identifiers are fictional.
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import median


SEED = 20_260_628
PATIENT_COUNT = 5_000
STORY_PATIENT_COUNT = 600
JOURNEY_EVENTS_PER_PATIENT = 6
FEEDBACK_COUNT = 4_000
STORY_FEEDBACK_COUNT = 1_200
GROUND_TRUTH_COUNT = 500
ANNOTATION_COUNT = 200

DATA_START = date(2025, 12, 30)
DATA_END = date(2026, 6, 27)
STORY_START = date(2026, 5, 1)
STORY_PRESCRIPTION_END = date(2026, 5, 25)

OUTPUT_ROOT = Path(__file__).resolve().parents[1] / ".data"
RAW_DIR = OUTPUT_ROOT / "raw"
VALIDATION_DIR = OUTPUT_ROOT / "validation"

THERAPIES = {
    "Therapy A": {
        "therapeutic_area": "Immunology",
        "annual_net_value_per_start_usd": 18_000,
    },
    "Therapy B": {
        "therapeutic_area": "Neurology",
        "annual_net_value_per_start_usd": 14_500,
    },
    "Therapy C": {
        "therapeutic_area": "Rare Disease",
        "annual_net_value_per_start_usd": 22_000,
    },
}

FIRST_NAMES = [
    "Avery", "Jordan", "Taylor", "Morgan", "Riley", "Casey", "Cameron",
    "Quinn", "Reese", "Parker", "Alex", "Jamie", "Drew", "Skyler",
    "Robin", "Emerson", "Sage", "Rowan", "Dakota", "Hayden",
]
LAST_NAMES = [
    "Adams", "Bennett", "Carter", "Diaz", "Ellis", "Foster", "Garcia",
    "Hughes", "Irwin", "Johnson", "Kim", "Lopez", "Mitchell", "Nguyen",
    "Owens", "Patel", "Reed", "Singh", "Turner", "Williams",
]
REGION_ZIPS = {
    "Northeast": ["02108", "10001", "19103", "02139", "11201"],
    "South": ["30303", "33130", "37203", "75201", "28202"],
    "Midwest": ["60601", "48226", "55401", "43215", "63101"],
    "West": ["90012", "94105", "98101", "80202", "85004"],
}


def weighted_choice(rng: random.Random, values: list[str], weights: list[int]) -> str:
    return rng.choices(values, weights=weights, k=1)[0]


def random_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def iso_timestamp(day: date, hour: int = 12) -> str:
    return datetime.combine(day, time(hour, 0), tzinfo=timezone.utc).isoformat()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def make_patients(rng: random.Random) -> tuple[list[dict], dict[str, dict], set[str]]:
    story_numbers = set(rng.sample(range(1, PATIENT_COUNT + 1), STORY_PATIENT_COUNT))
    patients: list[dict] = []
    patient_context: dict[str, dict] = {}
    story_patient_ids: set[str] = set()

    for number in range(1, PATIENT_COUNT + 1):
        patient_id = f"MPS-P{number:06d}"
        is_story = number in story_numbers

        if is_story:
            therapy = "Therapy A"
            region = "Northeast"
            payer_type = "Commercial"
            prescription_date = random_date(rng, STORY_START, STORY_PRESCRIPTION_END)
            story_patient_ids.add(patient_id)
        else:
            therapy = weighted_choice(
                rng, ["Therapy A", "Therapy B", "Therapy C"], [45, 32, 23]
            )
            region = weighted_choice(
                rng, ["Northeast", "South", "Midwest", "West"], [30, 28, 22, 20]
            )
            payer_type = weighted_choice(
                rng, ["Commercial", "Medicare", "Medicaid", "Self-pay"], [55, 28, 12, 5]
            )
            prescription_date = random_date(rng, DATA_START, STORY_PRESCRIPTION_END)
            # Keep the injected cohort unambiguous while retaining recent data elsewhere.
            if (
                therapy == "Therapy A"
                and region == "Northeast"
                and payer_type == "Commercial"
                and prescription_date >= STORY_START
            ):
                region = "Midwest"

        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        birth_date = random_date(rng, date(1942, 1, 1), date(2007, 12, 31))
        diagnosis_date = prescription_date - timedelta(days=rng.randint(14, 240))
        member_id = f"MP-{number:08d}"
        phone = f"+1-202-555-{number % 10_000:04d}"

        patient = {
            "patient_id": patient_id,
            "member_id": member_id,
            "full_name": f"{first_name} {last_name}",
            "date_of_birth": birth_date.isoformat(),
            "postal_code": rng.choice(REGION_ZIPS[region]),
            "phone_number": phone,
            "region": region,
            "payer_type": payer_type,
            "therapy": therapy,
            "diagnosis_date": diagnosis_date.isoformat(),
            "analytics_consent": "true",
        }
        patients.append(patient)
        patient_context[patient_id] = {
            **patient,
            "first_name": first_name,
            "last_name": last_name,
            "prescription_date": prescription_date,
            "is_story": is_story,
        }

    return patients, patient_context, story_patient_ids


def make_journeys(
    rng: random.Random, patient_context: dict[str, dict]
) -> tuple[list[dict], dict[str, dict]]:
    rows: list[dict] = []
    outcomes: dict[str, dict] = {}
    event_number = 1

    for patient_id, patient in patient_context.items():
        is_story = patient["is_story"]
        prescription_date = patient["prescription_date"]
        pa_wait = rng.randint(7, 12) if is_story else rng.randint(2, 5)
        denied = rng.random() < (0.20 if is_story else 0.08)
        appeal_wait = rng.randint(3, 7) if denied else 0
        appeal_approved = denied and rng.random() < (0.55 if is_story else 0.65)
        cleared = not denied or appeal_approved
        specialty_wait = rng.randint(4, 8) if is_story else rng.randint(1, 4)
        started = cleared and rng.random() < (0.64 if is_story else 0.78)

        payer_decision_date = prescription_date + timedelta(days=1 + pa_wait)
        follow_up_date = payer_decision_date + timedelta(days=appeal_wait)
        pharmacy_date = follow_up_date + timedelta(days=specialty_wait)
        outcome_date = pharmacy_date + timedelta(days=rng.randint(0, 2))
        total_delay = (outcome_date - prescription_date).days

        if started:
            final_barrier = ""
        elif not cleared:
            final_barrier = "payer_denial"
        elif is_story:
            final_barrier = weighted_choice(
                rng,
                ["prior_authorization", "specialty_pharmacy_delay", "out_of_pocket_cost", "scheduling"],
                [50, 30, 12, 8],
            )
        else:
            final_barrier = weighted_choice(
                rng,
                ["out_of_pocket_cost", "prior_authorization", "patient_concern", "scheduling"],
                [35, 25, 22, 18],
            )

        stages = [
            (
                1,
                prescription_date,
                "prescription_written",
                "written",
                0,
                "",
                "Provider EHR",
                0,
            ),
            (
                2,
                prescription_date + timedelta(days=1),
                "prior_authorization_submitted",
                "submitted",
                1,
                "",
                "Hub services",
                0,
            ),
            (
                3,
                payer_decision_date,
                "payer_decision",
                "denied" if denied else "approved",
                pa_wait,
                "prior_authorization" if is_story or denied else "",
                "Payer portal",
                0,
            ),
            (
                4,
                follow_up_date,
                "appeal_follow_up",
                ("approved" if appeal_approved else "denied") if denied else "not_required",
                appeal_wait,
                "payer_denial" if denied else "",
                "Hub services",
                0,
            ),
            (
                5,
                pharmacy_date,
                "specialty_pharmacy_coordination",
                "delayed" if specialty_wait >= 5 else "ready",
                specialty_wait,
                "specialty_pharmacy_delay" if specialty_wait >= 5 else "",
                "Specialty pharmacy",
                0,
            ),
            (
                6,
                outcome_date,
                "treatment_outcome",
                "started" if started else "abandoned",
                total_delay,
                final_barrier,
                "Patient services",
                0 if started else THERAPIES[patient["therapy"]]["annual_net_value_per_start_usd"],
            ),
        ]

        for stage_order, day, stage, outcome, delay, barrier, source, value_at_risk in stages:
            rows.append(
                {
                    "event_id": f"MPS-E{event_number:07d}",
                    "patient_id": patient_id,
                    "event_timestamp": iso_timestamp(day, 14),
                    "stage_order": stage_order,
                    "journey_stage": stage,
                    "event_outcome": outcome,
                    "delay_days": delay,
                    "barrier_category": barrier,
                    "source_system": source,
                    "therapy": patient["therapy"],
                    "region": patient["region"],
                    "payer_type": patient["payer_type"],
                    "estimated_annual_value_at_risk_usd": value_at_risk,
                }
            )
            event_number += 1

        outcomes[patient_id] = {
            "started": started,
            "total_delay": total_delay,
            "outcome_date": outcome_date,
            "final_barrier": final_barrier,
            "is_story": is_story,
        }

    return rows, outcomes


BARRIER_DETAILS = {
    "prior_authorization": {
        "stage": "prior_authorization",
        "call": [
            "the insurer still has not approved the prior authorization for {therapy}. The request has been open for {days} days and the planned start date may be missed",
            "the prior authorization for {therapy} is still pending after {days} days. The patient wants to know when treatment can begin",
            "additional paperwork was requested for the {therapy} authorization, creating a {days}-day delay",
        ],
        "survey": [
            "The prior authorization process for {therapy} has taken {days} days and I still do not know when treatment can begin.",
            "We submitted the authorization paperwork for {therapy}, but after {days} days there is still no decision.",
        ],
    },
    "specialty_pharmacy_delay": {
        "stage": "specialty_pharmacy_coordination",
        "call": [
            "the specialty pharmacy has not scheduled shipment of {therapy}. The handoff has added {days} days",
            "the prescription for {therapy} appears stuck between the hub and specialty pharmacy, delaying delivery by {days} days",
        ],
        "survey": [
            "The specialty pharmacy has called twice but {therapy} still has not shipped after {days} days.",
            "I was approved for {therapy}, but coordination with the specialty pharmacy added {days} days.",
        ],
    },
    "payer_denial": {
        "stage": "appeal_follow_up",
        "call": [
            "coverage for {therapy} was denied and an appeal is now required. Treatment has been delayed {days} days",
            "the payer denied {therapy} despite the submitted documentation, and the care team is requesting an urgent appeal",
        ],
        "survey": [
            "My insurance denied {therapy}, and I have already waited {days} days for the appeal.",
            "The payer rejection for {therapy} is preventing treatment from starting.",
        ],
    },
    "out_of_pocket_cost": {
        "stage": "benefit_verification",
        "call": [
            "the estimated out-of-pocket cost for {therapy} is ${cost}, which the patient cannot afford without assistance",
            "the patient paused the {therapy} start after learning the monthly cost would be ${cost}",
        ],
        "survey": [
            "My expected cost for {therapy} is ${cost}, so I may not be able to start treatment.",
            "I need financial assistance because the quoted cost for {therapy} is ${cost}.",
        ],
    },
    "step_therapy": {
        "stage": "payer_decision",
        "call": [
            "the plan requires another medicine to be tried before {therapy}, even though the clinician requested an exception",
            "a step-therapy requirement is blocking access to {therapy} and the office is preparing supporting documentation",
        ],
        "survey": [
            "Insurance says I must try another treatment before {therapy} can be covered.",
            "The step-therapy rule is delaying the treatment my physician selected.",
        ],
    },
    "scheduling": {
        "stage": "treatment_scheduling",
        "call": [
            "the earliest available treatment appointment is {days} days away, later than the care team recommended",
            "the patient has approval for {therapy} but cannot find an infusion appointment for {days} days",
        ],
        "survey": [
            "I have approval for {therapy}, but the first appointment is {days} days away.",
            "Scheduling the treatment visit has taken longer than the insurance approval.",
        ],
    },
    "patient_concern": {
        "stage": "treatment_decision",
        "call": [
            "the patient wants more information about {therapy} before deciding whether to start",
            "the patient is hesitant to begin {therapy} and requested a follow-up conversation with the care team",
        ],
        "survey": [
            "I want clearer information about what to expect before I start {therapy}.",
            "I am not ready to begin {therapy} until I can discuss my concerns with the care team.",
        ],
    },
    "no_barrier": {
        "stage": "treatment_outcome",
        "call": [
            "the patient received {therapy} on schedule and reported that the support process was clear",
            "approval and shipment for {therapy} were completed without an access issue",
        ],
        "survey": [
            "The approval and start process for {therapy} was straightforward.",
            "The support team helped me begin {therapy} on time.",
        ],
    },
}


def make_feedback_text(
    rng: random.Random,
    source: str,
    speaker_type: str,
    barrier: str,
    patient: dict,
    days: int,
    contains_sensitive_data: bool,
) -> str:
    source_key = "call" if source == "Call center" else "survey"
    template = rng.choice(BARRIER_DETAILS[barrier][source_key])
    body = template.format(
        therapy=patient["therapy"],
        days=max(days, 2),
        cost=rng.choice([450, 700, 950, 1_200, 1_800]),
    )
    if source == "Call center":
        body = f"{speaker_type} reports that {body}."
    if contains_sensitive_data:
        body = (
            f"Patient {patient['full_name']}, member {patient['member_id']}, "
            f"DOB {patient['date_of_birth']}: {body}"
        )
    return body


def make_feedback(
    rng: random.Random,
    patient_context: dict[str, dict],
    story_patient_ids: set[str],
    outcomes: dict[str, dict],
) -> tuple[list[dict], dict[str, dict], list[str], list[str]]:
    story_ids = sorted(story_patient_ids)
    regular_ids = sorted(set(patient_context) - story_patient_ids)
    rows: list[dict] = []
    labels: dict[str, dict] = {}
    story_feedback_ids: list[str] = []
    regular_feedback_ids: list[str] = []

    for number in range(1, FEEDBACK_COUNT + 1):
        is_story = number <= STORY_FEEDBACK_COUNT
        patient_id = rng.choice(story_ids if is_story else regular_ids)
        patient = patient_context[patient_id]
        journey = outcomes[patient_id]
        source = weighted_choice(rng, ["Call center", "Survey"], [63, 37])
        speaker_type = weighted_choice(rng, ["Patient", "Caregiver", "Physician"], [68, 12, 20])

        if is_story:
            barrier = weighted_choice(
                rng,
                [
                    "prior_authorization",
                    "specialty_pharmacy_delay",
                    "payer_denial",
                    "out_of_pocket_cost",
                    "step_therapy",
                    "scheduling",
                    "no_barrier",
                ],
                [45, 25, 10, 8, 5, 4, 3],
            )
        else:
            barrier = weighted_choice(
                rng,
                [
                    "out_of_pocket_cost",
                    "prior_authorization",
                    "specialty_pharmacy_delay",
                    "payer_denial",
                    "step_therapy",
                    "scheduling",
                    "patient_concern",
                    "no_barrier",
                ],
                [22, 15, 12, 10, 10, 9, 8, 14],
            )

        if barrier == "no_barrier":
            sentiment = weighted_choice(rng, ["positive", "neutral"], [80, 20])
            urgency = "low"
        else:
            sentiment = weighted_choice(rng, ["negative", "neutral"], [88, 12])
            urgency = (
                weighted_choice(rng, ["high", "medium"], [65, 35])
                if barrier in {"payer_denial", "prior_authorization"}
                else weighted_choice(rng, ["high", "medium", "low"], [20, 65, 15])
            )

        contains_sensitive_data = rng.random() < 0.12
        if is_story:
            feedback_day = random_date(rng, STORY_START, DATA_END)
        else:
            lower_bound = max(DATA_START, patient["prescription_date"])
            upper_bound = min(DATA_END, journey["outcome_date"] + timedelta(days=14))
            feedback_day = random_date(rng, lower_bound, max(lower_bound, upper_bound))

        feedback_id = f"MPS-F{number:06d}"
        text = make_feedback_text(
            rng,
            source,
            speaker_type,
            barrier,
            patient,
            journey["total_delay"],
            contains_sensitive_data,
        )
        rows.append(
            {
                "feedback_id": feedback_id,
                "patient_id": patient_id,
                "feedback_timestamp": iso_timestamp(feedback_day, rng.randint(8, 19)),
                "source": source,
                "speaker_type": speaker_type,
                "therapy": patient["therapy"],
                "region": patient["region"],
                "payer_type": patient["payer_type"],
                "feedback_text": text,
            }
        )
        labels[feedback_id] = {
            "feedback_id": feedback_id,
            "expected_barrier_category": barrier,
            "expected_sentiment": sentiment,
            "expected_urgency": urgency,
            "expected_journey_stage": BARRIER_DETAILS[barrier]["stage"],
            "contains_sensitive_data": str(contains_sensitive_data).lower(),
            "expected_review_required": str(
                contains_sensitive_data or urgency == "high"
            ).lower(),
        }
        (story_feedback_ids if is_story else regular_feedback_ids).append(feedback_id)

    return rows, labels, story_feedback_ids, regular_feedback_ids


def make_validation_data(
    rng: random.Random,
    labels: dict[str, dict],
    feedback_rows: list[dict],
    story_feedback_ids: list[str],
    regular_feedback_ids: list[str],
) -> tuple[list[dict], list[dict]]:
    selected_ids = rng.sample(story_feedback_ids, GROUND_TRUTH_COUNT // 2) + rng.sample(
        regular_feedback_ids, GROUND_TRUTH_COUNT // 2
    )
    rng.shuffle(selected_ids)
    ground_truth = [labels[feedback_id] for feedback_id in selected_ids]

    feedback_by_id = {row["feedback_id"]: row for row in feedback_rows}
    annotation_ids = rng.sample(selected_ids, ANNOTATION_COUNT)
    annotations: list[dict] = []
    for number, feedback_id in enumerate(annotation_ids, start=1):
        label = labels[feedback_id]
        feedback_day = date.fromisoformat(
            feedback_by_id[feedback_id]["feedback_timestamp"][:10]
        )
        annotation_day = min(DATA_END, feedback_day + timedelta(days=rng.randint(1, 7)))
        status = weighted_choice(rng, ["validated", "needs_follow_up"], [85, 15])
        annotations.append(
            {
                "annotation_id": f"MPS-A{number:05d}",
                "feedback_id": feedback_id,
                "analyst_alias": rng.choice(["analyst_01", "analyst_02", "analyst_03", "analyst_04"]),
                "annotated_barrier_category": label["expected_barrier_category"],
                "annotated_sentiment": label["expected_sentiment"],
                "annotation_status": status,
                "annotation_note": (
                    "Escalate for source review."
                    if status == "needs_follow_up"
                    else "Barrier and sentiment confirmed from source text."
                ),
                "annotated_at": iso_timestamp(annotation_day, 16),
            }
        )
    return ground_truth, annotations


def calculate_story_metrics(
    patient_context: dict[str, dict],
    outcomes: dict[str, dict],
    labels: dict[str, dict],
    story_feedback_ids: list[str],
    regular_feedback_ids: list[str],
) -> dict:
    story_outcomes = [outcomes[pid] for pid, p in patient_context.items() if p["is_story"]]
    regular_outcomes = [outcomes[pid] for pid, p in patient_context.items() if not p["is_story"]]
    story_pa_share = sum(
        labels[fid]["expected_barrier_category"] == "prior_authorization"
        for fid in story_feedback_ids
    ) / len(story_feedback_ids)
    regular_pa_share = sum(
        labels[fid]["expected_barrier_category"] == "prior_authorization"
        for fid in regular_feedback_ids
    ) / len(regular_feedback_ids)
    story_abandoned = sum(not item["started"] for item in story_outcomes)
    baseline_abandonment_rate = 1 - (
        sum(item["started"] for item in regular_outcomes) / len(regular_outcomes)
    )
    excess_abandonments = max(
        0, round(story_abandoned - len(story_outcomes) * baseline_abandonment_rate)
    )

    return {
        "story_cohort_definition": (
            "Therapy A + Northeast + Commercial payer + prescription on/after 2026-05-01"
        ),
        "story_patient_count": len(story_outcomes),
        "comparison_patient_count": len(regular_outcomes),
        "story_start_rate": round(
            sum(item["started"] for item in story_outcomes) / len(story_outcomes), 4
        ),
        "comparison_start_rate": round(
            sum(item["started"] for item in regular_outcomes) / len(regular_outcomes), 4
        ),
        "story_median_days_to_outcome": median(item["total_delay"] for item in story_outcomes),
        "comparison_median_days_to_outcome": median(
            item["total_delay"] for item in regular_outcomes
        ),
        "story_prior_authorization_feedback_share": round(story_pa_share, 4),
        "comparison_prior_authorization_feedback_share": round(regular_pa_share, 4),
        "estimated_excess_patient_starts_at_risk": excess_abandonments,
        "estimated_incremental_annual_value_at_risk_usd": (
            excess_abandonments
            * THERAPIES["Therapy A"]["annual_net_value_per_start_usd"]
        ),
    }


def validate(
    patients: list[dict],
    journeys: list[dict],
    feedback: list[dict],
    annotations: list[dict],
    ground_truth: list[dict],
    story_metrics: dict,
) -> None:
    assert len(patients) == PATIENT_COUNT
    assert len(journeys) == PATIENT_COUNT * JOURNEY_EVENTS_PER_PATIENT
    assert len(feedback) == FEEDBACK_COUNT
    assert len(annotations) == ANNOTATION_COUNT
    assert len(ground_truth) == GROUND_TRUTH_COUNT

    patient_ids = {row["patient_id"] for row in patients}
    feedback_ids = {row["feedback_id"] for row in feedback}
    assert all(row["patient_id"] in patient_ids for row in journeys)
    assert all(row["patient_id"] in patient_ids for row in feedback)
    assert all(row["feedback_id"] in feedback_ids for row in ground_truth)
    assert all(row["feedback_id"] in feedback_ids for row in annotations)

    assert 0.52 <= story_metrics["story_start_rate"] <= 0.64
    assert 0.72 <= story_metrics["comparison_start_rate"] <= 0.80
    assert (
        story_metrics["story_median_days_to_outcome"]
        >= story_metrics["comparison_median_days_to_outcome"] + 8
    )
    assert (
        story_metrics["story_prior_authorization_feedback_share"]
        >= story_metrics["comparison_prior_authorization_feedback_share"] + 0.20
    )


def main() -> None:
    rng = random.Random(SEED)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    patients, patient_context, story_patient_ids = make_patients(rng)
    journeys, outcomes = make_journeys(rng, patient_context)
    feedback, labels, story_feedback_ids, regular_feedback_ids = make_feedback(
        rng, patient_context, story_patient_ids, outcomes
    )
    ground_truth, annotations = make_validation_data(
        rng, labels, feedback, story_feedback_ids, regular_feedback_ids
    )
    story_metrics = calculate_story_metrics(
        patient_context, outcomes, labels, story_feedback_ids, regular_feedback_ids
    )

    validate(
        patients, journeys, feedback, annotations, ground_truth, story_metrics
    )

    write_csv(RAW_DIR / "patients_raw.csv", list(patients[0]), patients)
    write_csv(RAW_DIR / "journey_events_raw.csv", list(journeys[0]), journeys)
    write_jsonl(RAW_DIR / "feedback_raw.jsonl", feedback)
    write_csv(
        RAW_DIR / "analyst_annotations_raw.csv", list(annotations[0]), annotations
    )
    therapy_rows = [
        {"therapy": therapy, **details} for therapy, details in THERAPIES.items()
    ]
    write_csv(RAW_DIR / "therapy_reference.csv", list(therapy_rows[0]), therapy_rows)
    write_csv(
        VALIDATION_DIR / "signal_ground_truth.csv",
        list(ground_truth[0]),
        ground_truth,
    )

    manifest = {
        "dataset": "Patient Signal Workbench synthetic POC data",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "all_people_and_identifiers_are_fictional": True,
        "date_range": {"start": DATA_START.isoformat(), "end": DATA_END.isoformat()},
        "files": {
            "raw/patients_raw.csv": len(patients),
            "raw/journey_events_raw.csv": len(journeys),
            "raw/feedback_raw.jsonl": len(feedback),
            "raw/analyst_annotations_raw.csv": len(annotations),
            "raw/therapy_reference.csv": len(therapy_rows),
            "validation/signal_ground_truth.csv": len(ground_truth),
        },
        "story_metrics": story_metrics,
        "category_counts": {
            "therapy": dict(Counter(row["therapy"] for row in patients)),
            "region": dict(Counter(row["region"] for row in patients)),
            "payer_type": dict(Counter(row["payer_type"] for row in patients)),
        },
    }
    (OUTPUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
