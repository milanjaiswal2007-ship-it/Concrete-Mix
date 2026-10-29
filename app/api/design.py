"""Mix design API — the core endpoint that runs the IS 10262 calculation."""

import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engine.concrete_type import SPECIAL_TYPES, detect_concrete_type
from app.engine.is10262 import design as is10262_design
from app.engine.parser import parse_problem
from app.engine.special_extract import extract_special_inputs
from app.engine.special_mix import run_special_mix_engine
from app.engine.type_schemas import TYPE_SCHEMAS, get_type_schema
from app.engine.validator import validate_inputs
from app.models import DesignSession
from app.rag.examples import ExampleManager
from app.database import SessionLocal

router = APIRouter(prefix="/api/design", tags=["design"])


def _get_example_manager() -> ExampleManager:
    return ExampleManager(SessionLocal)


@router.post("/parse")
def parse_only(request: Dict[str, Any]):
    """Endpoint for live front-end problem statement parsing.
    Returns extracted facts, assumptions, suggested parameters,
    and detected special concrete type in real-time.
    """
    text = request.get("problem_text", "")
    active_type = request.get("active_type") or request.get("concrete_type")

    type_info = detect_concrete_type(text)
    detected_type = type_info.get("type", "conventional")

    # If user has an active type explicitly selected (and not 'auto'), use it; otherwise use detected
    effective_type = active_type if (active_type and active_type != "auto") else detected_type

    if effective_type and effective_type != "conventional" and effective_type in SPECIAL_TYPES:
        extracted = extract_special_inputs(text, effective_type)
        extracted["detected_type"] = detected_type
        extracted["confidence"] = type_info.get("confidence", 0.0)
        extracted["matched_keywords"] = type_info.get("matched_keywords", [])
        extracted["runner_up"] = type_info.get("runner_up")
        return extracted
    else:
        parsed = parse_problem(text)
        parsed["concrete_type"] = "conventional"
        parsed["detected_type"] = detected_type
        parsed["confidence"] = type_info.get("confidence", 0.0)
        parsed["matched_keywords"] = type_info.get("matched_keywords", [])
        parsed["runner_up"] = type_info.get("runner_up")
        parsed["extracted_keys"] = list(parsed.get("parsed", {}).keys())
        parsed["clamped_keys"] = {}
        return parsed


