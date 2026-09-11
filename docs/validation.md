# Validation and capability states

- **Stable** — interface and implementation are tested, but no claim of independent numerical reference validation is implied.
- **Validated** — numerical behavior passes a documented reference and tolerance.
- **Experimental** — usable for investigation, with accuracy or interface limitations stated.
- **Unsupported** — deliberately rejected because required data or a trustworthy implementation is unavailable.

The water total-density grid integrates to 10 electrons with relative error below 0.5% using 0.15-bohr spacing and 6-bohr padding. The AO overlap and density matrices recover 10 electrons through both Mulliken and Löwdin accounting.

Validation status is included in structured CLI results, reports, and workbench fields. A successful command alone does not promote a method to Validated.
