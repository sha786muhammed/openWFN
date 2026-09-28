# Repository trust and publication-readiness cleanup

## Purpose

This cleanup makes the existing openWFN repository internally consistent,
legally attributable, easier to contribute to, and ready to support a future
software paper. It does not add scientific formats, analyses, services, or
interfaces. Version `0.8.0a2` and its scientific behavior remain unchanged.

The repository must state only facts supported by source code, package
contents, versioned records, upstream licenses, or reproducible validation
evidence. Unknown authorship, provenance, affiliation, version, or publication
metadata must be identified as unavailable rather than inferred.

## Scope

The cleanup covers:

- bundled third-party software and its redistribution terms;
- project-created website assets and scientific examples;
- software citation and future-paper guidance;
- contributor, maintainer, conduct, issue, pull-request, and security guidance;
- README, PyPI metadata, website pages, examples, and release-facing documents;
- documentation duplication, outdated wording, links, and runnable commands;
- package contents, development-environment hygiene, and automated consistency
  checks;
- existing HTML reports, viewer exports, and the Experimental workbench.

The cleanup does not cover:

- new input or output formats;
- new scientific methods or validation claims;
- changes to numerical results, command syntax, schemas, or the public Python
  API;
- REST, MCP, hosted services, or telemetry;
- a version bump, tag, release, or PyPI upload;
- a paper title, author list, DOI, journal, ORCID, or institutional affiliation.

## Sources of truth

Each public fact has one authoritative source.

| Subject | Authoritative source |
|---|---|
| Project license | `LICENSE` |
| Bundled external components | `THIRD_PARTY_NOTICES.md` and the component's full bundled license |
| Software citation metadata | `CITATION.cff` |
| Contributor workflow | `CONTRIBUTING.md` |
| Contributor acknowledgement | `CONTRIBUTORS.md` |
| Vulnerability reporting | `SECURITY.md` |
| Website-data privacy | `docs/project/security.md` |
| Example provenance | `examples/PROVENANCE.md` |
| Website-asset provenance | `docs/assets/data/asset-provenance.yml` |
| Current supported interfaces | installed CLI help, `openwfn.__all__`, parser registry, and analysis registry |
| Scientific confidence | validation manifests, reference records, limitations, and validation-status documentation |
| Historical behavior | versioned release notes and Git history |

Summary pages may explain or link to these sources but must not maintain a
second conflicting policy.

## Third-party software and HTML outputs

The repository bundles a minified 3Dmol.js asset used by the standalone viewer
and Experimental workbench. Its current banner references a license file that
is not present. The cleanup must:

1. identify the upstream project and exact redistribution terms from an
   authoritative upstream source;
2. calculate and record the SHA-256 checksum of the bundled file;
3. recover the bundled version or source revision when evidence permits;
4. avoid guessing a version when it cannot be established;
5. add the complete applicable license text beside the asset;
6. add a repository-level third-party notice explaining where and why the
   asset is used;
7. include the notice and full license in source and wheel distributions;
8. retain attribution in generated HTML without requiring a network request.

HTML research reports remain supported human-readable artifacts. The existing
viewer and workbench remain available for compatibility and receive only
correctness, attribution, privacy, and documentation fixes. The workbench stays
Experimental and outside the primary installation and first-analysis path.
Machine-readable results remain the scientific record; an HTML file or
screenshot must not be presented as the only numerical evidence.

## Project assets and examples

Every distributed project asset must have a factual provenance statement.
Website images use the existing asset registry. Records must name the asset,
source category, transformation history when known, license, and descriptive
alternative text. If the exact generation record is unavailable, the record
must say so plainly.

`examples/PROVENANCE.md` must cover water, ammonia, and methane. For every
tracked input and derived file it must record:

- project ownership or an external source;
- calculation program and version when verified;
- method, basis, charge, and multiplicity when present in the file;
- the relationship between input, formatted checkpoint, and XYZ files;
- SHA-256 checksum;
- redistribution terms;
- any unknown or unavailable provenance field.

The packaged water copy must match the repository example byte for byte. Its
package README may summarize the authoritative example record but must not
contradict it. Documentation may list only files that actually exist.

## Citation and publication readiness

The public software author name is `Muhammed Shah Shaji`. The current
institutional affiliation is deliberately omitted until paper metadata is
finalized. No author email is published through this cleanup.

`CITATION.cff` must contain valid Citation File Format 1.2 metadata for the
software release. It must include the verified author name, software title,
version, release date, repository, license, keywords, and release URL. It must
not include a DOI, ORCID, preferred paper citation, journal, paper title, or
affiliation until those facts exist.

