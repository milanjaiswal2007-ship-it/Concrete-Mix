"""Import and manage the 100 solved mix design examples.

Handles JSONL ingestion, validation, similarity search, and CRUD
operations against the SQLite database.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Example

logger = logging.getLogger(__name__)


class ExampleManager:
    """Manages import, validation, and retrieval of solved examples."""

    def __init__(self, db_session_factory) -> None:
        self.db_factory = db_session_factory

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_from_jsonl(self, filepath: str) -> Dict[str, Any]:
        """Import examples from a JSONL file.

        Returns ``{imported, skipped, errors}`` summary.
        """
        imported = 0
        skipped = 0
        errors: List[str] = []

        db: Session = self.db_factory()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {line_no}: JSON parse error – {e}")
                        continue

                    valid, issues = self.validate_example(data)
                    if not valid:
                        errors.append(f"Line {line_no} ({data.get('id', '?')}): {'; '.join(issues)}")
                        continue

                    ext_id = data["id"]
                    existing = db.query(Example).filter(Example.external_id == ext_id).first()
                    if existing:
                        skipped += 1
                        continue

                    inputs = data.get("inputs", {})
                    ex = Example(
                        external_id=ext_id,
                        group=data.get("group"),
                        concrete_type="conventional",
                        grade=f"M{inputs.get('fck', '')}",
                        exposure=inputs.get("exposure"),
                        member=inputs.get("member", "RCC"),
                        max_size=inputs.get("max_size"),
                        slump=inputs.get("slump"),
                        zone=inputs.get("zone"),
                        cement_grade=inputs.get("cement_grade"),
                        problem_statement=data.get("problem_statement"),
                        inputs_json=json.dumps(inputs, ensure_ascii=False),
                        solution_json=json.dumps(data.get("solution_steps", []), ensure_ascii=False),
                        mix_json=json.dumps(data.get("mix_per_m3", {}), ensure_ascii=False),
                        checks_json=json.dumps(data.get("checks", {}), ensure_ascii=False),
                        retrieval_text=data.get("retrieval_text", ""),
                        verification_status=data.get("verification_status", "unverified"),
                        source=data.get("source", ""),
                    )
                    db.add(ex)
                    imported += 1

            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(f"Database error: {e}")
            logger.exception("Error during JSONL import")
        finally:
            db.close()

        return {"imported": imported, "skipped": skipped, "errors": errors}

    def import_special_from_jsonl(self, filepath: str) -> Dict[str, Any]:
        """Import special concrete records from a JSONL file.

        Returns {imported, skipped, errors} summary.
        """
        imported = 0
        skipped = 0
        errors: List[str] = []

        db: Session = self.db_factory()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {line_no}: JSON parse error – {e}")
                        continue

                    valid, issues = self.validate_special_example(data)
                    if not valid:
                        errors.append(f"Line {line_no} ({data.get('id', '?')}): {'; '.join(issues)}")
                        continue

                    ext_id = data["id"]
                    existing = db.query(Example).filter(Example.external_id == ext_id).first()
                    if existing:
                        skipped += 1
                        continue

                    inputs = data.get("inputs", {})
                    fck = inputs.get("fck")
                    indicative_range = data.get("indicative_28d_compressive_MPa") or []
                    strength_lo = float(indicative_range[0]) if len(indicative_range) > 0 else None
                    strength_hi = float(indicative_range[1]) if len(indicative_range) > 1 else None

                    ctype = data.get("concrete_type", "special")
                    if fck is not None:
                        try:
                            grade_label = f"M{int(float(fck))}"
                        except (ValueError, TypeError):
                            grade_label = str(fck)
                    elif strength_lo is not None and strength_hi is not None:
                        mid_str = int(round((strength_lo + strength_hi) / 2.0))
                        grade_label = f"{ctype.upper()}-{mid_str}"
                    else:
                        grade_label = ctype.upper()

                    keywords = data.get("keywords", [])
                    kw_boost = (" " + " ".join(keywords) + " " + " ".join(keywords)) if keywords else ""
                    base_retrieval = data.get("retrieval_text", "")
                    retrieval_text = f"{base_retrieval}{kw_boost}".strip()

                    binder = (
                        inputs.get("binder")
                        or inputs.get("binder_system")
                        or inputs.get("cement_type")
                        or ctype
                    )

                    ex = Example(
                        external_id=ext_id,
                        group=data.get("group"),
                        concrete_type=ctype,
                        grade=grade_label,
                        exposure=inputs.get("exposure"),
                        member=inputs.get("member", "RCC"),
                        max_size=inputs.get("max_size"),
                        slump=inputs.get("slump"),
                        zone=inputs.get("zone"),
                        cement_grade=inputs.get("cement_grade"),
                        binder_system=str(binder) if binder else None,
                        keywords_json=json.dumps(keywords, ensure_ascii=False),
                        strength_lo=strength_lo,
                        strength_hi=strength_hi,
                        curing=str(data.get("curing", "")),
                        properties_json=json.dumps(data.get("expected_properties", {}), ensure_ascii=False),
                        notes=data.get("notes"),
                        source_refs=data.get("source"),
                        problem_statement=data.get("problem_statement"),
                        inputs_json=json.dumps(inputs, ensure_ascii=False),
                        solution_json=json.dumps(data.get("solution_steps", []), ensure_ascii=False),
                        mix_json=json.dumps(data.get("mix_per_m3", {}), ensure_ascii=False),
                        checks_json=json.dumps(data.get("checks", {}), ensure_ascii=False),
                        retrieval_text=retrieval_text,
                        verification_status=data.get("verification_status", "literature_based_unverified"),
                        source=data.get("source", ""),
                    )
                    db.add(ex)
                    imported += 1

            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(f"Database error: {e}")
            logger.exception("Error during special JSONL import")
        finally:
            db.close()

        return {"imported": imported, "skipped": skipped, "errors": errors}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_example(data: Dict) -> Tuple[bool, List[str]]:
        """Validate a single example record.

        Returns ``(is_valid, issues_list)``.
        """
        issues: List[str] = []

        if "id" not in data:
            issues.append("Missing required field 'id'")
        if "inputs" not in data:
            issues.append("Missing required field 'inputs'")

        inputs = data.get("inputs", {})
        fck = inputs.get("fck")
        if fck is not None and (fck < 10 or fck > 100):
            issues.append(f"fck={fck} is outside plausible range")

        exposure = inputs.get("exposure")
        if exposure and exposure not in {"mild", "moderate", "severe", "very severe", "extreme"}:
            issues.append(f"Unknown exposure '{exposure}'")

        checks = data.get("checks", {})
        if checks and not all(checks.values()):
            failed = [k for k, v in checks.items() if not v]
            issues.append(f"Failed checks: {', '.join(failed)}")

        return len(issues) == 0, issues

    @staticmethod
    def validate_special_example(data: Dict) -> Tuple[bool, List[str]]:
        """Validate a special concrete example record.

        Returns ``(is_valid, issues_list)``.
        """
        issues: List[str] = []

        if "id" not in data:
            issues.append("Missing required field 'id'")
        if "concrete_type" not in data:
            issues.append("Missing required field 'concrete_type'")
        if "mix_per_m3" not in data:
            issues.append("Missing required field 'mix_per_m3'")

        inputs = data.get("inputs", {})
        fck = inputs.get("fck")
        if fck is not None:
            try:
                fck_num = float(fck)
                if fck_num < 1 or fck_num > 250:
                    issues.append(f"fck={fck} outside plausible range (1-250 MPa)")
            except (ValueError, TypeError):
                issues.append(f"Invalid fck format '{fck}'")

        exposure = inputs.get("exposure")
        if exposure and exposure not in {"mild", "moderate", "severe", "very severe", "extreme"}:
            issues.append(f"Unknown exposure '{exposure}'")

        checks = data.get("checks", {})
        if not checks.get("absolute_volume_closed"):
            issues.append("Check 'absolute_volume_closed' must be true")
        if not checks.get("positive_quantities"):
            issues.append("Check 'positive_quantities' must be true")

        return len(issues) == 0, issues

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def get_example(self, example_id: str) -> Optional[Dict]:
        """Get a single example by external ID (e.g. 'P001' or 'GP001')."""
        db: Session = self.db_factory()
        try:
            ex = db.query(Example).filter(Example.external_id == example_id).first()
            if not ex:
                return None
            return self._to_dict(ex)
        finally:
            db.close()

    def list_examples(
        self,
        grade: Optional[str] = None,
        exposure: Optional[str] = None,
        zone: Optional[str] = None,
        group: Optional[str] = None,
        concrete_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict], int]:
        """List examples with optional filtering. Returns (results, total_count)."""
        db: Session = self.db_factory()
        try:
            q = db.query(Example)
            if concrete_type:
                q = q.filter(Example.concrete_type == concrete_type)
            if grade:
                q = q.filter(Example.grade == grade)
            if exposure:
                q = q.filter(Example.exposure == exposure)
            if zone:
                q = q.filter(Example.zone == zone)
            if group:
                q = q.filter(Example.group == group)

            total = q.count()
            examples = q.order_by(Example.external_id).offset(offset).limit(limit).all()
            return [self._to_dict(ex) for ex in examples], total
        finally:
            db.close()

    def get_similar_examples(self, inputs: Dict, top_k: int = 3) -> List[Dict]:
        """Find examples most similar to given inputs.

        Uses a weighted scoring system comparing key parameters.
        Guarded against non-numeric grades and type-aware for special concretes.
        """
        db: Session = self.db_factory()
        try:
            target_type = inputs.get("concrete_type")
            if target_type and target_type != "conventional":
                # Special concrete retrieval: filter strictly by concrete_type
                candidates = db.query(Example).filter(Example.concrete_type == target_type).all()
                if not candidates:
                    candidates = db.query(Example).all()

                scored_special: List[Tuple[float, Dict, Dict]] = []
                target_fck = inputs.get("fck")
                target_curing = inputs.get("curing")

                for ex in candidates:
                    score = 0.0
                    diffs: Dict[str, str] = {}
                    matches: List[str] = []
                    ex_inputs = json.loads(ex.inputs_json) if ex.inputs_json else {}

                    # Target compressive strength comparison (weight: 0.40)
                    if target_fck:
                        if ex.strength_lo is not None and ex.strength_hi is not None:
                            if ex.strength_lo <= target_fck <= ex.strength_hi:
                                score += 0.40
                                matches.append(f"Strength within indicative {ex.strength_lo}-{ex.strength_hi} MPa")
                            else:
                                mid = (ex.strength_lo + ex.strength_hi) / 2.0
                                diff = abs(mid - target_fck)
                                score += max(0.0, 0.40 - (diff / 100.0) * 0.40)
                                diffs["strength"] = f"Target {target_fck} MPa, typical {ex.strength_lo}-{ex.strength_hi} MPa"
                        elif ex.grade and ex.grade.startswith("M"):
                            try:
                                ex_fck = int(ex.grade[1:])
                                diff = abs(ex_fck - target_fck)
                                score += max(0.0, 0.40 - (diff / 100.0) * 0.40)
                            except (ValueError, TypeError):
                                pass

                    # Curing condition comparison (weight: 0.20)
                    if target_curing and ex.curing:
                        if target_curing.lower() in ex.curing.lower() or ex.curing.lower() in target_curing.lower():
                            score += 0.20
                            matches.append(f"Curing: {ex.curing}")
                        else:
                            diffs["curing"] = f"Target {target_curing}, base {ex.curing}"

                    # Type-specific parameter comparison (weight: 0.40)
                    if target_type == "geopolymer":
                        tgt_m = inputs.get("naoh_molarity")
                        ex_m = ex_inputs.get("naoh_molarity")
                        if tgt_m is not None and ex_m is not None:
                            if tgt_m == ex_m:
                                score += 0.20
                                matches.append(f"NaOH molarity: {tgt_m}M")
                            else:
                                score += max(0.0, 0.20 - abs(tgt_m - ex_m) * 0.03)
                                diffs["molarity"] = f"Target {tgt_m}M, base {ex_m}M"
                        tgt_ggbs = inputs.get("ggbs_pct")
                        ex_ggbs = ex_inputs.get("ggbs_pct")
                        if tgt_ggbs is not None and ex_ggbs is not None:
                            if tgt_ggbs == ex_ggbs:
                                score += 0.20
                                matches.append(f"GGBS: {tgt_ggbs}%")
                            else:
                                score += max(0.0, 0.20 - abs(tgt_ggbs - ex_ggbs) * 0.003)

                    elif target_type in ("fiber-reinforced", "uhpc", "ecc"):
                        tgt_f_type = inputs.get("fiber_type") or inputs.get("fibre_type")
                        ex_f_type = ex_inputs.get("fiber_type") or ex_inputs.get("fibre_type")
                        if tgt_f_type and ex_f_type:
                            if str(tgt_f_type).lower() in str(ex_f_type).lower():
                                score += 0.20
                                matches.append(f"Fibre: {ex_f_type}")
                        tgt_dose = inputs.get("fiber_dose") or inputs.get("fibre_dose")
                        ex_dose = ex_inputs.get("fiber_dose") or ex_inputs.get("fibre_dose")
                        if tgt_dose is not None and ex_dose is not None:
                            try:
                                score += max(0.0, 0.20 - abs(float(tgt_dose) - float(ex_dose)) * 0.05)
                            except (ValueError, TypeError):
                                pass

                    elif target_type == "lightweight":
                        tgt_den = inputs.get("density_target") or inputs.get("density")
                        ex_den = ex_inputs.get("density_target") or ex_inputs.get("density")
                        if tgt_den is not None and ex_den is not None:
                            try:
                                score += max(0.0, 0.30 - (abs(float(tgt_den) - float(ex_den)) / 500.0) * 0.30)
                            except (ValueError, TypeError):
                                pass

                    elif target_type == "pervious":
                        tgt_v = inputs.get("void_pct")
                        ex_v = ex_inputs.get("void_pct")
                        if tgt_v is not None and ex_v is not None:
                            try:
                                score += max(0.0, 0.30 - abs(float(tgt_v) - float(ex_v)) * 0.02)
                            except (ValueError, TypeError):
                                pass

                    elif target_type == "sea-sand":
                        tgt_w = inputs.get("mixing_water")
                        ex_w = ex_inputs.get("mixing_water")
                        if tgt_w and ex_w and str(tgt_w).lower() == str(ex_w).lower():
                            score += 0.25
                            matches.append(f"Mixing water: {ex_w}")

                    d = self._to_dict(ex)
                    d["similarity_score"] = round(score, 3)
                    d["matches"] = matches
                    d["differences"] = diffs
                    scored_special.append((score, d, diffs))

                scored_special.sort(key=lambda x: x[0], reverse=True)
                return [item[1] for item in scored_special[:top_k]]

            # Conventional concrete similarity
            all_examples = db.query(Example).filter(
                (Example.concrete_type == "conventional") | (Example.concrete_type == None)
            ).all()
            if not all_examples:
                all_examples = db.query(Example).all()
            if not all_examples:
                return []

            scored: List[Tuple[float, Dict, Dict]] = []
            target_fck = inputs.get("fck")
            target_exp = inputs.get("exposure")
            target_zone = inputs.get("zone")
            target_size = inputs.get("max_size")
            target_cg = inputs.get("cement_grade")
            target_scm = inputs.get("scm", [])

            for ex in all_examples:
                score = 0.0
                diffs: Dict[str, str] = {}
                matches: List[str] = []

                # Grade similarity (weight: 0.30) - Guarded against non-M grades
                if target_fck and ex.grade:
                    ex_fck = None
                    if ex.grade.startswith("M"):
                        try:
                            ex_fck = int(ex.grade[1:])
                        except (ValueError, TypeError):
                            ex_fck = None
                    elif ex.strength_lo is not None and ex.strength_hi is not None:
                        ex_fck = (ex.strength_lo + ex.strength_hi) / 2.0

                    if ex_fck is not None:
                        if ex_fck == target_fck:
                            score += 0.30
                            matches.append(f"Grade {ex.grade}")
                        elif abs(ex_fck - target_fck) <= 5:
                            score += 0.15
                            diffs["grade"] = f"Target M{target_fck}, example {ex.grade}"
                        else:
                            diffs["grade"] = f"Target M{target_fck}, example {ex.grade}"

                # Exposure (weight: 0.25)
                if target_exp and ex.exposure:
                    if ex.exposure == target_exp:
                        score += 0.25
                        matches.append(f"Exposure: {ex.exposure}")
                    else:
                        diffs["exposure"] = f"Target {target_exp}, example {ex.exposure}"

                # Zone (weight: 0.15)
                zone_order = {"I": 1, "II": 2, "III": 3, "IV": 4}
                if target_zone and ex.zone:
                    if ex.zone == target_zone:
                        score += 0.15
                        matches.append(f"Zone {ex.zone}")
                    elif abs(zone_order.get(ex.zone, 0) - zone_order.get(target_zone, 0)) == 1:
                        score += 0.07
                        diffs["zone"] = f"Target Zone {target_zone}, example Zone {ex.zone}"
                    else:
                        diffs["zone"] = f"Target Zone {target_zone}, example Zone {ex.zone}"

                # Aggregate size (weight: 0.15)
                if target_size and ex.max_size:
                    if ex.max_size == target_size:
                        score += 0.15
                        matches.append(f"Aggregate size: {ex.max_size} mm")
                    else:
                        score += 0.05
                        diffs["max_size"] = f"Target {target_size} mm, example {ex.max_size} mm"

                # Cement grade (weight: 0.10)
                if target_cg and ex.cement_grade:
                    if ex.cement_grade == target_cg:
                        score += 0.10
                        matches.append(f"Cement grade: {ex.cement_grade}")
                    else:
                        score += 0.03
                        diffs["cement_grade"] = f"Target {target_cg}, example {ex.cement_grade}"

                # SCM type (weight: 0.05)
                if target_scm:
                    ex_inputs = json.loads(ex.inputs_json) if ex.inputs_json else {}
                    ex_scm = ex_inputs.get("scm", [])
                    target_types = {s[0] if isinstance(s, (list, tuple)) else s.get("type", "") for s in target_scm}
                    ex_types = {s[0] if isinstance(s, (list, tuple)) else "" for s in ex_scm} if ex_scm else set()
                    if target_types & ex_types:
                        score += 0.05
                        matches.append(f"SCM: {', '.join(target_types & ex_types)}")

                d = self._to_dict(ex)
                d["similarity_score"] = round(score, 3)
                d["matches"] = matches
                d["differences"] = diffs
                scored.append((score, d, diffs))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored[:top_k]]
        finally:
            db.close()

    def update_verification_status(self, example_id: str, status: str, notes: str = "") -> bool:
        """Update verification status of an example."""
        db: Session = self.db_factory()
        try:
            ex = db.query(Example).filter(Example.external_id == example_id).first()
            if not ex:
                return False
            ex.verification_status = status
            if notes:
                ex.source = (ex.source or "") + f" | Note: {notes}"
            db.commit()
            return True
        finally:
            db.close()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the example collection."""
        db: Session = self.db_factory()
        try:
            total = db.query(Example).count()
            by_group = {}
            for ex in db.query(Example.group).distinct():
                cnt = db.query(Example).filter(Example.group == ex[0]).count()
                by_group[ex[0] or "ungrouped"] = cnt
            by_grade = {}
            for ex in db.query(Example.grade).distinct():
                cnt = db.query(Example).filter(Example.grade == ex[0]).count()
                by_grade[ex[0] or "unknown"] = cnt
            by_status = {}
            for ex in db.query(Example.verification_status).distinct():
                cnt = db.query(Example).filter(Example.verification_status == ex[0]).count()
                by_status[ex[0] or "unknown"] = cnt
            by_type = {}
            for ex in db.query(Example.concrete_type).distinct():
                cnt = db.query(Example).filter(Example.concrete_type == ex[0]).count()
                by_type[ex[0] or "conventional"] = cnt
            return {
                "total": total,
                "by_group": by_group,
                "by_grade": by_grade,
                "by_verification_status": by_status,
                "by_concrete_type": by_type,
            }
        finally:
            db.close()

    def get_for_search_index(self) -> List[Dict]:
        """Get all examples formatted for the search index."""
        db: Session = self.db_factory()
        try:
            examples = db.query(Example).all()
            docs = []
            for ex in examples:
                docs.append({
                    "id": ex.external_id,
                    "text": ex.retrieval_text or ex.problem_statement or "",
                    "metadata": {
                        "grade": ex.grade,
                        "exposure": ex.exposure,
                        "zone": ex.zone,
                        "max_size": ex.max_size,
                        "member": ex.member,
                        "group": ex.group,
                        "cement_grade": ex.cement_grade,
                        "concrete_type": ex.concrete_type or "conventional",
                        "verification_status": ex.verification_status,
                        "source_type": "example",
                    },
                })
            return docs
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(ex: Example) -> Dict[str, Any]:
        """Convert an Example ORM object to a plain dict."""
        ctype = ex.concrete_type or "conventional"
        solution_steps = json.loads(ex.solution_json) if ex.solution_json else []
        mix_data = json.loads(ex.mix_json) if ex.mix_json else {}
        inputs_data = json.loads(ex.inputs_json) if ex.inputs_json else {}
        expected_props = json.loads(ex.properties_json) if ex.properties_json else {}

        # If special concrete record and solution_steps is empty, synthesize engineering steps
        if ctype != "conventional" and not solution_steps:
            try:
                from app.engine.special_steps import generate_special_calculation_steps
                base_synth = {
                    "id": ex.external_id,
                    "concrete_type": ctype,
                    "indicative_28d_compressive_MPa": [ex.strength_lo or 30.0, ex.strength_hi or 40.0],
                    "curing": ex.curing or "Standard curing",
                    "source": ex.source_refs or ex.source or "Published literature",
                    "notes": ex.notes or "",
                    "inputs": inputs_data,
                    "expected_properties": expected_props,
                    "verification_status": ex.verification_status or "literature_based_unverified",
                }
                solution_steps = generate_special_calculation_steps(ctype, base_synth, mix_data, inputs_data)
            except Exception as e:
                logger.warning("Failed to auto-generate special steps for %s: %s", ex.external_id, e)

        return {
            "id": ex.id,
            "external_id": ex.external_id,
            "group": ex.group,
            "concrete_type": ctype,
            "grade": ex.grade,
            "exposure": ex.exposure,
            "member": ex.member,
            "max_size": ex.max_size,
            "slump": ex.slump,
            "zone": ex.zone,
            "cement_grade": ex.cement_grade,
            "binder_system": ex.binder_system,
            "keywords": json.loads(ex.keywords_json) if ex.keywords_json else [],
            "strength_lo": ex.strength_lo,
            "strength_hi": ex.strength_hi,
            "curing": ex.curing,
            "expected_properties": expected_props,
            "notes": ex.notes,
            "source_refs": ex.source_refs,
            "problem_statement": ex.problem_statement,
            "inputs": inputs_data,
            "solution_steps": solution_steps,
            "mix_per_m3": mix_data,
            "checks": json.loads(ex.checks_json) if ex.checks_json else {},
            "retrieval_text": ex.retrieval_text,
            "verification_status": ex.verification_status,
            "source": ex.source,
            "created_at": ex.created_at.isoformat() if ex.created_at else None,
        }


