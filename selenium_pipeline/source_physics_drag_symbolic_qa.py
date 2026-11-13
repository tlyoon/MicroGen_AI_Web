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
        # Topic indicators are literal publisher-source words only. They
        # NEVER make a computed theorem applicable to one spoken claim.
        "printed_time_constant_topic":any("time constant" in t
                                           for t in pages),
        "printed_parachute_topic":any("parachute" in t
                                     for t in pages),
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


def prove_conditional_drag_challenges_v2() -> dict:
    """Exact *conditional* laws, not a decision about textbook/voice meaning.

    These reusable equations address the two common reasoning traps after a
    linear/quadratic drag derivation: comparing two masses at the SAME b,
    and the force/velocity signs immediately after drag increases. Every
    condition is explicit. This does not assert that an original figure,
    narration, or model reply actually supplied those assumptions.
    """
    import sympy as sp
    m,b,g,r,k,q,u=sp.symbols(
        "m b g r k q u",positive=True,finite=True)
    mass_1=m
    mass_2=r*m
    vt_1=mass_1*g/b
    vt_2=mass_2*g/b
    tau_1=mass_1/b
    tau_2=mass_2/b

    # Positive-downward convention. BEFORE opening, the falling object is
    # at terminal speed with coefficient k. AFTER opening, k increases to
    # (1+q)k, q>0. Speed remains downward initially: v_before>0.
    # The force sum and acceleration therefore point UP, even though the
    # velocity still points DOWN. This is a conditional result, not a
    # claim about the actual skydiver without the narrated assumptions.
    k_before=k
    k_after=k*(1+q)
    speed_before=sp.sqrt(m*g/k_before)
    speed_new_terminal=sp.sqrt(m*g/k_after)
    speed_above_new_terminal=speed_new_terminal*(1+u)
    checks={
        "same_b_linear_terminal_speed_ratio_equals_mass_ratio":
            sp.simplify(vt_2/vt_1-r)==0,
        "same_b_linear_time_constant_ratio_equals_mass_ratio":
            sp.simplify(tau_2/tau_1-r)==0,
        "doubled_mass_doubles_terminal_speed_same_b":
            sp.simplify((vt_2/vt_1).subs(r,2)-2)==0,
        "doubled_mass_doubles_tau_same_b":
            sp.simplify((tau_2/tau_1).subs(r,2)-2)==0,
        "initial_terminal_force_before_drag_increase_is_zero":
            sp.simplify(m*g-k_before*speed_before**2)==0,
        "post_opening_drag_to_weight_ratio_is_one_plus_q":
            sp.simplify(k_after*speed_before**2/(m*g)-(1+q))==0,
        "post_opening_net_force_upward_minus_qmg":
            sp.simplify((m*g-k_after*speed_before**2)+q*m*g)==0,
        "post_opening_acceleration_upward_minus_qg":
            sp.simplify((m*g-k_after*speed_before**2)/m+q*g)==0,
        "new_quadratic_terminal_speed_ratio_squared_one_over_one_plus_q":
            sp.simplify((speed_new_terminal/speed_before)**2
                        -1/(1+q))==0,
        "new_terminal_force_balances_weight":
            sp.simplify(m*g-k_after*speed_new_terminal**2)==0,
        "above_new_terminal_drag_exceeds_weight_by_positive_fraction":
            sp.simplify(k_after*speed_above_new_terminal**2/(m*g)
                        -(1+u)**2)==0,
        "above_new_terminal_acceleration_is_upward":
            sp.simplify((m*g-k_after*speed_above_new_terminal**2)/m
                        +g*u*(2+u))==0,
        "quadratic_drag_increases_with_positive_downward_speed":
            sp.simplify(sp.diff(k_after*sp.Symbol("v",positive=True)**2,
                                 sp.Symbol("v",positive=True))
                        -2*k_after*sp.Symbol("v",positive=True))==0,
    }
    require(all(bool(value) for value in checks.values()),
            "Conditioned independent drag challenge theorem failed")
    return {
        "schema_version":2,
        "status":"EXACT_CONDITIONAL_DRAG_IDENTITIES_REVIEW_INPUT_ONLY",
        "conditions":[
            "m>0, g>0, b>0, k_before>0, and positive-downward velocity",
            "linear compared masses share the SAME drag coefficient b",
            "second mass r*m, r>0; r=2 for doubling",
            "before parachute opens, object travels downward at old terminal speed",
            "on opening, quadratic drag coefficient becomes (1+q)k with q>0",
            "after opening, mass and g do not change and no added external forces",
            "during deceleration, downward speed stays above new terminal speed",
        ],
        "conditional_positive_variables":["m","b","g","r","k","q","u"],
        "checks":checks,
        "mathematical_conditional_results_proven":True,
        "printed_source_equations_independently_glyph_verified":False,
        "original_narration_utterance_semantics_approved":False,
        "real_source_drag_coefficients_empirically_verified":False,
        "word_level_audio_correspondence_verified":False,
        "student_publication_authorized":False,
        "G2_approved":False,
    }


def inspect(*,source: Path,script: Path|None=None) -> dict:
    source=Path(source).absolute()
    context,pages=_context(source)
    required=("linear_model_heading","quadratic_model_heading",
              "terminal_speed_text","linear_release_from_rest",
              "quadratic_speed_squared")
    applicable=all(context[k] for k in required)
    details=prove_model_identities() if applicable else None
    # A distinct conditional proof is available only under a source PDF
    # with BOTH actual drag models. Its assumptions are not inferred as
    # accepted properties of the specific teacher's narration.
    conditional=prove_conditional_drag_challenges_v2() if applicable else None
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
        "conditional_physics_challenges_v2":conditional,
        "printed_time_constant_and_parachute_topics_cooccur":bool(
            context["printed_time_constant_topic"] and
            context["printed_parachute_topic"]),
        "conditional_math_is_independent_narration_review":False,
        "mathematical_all_utterance_review_approved":False,
        "source_to_panel_semantic_approval":False,
        "audio_or_TTS_authorized":False,
        "G2_approved":False,"student_publication_authorized":False,
    }