The citation guide must provide a plain-text software citation and a BibTeX
software entry derived from the same verified fields. It must tell researchers
to record the exact openWFN version, input checksum, source program, method,
basis, charge, multiplicity, and relevant numerical controls. It must state
that a paper citation will be added after an archival deposit or publication.

Repository contribution and future paper authorship are separate decisions.
The cleanup must not promise paper authorship based on commits or contribution
count.

## Contributor and governance structure

The repository must provide:

- a concise `CONTRIBUTING.md` with supported setup, clean-environment,
  testing, documentation, scientific-evidence, fixture-rights, and pull-request
  requirements;
- `CONTRIBUTORS.md` based only on verifiable Git history, with a correction
  process and no inferred affiliations;
- `CODE_OF_CONDUCT.md` using a recognized text and an explicit project contact
  route that does not expose a private email;
- `SECURITY.md` recognized by GitHub, with supported-version and private
  reporting instructions;
- a maintainer policy describing review, release authority, scientific-claim
  review, and conflict handling without inventing additional maintainers;
- structured issue forms for bugs, scientific discrepancies, and feature
  proposals;
- a pull-request template requiring tests, documentation, provenance, license
  review, and scientific validation when applicable;
- a restrained roadmap that separates maintenance, interoperability,
  scientific methods, validation, and future service layers without promising
  dates.

Scientific changes must document units, conventions, supported cases,
tolerances, reference evidence, and limitations. Parser changes must cite the
format specification or producer documentation and establish redistribution
rights for fixtures. No external implementation may be copied without a
compatible license and preserved attribution.

## Documentation consolidation

The current documentation contains overlapping CLI, Python API, quick-start,
and format pages. The cleanup must designate one authoritative page for each
subject. A retained compatibility page must be a short signpost to the
authoritative page, not a second full reference.

The audit must compare public text with:

- current CLI help;
- the parser registry;
- the analysis registry;
- `openwfn.__all__`;
- package metadata and contents;
- validation and external-reference manifests;
- tracked examples and assets.

Outdated present-tense `v0.7` wording must be corrected when it describes the
current `0.8.0a2` interface. Historical release notes remain historical and are
changed only for broken links or demonstrably incorrect present-tense claims.
Internal implementation plans and specifications remain outside website
navigation.

All documented commands must run from the directory and installation mode
stated on the page. Broken internal links, nonexistent example files, and
unsupported command forms are defects.

## Development and package hygiene

Ignored build outputs, caches, virtual environments, worktrees, coverage data,
and generated metadata must not be committed. The contributor workflow must
provide an explicit clean-environment setup and a diagnostic preflight that
detects stale editable-install metadata. It must not silently delete user data.

The package must include:

- the openWFN license required by its metadata;
- third-party notices and the full 3Dmol.js license;
- the vendored JavaScript asset;
- the packaged water fixture and its provenance summary;
- all modules needed by the documented CLI and public Python imports.

PyPI project URLs must expose documentation, source, issues, changelog, and
release information without adding unverifiable metadata.

## Automated checks

Tests must fail when:

- a bundled third-party asset lacks a notice, full license, checksum, or
  package inclusion rule;
- example files lack provenance records or recorded checksums disagree;
- the packaged water fixture differs from its repository source;
- citation version, date, release URL, author, or license diverges from release
  metadata;
- an unverified affiliation, DOI, ORCID, or paper claim appears in active
  citation pages;
- contributor or security links point to missing policies;
- public documentation names nonexistent examples, commands, formats, or
  analyses;
- a built wheel omits required attribution or provenance files;
- active public documentation contains private-machine paths, credentials, or
  internal-assistant branding.

Existing scientific validation, compatibility, and platform tests remain
unchanged except where a test must follow an authoritative documentation path.

## Verification

Completion requires all of the following from a clean supported Python
environment:

1. Ruff passes for source, tests, and scripts.
2. The complete pytest suite passes with strict markers.
3. Documentation-specific tests and the documentation consistency checker pass.
4. MkDocs builds in strict mode without project-authored warnings.
5. Internal validation and repository-owned external comparisons pass.
6. Source and wheel distributions build and pass Twine checks.
7. Distribution inspection confirms all required licenses, notices, assets,
   examples, and package metadata.
8. A clean wheel installation runs version, example installation, summary,
   frontier, and HTML export smoke tests without network access after install.
9. Generated HTML contains the required attribution and no external runtime
   dependency.
10. Git status is clean apart from intentionally ignored local artifacts.

## Success criteria

The cleanup is complete when a new contributor can understand how to work on
the repository, a researcher can identify exactly what to cite and preserve, a
redistributor can find the terms for every bundled component, documentation
matches the installed software, and no public file claims an identity,
affiliation, source, scientific validation, or publication record that the
repository cannot prove.