@router.post("")
def create_design(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Run a concrete mix design calculation or reference proposal.

    Accepts either a ``problem_text`` (natural language) or structured
    inputs. If a special concrete type is detected or requested, routes
    to the literature-anchored special engine. Otherwise runs the
    statutory IS 10262:2019 calculation engine.
    """
    problem_text = request.get("problem_text", "")
    structured = {k: v for k, v in request.items() if k != "problem_text" and v is not None and v != ""}

    # Check for explicit or detected special concrete type
    explicit_type = request.get("concrete_type")
    special_type = None
    if explicit_type in SPECIAL_TYPES:
        special_type = explicit_type
    elif explicit_type not in ("conventional", "is10262", "opc"):
        detected = detect_concrete_type(problem_text)
        special_type = detected.get("type")

    # ── SPECIAL CONCRETE ROUTE ──────────────────────────────────────────────
    if special_type and special_type in SPECIAL_TYPES:
        schema = get_type_schema(special_type)
        valid_keys = {f["key"] for f in schema.get("fields", [])}
        sanitized_inputs = {k: v for k, v in structured.items() if k in valid_keys or k == "concrete_type"}
        try:
            special_res = run_special_mix_engine(
                problem_text=problem_text,
                ctype=special_type,
                user_inputs=sanitized_inputs,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail={
                "message": f"Special mix engine error: {e}",
                "concrete_type": special_type,
            })

        mgr = _get_example_manager()
        similar = mgr.get_similar_examples({"concrete_type": special_type, **sanitized_inputs}, top_k=3)

        session_id = str(uuid.uuid4())
        session = DesignSession(
            session_id=session_id,
            problem_text=problem_text,
            parsed_inputs_json=json.dumps({"concrete_type": special_type, **sanitized_inputs}, ensure_ascii=False, default=str),
            result_json=json.dumps(special_res, ensure_ascii=False, default=str),
            retrieved_examples_json=json.dumps(
                [{"external_id": s["external_id"], "similarity": s.get("similarity_score", 0)} for s in similar],
                ensure_ascii=False,
            ),
        )
        db.add(session)
        db.commit()

        return {
            "session_id": session_id,
            "parsed_inputs": {"concrete_type": special_type, **sanitized_inputs},
            "facts": [{"field": "concrete_type", "value": special_type, "source": f"Detected special concrete type '{special_type}'"}],
            "assumptions": [],
            "missing": [],
            "warnings": special_res.get("warnings", []),
            "result": special_res,
            "retrieved_examples": similar,
        }

    # ── CONVENTIONAL IS 10262 ROUTE (UNTOUCHED) ─────────────────────────────
    # ── Step 1: Parse natural language if provided ───────────────────────
    parsed_result = {"parsed": {}, "facts": [], "assumptions": [], "missing": [], "warnings": []}
    if problem_text:
        parsed_result = parse_problem(problem_text)

    # Merge: structured inputs explicitly override parsed values
    inputs = {**parsed_result["parsed"], **structured}

    # Handle SCM format from frontend
    if "scm" in inputs and inputs["scm"]:
        scm_list = []
        for item in inputs["scm"]:
            if isinstance(item, dict):
                scm_list.append((item["type"], item["percent"]))
            elif isinstance(item, (list, tuple)):
                scm_list.append(tuple(item))
        inputs["scm"] = scm_list

    # ── Step 2: Validate ─────────────────────────────────────────────────
    errors, warnings = validate_inputs(inputs)
    if errors:
        raise HTTPException(status_code=422, detail={
            "message": "Validation failed",
            "errors": errors,
            "warnings": warnings,
            "parsed_inputs": inputs,
            "facts": parsed_result["facts"],
            "assumptions": parsed_result["assumptions"],
            "missing": parsed_result["missing"],
        })

    all_warnings = parsed_result["warnings"] + warnings

    # ── Step 3: Check for missing required inputs with safe engineering fallbacks ──
    assumptions = list(parsed_result["assumptions"])
    if "exposure" not in inputs or inputs["exposure"] is None or inputs["exposure"] == "":
        inputs["exposure"] = "moderate"
        assumptions.append({"field": "exposure", "value": "moderate", "reason": "IS 456:2000 Table 3: Assumed standard 'Moderate' baseline exposure."})

    if "fck" not in inputs or inputs["fck"] is None or inputs["fck"] == "":
        inputs["fck"] = 25.0
        assumptions.append({"field": "fck", "value": 25.0, "reason": "Standard structural baseline grade M25 adopted."})

    # ── Step 4: Set defaults for optional inputs ─────────────────────────
    defaults = {
        "max_size": 20, "slump": 75, "zone": "II", "cement_grade": 43,
        "placement": "chute", "supervision": "good", "agg_type": "angular",
        "sg_cement": 3.15, "sg_fa": 2.65, "sg_ca": 2.74,
        "sg_fa_scm": 2.20, "sg_ggbs": 3.00, "sg_sf": 2.20, "sg_sp": 1.145,
        "abs_fa": 1.0, "abs_ca": 0.5, "fm_fa": 0.0, "fm_ca": 0.0,
        "pumped": False,
    }
    for k, v in defaults.items():
        if k not in inputs or inputs[k] is None:
            inputs[k] = v
            assumptions.append({"field": k, "value": v, "reason": f"Not specified; using default {v}"})

    # For high grade mixes (M55+), set advanced=True in design
    if inputs.get("fck", 0) >= 55:
        inputs["advanced"] = True

    # ── Step 5: Run calculation ──────────────────────────────────────────
    try:
        result = is10262_design(inputs)
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": f"Calculation engine error: {e}",
            "parsed_inputs": inputs,
        })

    # ── Step 6: Retrieve similar examples ────────────────────────────────
    mgr = _get_example_manager()
    similar = mgr.get_similar_examples(inputs, top_k=3)

    # ── Step 7: Save session ─────────────────────────────────────────────
    session_id = str(uuid.uuid4())
    session = DesignSession(
        session_id=session_id,
        problem_text=problem_text,
        parsed_inputs_json=json.dumps(inputs, ensure_ascii=False, default=str),
        result_json=json.dumps(result, ensure_ascii=False, default=str),
        retrieved_examples_json=json.dumps(
            [{"external_id": s["external_id"], "similarity": s.get("similarity_score", 0)}
             for s in similar],
            ensure_ascii=False,
        ),
    )
    db.add(session)
    db.commit()

    # ── Build response ───────────────────────────────────────────────────
    return {
        "session_id": session_id,
        "parsed_inputs": inputs,
        "facts": parsed_result["facts"],
        "assumptions": assumptions,
        "missing": parsed_result["missing"],
        "warnings": all_warnings,
        "result": result,
        "retrieved_examples": similar,
    }


@router.get("/{session_id}")
def get_design_session(session_id: str, db: Session = Depends(get_db)):
    """Retrieve a previously saved design session."""
    session = db.query(DesignSession).filter(DesignSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "problem_text": session.problem_text,
        "parsed_inputs": json.loads(session.parsed_inputs_json or "{}"),
        "result": json.loads(session.result_json or "{}"),
        "retrieved_examples": json.loads(session.retrieved_examples_json or "[]"),
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }
