# Independent Multiwfn basin investigation

This is investigation evidence, **not an accepted release reference**. It does
not clear the existing openWFN coarse/medium/fine convergence gates or promote
QTAIM basins from Experimental.

The unmodified distributed Multiwfn binary was obtained from mirror commit
`584bd99f284b7324354d6b836d19232657383733`. Its SHA-256, version banner,
license source, input hashes, settings, commands, atom mappings, populations and
complete stdout are recorded in `investigation.json`. Cite Tian Lu and Feiwu
Chen, *J. Comput. Chem.* **33**, 580–592 (2012) when using these results.
The external executable is not distributed with openWFN.

Only `nthreads` in the distributed settings file was changed from 4 to 1.
Multiwfn loaded the same FCHK files directly; no wavefunction transformation or
scientific source modification was made. Run from a directory containing the
recorded `settings.ini`, using the executable and input path recorded in JSON,
and redirect the corresponding `.stdin` file into the process. The original
absolute paths document this run; substitute the equivalent checkout paths when
reproducing it. Required system shared libraries were extracted to a temporary
directory without altering the installed operating system.

Each run generates electron-density basins, then uses mixed atomic-center and
uniform-grid integration with exact boundary refinement. Uniform spacings are
0.10, 0.06 and 0.04 bohr. Reported populations are the **raw integrals before
Multiwfn's optional charge normalization**. Normalized charges printed later in
the transcripts are not used.

| Input | Finest populations, electrons, input atom order | Maximum 0.06→0.04 shift | Electron closure error |
|---|---|---:|---:|
| Water | 8.92542673, 0.53728601, 0.53728523 | 0.00122222 | 0.00000203 |
| Methane | 6.02159619, 0.99459691, 0.99459576, 0.99459574, 0.99459574 | 0.00277151 | 0.00001966 |
| Ammonia | 7.96844204, 0.67723837, 0.67715841, 0.67715463 | 0.00017488 | 0.00000656 |

The finite-grid attractor inventory reports exactly one mapped attractor per
atom, with no additional attractor. It cannot establish exhaustive absence of
undiscovered non-nuclear attractors. These checks cover restricted, small,
all-electron wavefunctions only.

The existing openWFN fine-grid methane carbon population is 6.04607563 e,
0.02447944 e above this independent value, exceeding the predeclared 0.02 e
agreement limit. Water and methane additionally fail the existing openWFN
medium-to-fine 0.01 e convergence gate. Increasing resource budgets, selecting a
favorable grid or using normalized charges does not clear those failures.
