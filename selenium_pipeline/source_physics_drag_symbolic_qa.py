"""Reusable independent analytical checks for linear/quadratic fluid drag.

A section discussing resistive force may carry a wrong numerical example or
incorrect algebra even when a Gemini source review is inconclusive. Reuse
a conservative SymPy analytic model as an orthogonal *mathematical* witness.

Only apply when original PDF text physically identifies both proportional
drag regimes and terminal speed. Source PDF equation glyph semantics cannot
be inferred from prose alone: no broad math, pedagogy, TTS or G2 approval.
"""
from __future__ import annotations

from pathlib import Path
import re

import pymupdf

from .figure_source_identity import require, _sha


def _context(source: Path) -> tuple[dict,list[str]]:
    source=Path(source).absolute()
    require(source.is_file() and not source.is_symlink(),
            "Original actual source PDF required for independent math QA")
    digest=_sha(source)
    with pymupdf.open(source) as pdf:
        pages=[" ".join(page.get_text().lower().split()) for page in pdf]
    require(digest==_sha(source),"Source changed during analytical QA")
    context={
        "source_sha256":digest,
        "source_page_count":len(pages),
        "linear_model_heading":any(re.search(
            r"model\s+1:\s*resistive\s+force\s+proportional",t) for t in pages),
        "quadratic_model_heading":any(re.search(
            r"model\s+2:\s*resistive\s+force\s+proportional",t) for t in pages),
        "terminal_speed_text":any("terminal speed" in t for t in pages),
        "linear_release_from_rest":any("sphere" in t and
            "released from rest" in t for t in pages),
        "quadratic_speed_squared":any("square of the speed" in t or
            "speed squared" in t for t in pages),
    }
    return context,pages


def prove_model_identities() -> dict:
    """Independent exact SymPy identities, with explicit positive domains."""
    import sympy as sp
    m,b,g,t,rho,A,D,v=sp.symbols(
        "m b g t rho A D v", positive=True,finite=True)
    vt=m*g/b
    tau=m/b
    speed=vt*(1-sp.exp(-t/tau))
    checks={
        "initial_velocity_v_zero":sp.simplify(speed.subs(t,0))==0,
        "initial_downward_acceleration_is_g":sp.simplify(
            sp.diff(speed,t).subs(t,0)-g)==0,
        "differential_equation_m_dvdt_equals_mg_minus_bv":sp.simplify(
            m*sp.diff(speed,t)-(m*g-b*speed))==0,
        "linear_terminal_speed_mg_over_b":sp.simplify(
            sp.limit(speed,t,sp.oo)-vt)==0,
        "time_constant_m_over_b":sp.simplify(tau-m/b)==0,
        "one_tau_fraction_one_minus_exp_minus_one":sp.simplify(
            speed.subs(t,tau)/vt-(1-sp.exp(-1)))==0,
        "linear_t90_equals_tau_ln10":sp.simplify(
            speed.subs(t,tau*sp.log(10))/vt-sp.Rational(9,10))==0,
    }
    quadratic_vt=sp.sqrt(2*m*g/(D*rho*A))
    checks.update({
        "quadratic_drag_terminal_acceleration_zero":sp.simplify(
            g-D*rho*A*quadratic_vt**2/(2*m))==0,
        "quadratic_terminal_speed_positive_root":sp.simplify(
            quadratic_vt-sp.sqrt(2*m*g/(D*rho*A)))==0,
        "quadratic_drag_as_weight_times_speed_ratio_squared":sp.simplify(
            (D*rho*A*v**2/2)-
            (m*g)*(v/quadratic_vt)**2)==0,
    })
    require(all(bool(x) for x in checks.values()),
            "An exact model identity was not independently proven")
    numeric_tau=sp.Rational(5,980)
    numeric_t90=numeric_tau*sp.log(10)
    numeric_one_tau=1-sp.exp(-1)
    numeric={
        "oil_sphere_5_cm_per_s_and_980_cm_per_s_squared_tau_s":
            float(numeric_tau),
        "oil_sphere_t90_s":float(numeric_t90),
        "one_tau_terminal_speed_fraction":float(numeric_one_tau),
        "oil_sphere_tau_round_3sig_ms":round(float(numeric_tau*1000),2),
        "oil_sphere_t90_round_3sig_ms":round(float(numeric_t90*1000),1),
        "baseball_145g_speed40_2_terminal43_drag_N":float(
            sp.Rational(145,1000)*sp.Rational(98,10)*
            (sp.Rational(402,10)/43)**2),
    }
    require(.631<numeric["one_tau_terminal_speed_fraction"]<.633
            and 5.095<numeric["oil_sphere_tau_round_3sig_ms"]<5.105
            and 11.65<numeric["oil_sphere_t90_round_3sig_ms"]<11.75,
            "Orthogonal physics numeric invariants failed")
    return {"symbolic_identity_proof_passed":True,
            "exact_positive_domain_parameter_conditions":
                ["m>0","b>0","g>0","D>0","rho>0","A>0","t>=0"],
            "equation_identity_checks":checks,
            "numeric_predictions":numeric,
            "theorem_proof_is_textbook_glyph_verification":False,
            "entire_original_narration_scientifically_approved":False}


def inspect(*,source: Path,script: Path|None=None) -> dict:
    source=Path(source).absolute()
    context,pages=_context(source)
    required=("linear_model_heading","quadratic_model_heading",
              "terminal_speed_text","linear_release_from_rest",
              "quadratic_speed_squared")
    applicable=all(context[k] for k in required)
    details=prove_model_identities() if applicable else None
    script_sha=None
    if script is not None:
        script=Path(script).absolute()
        require(script.is_file() and not script.is_symlink(),
                "Genuine immutable narration script required")
        script_sha=_sha(script)
    pdf_sha=context["source_sha256"]
    require(_sha(source)==pdf_sha
            and (script is None or script_sha==_sha(script)),
            "Source/narration bytes drifted during mathematical QA")
    return {
        "schema_version":1,
        "status":("SOURCE_DRAG_ANALYTICAL_IDENTITIES_INDEPENDENTLY_PROVEN"
                  if applicable else "SOURCE_DRAG_PROOF_NOT_APPLICABLE"),
        **context,"script_sha256":script_sha,
        "source_physically_has_relevant_model_headings":applicable,
        "source_script_math_equations_all_semantically_verified":False,
        "proof":details,
        "mathematical_all_utterance_review_approved":False,
        "source_to_panel_semantic_approval":False,
        "audio_or_TTS_authorized":False,
        "G2_approved":False,"student_publication_authorized":False,
    }