def ingest_initial_examples() -> Dict[str, Any]:
    """Helper to initialize database tables and ingest bundled 100 benchmark examples + special records."""
    import os
    from app.config import settings
    from app.database import init_db, SessionLocal
    from app.rag.embeddings import TFIDFEmbedder
    from app.rag.search import HybridSearcher
    from app.models import Example

    init_db()
    mgr = ExampleManager(SessionLocal)
    jsonl_path = os.path.join(settings.DATA_DIR, "examples", "mix_problems.jsonl")
    special_jsonl_path = os.path.join(settings.DATA_DIR, "examples", "special", "special_concrete_mixes.jsonl")
    result = {"imported": 0, "status": "already_indexed"}

    needs_index = False
    if os.path.exists(jsonl_path):
        res = mgr.import_from_jsonl(jsonl_path)
        if res.get("imported", 0) > 0:
            needs_index = True

    if os.path.exists(special_jsonl_path):
        db = SessionLocal()
        special_count = db.query(Example).filter(Example.concrete_type != "conventional").count()
        db.close()
        if special_count == 0:
            res_sp = mgr.import_special_from_jsonl(special_jsonl_path)
            if res_sp.get("imported", 0) > 0:
                needs_index = True

    if needs_index:
        docs = mgr.get_for_search_index()
        if docs:
            embedder = TFIDFEmbedder()
            searcher = HybridSearcher(embedder)
            searcher.index_documents(docs)
            embedder.save_index()
            result["status"] = "indexed"
            result["total_docs"] = len(docs)

    return result

