import pytest


def test_method_classification_matrix_preserves_source_detail() -> None:
    from openwfn.parsers.excited.conventions import classify_method

    cases = (
        ("Gaussian", "CIS/6-31G", "cis"),
        ("Gaussian", "TDHF", "rpa"),
        ("Gaussian", "TD(B3LYP)", "tddft"),
        ("Gaussian", "TDA CAM-B3LYP", "tddft"),
        ("ORCA", "SF-TDA", "spin_flip"),
        ("ORCA", "ROCIS", "rocis"),
        ("ORCA", "ADC(2)", "adc"),
        ("ORCA", "CVS-ADC(2)-x", "adc"),
        ("Q-Chem", "EOM-EE-CCSD", "eom"),
        ("Q-Chem", "EOM-IP-CCSD", "eom"),
        ("Q-Chem", "EOM-EA-CCSD", "eom"),
        ("Q-Chem", "EOM-SF-CCSD", "eom"),
        ("ORCA", "STEOM-CCSD", "steom"),
        ("ORCA", "DLPNO-STEOM-CCSD", "steom"),
        ("ORCA", "PNO-EOM-CCSD", "local_cc"),
        ("ORCA", "SA-CASSCF", "casscf"),
        ("ORCA", "CASPT2", "caspt2"),
        ("ORCA", "NEVPT2", "nevpt2"),
        ("Q-Chem", "RAS-SF", "ras"),
        ("ORCA", "MRCI", "mrci"),
        ("Q-Chem", "NOCI", "noci"),
        ("Q-Chem", "STEX", "core"),
        ("Q-Chem", "CVS-EOM-CCSD", "core"),
        ("Q-Chem", "MOM", "dscf"),
        ("Q-Chem", "Delta-SCF", "dscf"),
        ("Q-Chem", "MYSTERY-EXCITED", "other"),
    )

    for program, label, family in cases:
        classification = classify_method(program, label)
        assert classification.family == family
        assert classification.detail == label


def test_transition_kind_hints_are_conservative() -> None:
    from openwfn.parsers.excited.conventions import classify_method

    assert classify_method("Q-Chem", "EOM-IP-CCSD").transition_kind_hint == "ionization"
    assert classify_method("Q-Chem", "EOM-EA-CCSD").transition_kind_hint == "electron_attachment"
    assert classify_method("Q-Chem", "CVS-EOM-CCSD").transition_kind_hint == "core"
    assert classify_method("Gaussian", "TD(B3LYP)").transition_kind_hint is None


def test_amplitude_semantics_do_not_promote_percentages_or_unknown_coefficients() -> None:
    from openwfn.parsers.excited.conventions import amplitude_semantics

    percentage = amplitude_semantics("printed transition percentage")
    assert percentage.defined
    assert not percentage.nto_ready

    eom = amplitude_semantics("eom-right-vector")
    assert eom.defined
    assert not eom.nto_ready
    assert eom.requires_left_state

    unknown = amplitude_semantics("mystery coefficients")
    assert not unknown.defined
    assert not unknown.nto_ready


def test_only_explicit_transition_objects_are_nto_ready() -> None:
    from openwfn.parsers.excited.conventions import amplitude_semantics

    transition_density = amplitude_semantics("transition-density-matrix")
    cis = amplitude_semantics("cis-transition-amplitude-matrix")

    assert transition_density.nto_ready
    assert transition_density.requires_domain_metadata
    assert cis.nto_ready
    assert cis.row_domain == "occupied"
    assert cis.column_domain == "virtual"
    assert not amplitude_semantics("tddft-x-amplitudes").nto_ready
    assert not amplitude_semantics("adc-isr-amplitudes").nto_ready


def test_amplitude_block_uses_shared_semantics_registry() -> None:
    from openwfn.excited_states import AmplitudeBlock

    implicit = AmplitudeBlock(
        convention="transition-density-matrix",
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
    )
    explicit = AmplitudeBlock(
        convention="transition-density-matrix",
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
        row_domain="occupied",
        column_domain="virtual",
    )
    cis = AmplitudeBlock(
        convention="cis-transition-amplitude-matrix",
        values=(0.8, 0.1, -0.2, 0.3),
        dimensions=(2, 2),
    )
    generic = AmplitudeBlock(convention="mystery coefficients", values=(0.5,))

    assert not implicit.nto_ready
    assert explicit.nto_ready
    assert cis.nto_ready
    assert not generic.nto_ready


def test_blank_method_label_is_rejected() -> None:
    from openwfn.parsers.excited.conventions import classify_method

    with pytest.raises(ValueError, match="blank"):
        classify_method("Gaussian", "   ")
