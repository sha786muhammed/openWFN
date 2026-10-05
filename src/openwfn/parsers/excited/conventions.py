"""Shared excited-state method classification and amplitude semantics."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MethodClassification:
    """Canonical method family plus the exact source-reported detail."""

    family: str
    detail: str
    transition_kind_hint: str | None = None


@dataclass(frozen=True, slots=True)
class AmplitudeSemantics:
    """Scientific meaning attached to one explicit amplitude convention."""

    defined: bool
    nto_ready: bool
    requires_left_state: bool = False
    spin_structure: str | None = None
    row_domain: str | None = None
    column_domain: str | None = None
    requires_domain_metadata: bool = False
    note: str = ""


def _normalized(value: str) -> str:
    clean = value.strip()
    if not clean:
        raise ValueError("excited-state method label must not be blank")
    return clean


def classify_method(source_program: str, source_label: str) -> MethodClassification:
    """Map source labels to stable families without discarding source wording."""

    del source_program
    detail = _normalized(source_label)
    upper = detail.upper().replace("Δ", "DELTA")

    transition_kind: str | None = None
    if "EOM-IP" in upper or "IP-EOM" in upper:
        transition_kind = "ionization"
    elif "EOM-EA" in upper or "EA-EOM" in upper:
        transition_kind = "electron_attachment"
    elif "CVS-EOM" in upper or "STEX" in upper or "CORE-EXCIT" in upper:
        transition_kind = "core"

    if "STEOM" in upper:
        family = "steom"
    elif ("PNO" in upper or "DLPNO" in upper) and "EOM" in upper:
        family = "local_cc"
    elif "CVS-EOM" in upper or "STEX" in upper or "CORE-EXCIT" in upper:
        family = "core"
    elif "EOM" in upper:
        family = "eom"
    elif "ADC" in upper:
        family = "adc"
    elif "ROCIS" in upper:
        family = "rocis"
    elif "SF-TDA" in upper or "SF-TDDFT" in upper or "SPIN-FLIP" in upper:
        family = "spin_flip"
    elif "SA-CASSCF" in upper or "CASSCF" in upper or "CAS-SCF" in upper:
        family = "casscf"
    elif "CASPT2" in upper:
        family = "caspt2"
    elif "NEVPT2" in upper:
        family = "nevpt2"
    elif re.search(r"\bRAS(?:-|\b)", upper):
        family = "ras"
    elif "MRCI" in upper or "MR-CI" in upper:
        family = "mrci"
    elif "NOCI" in upper:
        family = "noci"
    elif "MOM" in upper or "DELTA-SCF" in upper or "DELTASCF" in upper:
        family = "dscf"
    elif "TDHF" in upper or re.search(r"\bRPA\b", upper):
        family = "rpa"
    elif "TDDFT" in upper or "TDA" in upper or re.search(r"\bTD\s*\(", upper):
        family = "tddft"
    elif re.search(r"(?:^|[\s/,(])CIS(?:[\s/),]|$)", upper):
        family = "cis"
    else:
        family = "other"

    return MethodClassification(
        family=family,
        detail=detail,
        transition_kind_hint=transition_kind,
    )


def amplitude_semantics(convention: str) -> AmplitudeSemantics:
    """Return conservative semantics for an explicitly named amplitude object."""

    clean = _normalized(convention)
    key = re.sub(r"[\s_]+", "-", clean.casefold())

    if key in {"transition-density-matrix", "transition-density"}:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=True,
            spin_structure="source-defined",
            requires_domain_metadata=True,
            note=(
                "Explicit transition-density matrix; NTO use additionally requires source "
                "metadata proving occupied-row/virtual-column orbital domains."
            ),
        )
    if key in {"cis-transition-amplitude-matrix", "cis-transition-matrix"}:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=True,
            spin_structure="source-defined",
            row_domain="occupied",
            column_domain="virtual",
            note=(
                "Explicit complete CIS transition-amplitude matrix with occupied rows and "
                "virtual columns."
            ),
        )
    if "percentage" in key or "weight" in key:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=False,
            note="Printed percentages/weights are descriptive contributions, not reconstructible transition amplitudes.",
        )
    if key in {"eom-right-vector", "eom-right-amplitudes"}:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=False,
            requires_left_state=True,
            note="A right EOM vector alone is not treated as an NTO transition density.",
        )
    if key in {"eom-left-vector", "eom-left-amplitudes"}:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=False,
            requires_left_state=True,
            note="Left/right EOM objects require method-specific transition-density construction.",
        )
    if key in {"tddft-x-amplitudes", "tddft-y-amplitudes", "tddft-xy-amplitudes"}:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=False,
            spin_structure="method-dependent",
            note="TDDFT X/Y amplitudes are preserved but require explicit response-theory reconstruction before NTO use.",
        )
    if key in {"adc-isr-amplitudes", "adc-amplitudes"}:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=False,
            note="ADC/ISR amplitudes are method-specific and are not silently converted into a transition density.",
        )
    if key in {"ci-coefficients", "cis-coefficients", "configuration-coefficients"}:
        return AmplitudeSemantics(
            defined=True,
            nto_ready=False,
            note="Configuration coefficients are preserved but are not automatically interpreted as a dense transition matrix.",
        )

    return AmplitudeSemantics(
        defined=False,
        nto_ready=False,
        note="Unknown amplitude convention; retained without mathematical reinterpretation.",
    )
