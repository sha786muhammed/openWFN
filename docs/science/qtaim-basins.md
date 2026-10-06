# QTAIM atomic basin populations

**Experimental; release validation is incomplete.** Package stability does not
promote this method to Validated. A successful single-grid computation only
passes its reported conservation checks; it does not establish convergence.

## Definition and required data

For total electron density $\rho$, a basin $\Omega_A$ consists of trajectories
of $d\mathbf r/ds=\nabla\rho/|\nabla\rho|$ ending at attractor $A$:

$$
N_A=\int_{\Omega_A}\rho(\mathbf r)\,d\mathbf r,\qquad q_A=Z_A-N_A.
$$

Populations are in electrons, charges in elementary-charge units, coordinates
in bohr. These are real-space populations, not Mulliken or Hirshfeld populations.
All-electron total AO density, supported Gaussian basis functions and physical
nuclei are required. ECPs, ghosts, non-nuclear attractors and ambiguous or missing
attractor matches are rejected. Unrestricted inputs use the spin-summed total
density; spin-basin integration is not implemented. SCF density used for a
post-SCF calculation is explicitly labelled and warned about.

## Algorithm and safeguards

Bounded critical-point discovery identifies Gaussian-density maxima and matches
them uniquely to nuclei within 0.35 bohr. Maxima need not coincide with nuclei.
Absence of undiscovered non-nuclear attractors is not proven.

Atom-centred radial/angular quadrature uses smooth molecular partition weights
only to integrate space. Those quadrature owners never define basin membership.
Membership is determined by normalized-gradient ascent with density-ascent
backtracking. Unique capture, ambiguous capture, small gradients, non-finite
fields, exhausted backtracking, bounds and step limits are accounted separately.
No nearest-atom fallback or population renormalization is applied.

The current default quadrature is 48 radial × 12 polar × 24 azimuthal points per
atom, radial extent 18 bohr and chunk size 4096. Flow uses a 0.05 bohr step,
0.25 bohr capture radius, up to 2400 steps and eight backtracks. These defaults
have not passed the independent/convergence release gate. Increase quadrature
resolution and refine the flow step before interpreting populations.

Unresolved electrons above 0.001, electron-count or charge closure residuals
above 0.01, or inconsistent population accounting produce `status="partial"`.
Low-density unresolved trajectories remain explicitly reported. Passing electron
closure does not establish convergence of individual atomic populations.

Boundary diagnostics are explicitly requested with `--boundary-diagnostics`.
They sample interfaces, refine crossings by bisection, fit local normals and
report normalized gradient-normal residuals, conditioning and coverage. They
are diagnostics, not a proof of a globally closed zero-flux surface. No isolated
basin volumes, meshes, atomic energies or delocalization indices are reported.

Requests are checked against quadrature and boundary-grid point ceilings before
allocation. AO evaluation uses bounded chunks and a gradient-only shared core
for flow; Hessians are still used when critical-point discovery requires them.
Point/step limits do not impose a wall-clock deadline. For expensive trusted
local calculations use the [resource supervisor](../project/resource-validation.md).
MCP basin execution is deferred until bounded server execution is implemented;
`list_analyses` reports this in `deferred_analyses`.

## Examples and result contract

```bash
openwfn --format json examples/water/water.fchk population qtaim
openwfn --format json examples/methane/methane.fchk population qtaim \
  --radial-points 72 --theta-points 16 --phi-points 32 --radial-extent 20
openwfn --format json examples/ammonia/ammonia.fchk population qtaim \
  --boundary-diagnostics
```

```python
import openwfn

record = openwfn.load("examples/water/water.fchk").qtaim_basins()
print(record.status, record.validation_status)
print(record.data["atoms"], record.data["diagnostics"])
```

The registry name is `qtaim-basins`; CLI, Python and registry-based batch/report
workflows use the same core and `ResultRecord`. Atom rows contain zero-based
`atom_index`, `element`, `attractor_position_bohr`, `electron_population` and
`net_charge`. `diagnostics` contains resolved/unresolved populations, expected
and integrated electron counts, closure residuals and trajectory termination
counts. `boundary_diagnostics.status` is `not_requested` when omitted. Settings,
density source, input hash, parser transformations, warnings, result status and
Experimental scientific status are preserved. Missing required data produce a
structured failed result; they do not produce substituted charges.

## Validation evidence and limitations

Synthetic analytic tests cover distinct/ambiguous captures, bounded trajectories,
conservation, malformed inputs and boundary conditioning. Integration tests cover
CLI/Python/registry parity. Density and gradient also agree with independently
executed pinned Critic2 1.2 point evaluations for the investigated methane input.

The planned independent basin gate uses immutable water, methane and ammonia
FCHK hashes and Critic2 commit
`9731d532c6407d35c75bbce5af449211470437a7`. It requires fine-grid per-atom
agreement within 0.02 electron, medium-to-fine shifts within 0.01 electron,
closure within 0.01 electron and unresolved density within 0.001 electron.
Coarse/medium/fine grids are 32×8×16/48×12×24/72×16×32, extents 16/18/20 bohr.
The generator rejects non-finite, negative or electron-deficient references and
CI now performs an actual comparison, retaining raw outputs on failure.

The initial molecular-bisection water reference sums to 9.423414138 rather than
10 electrons and is rejected. Current water and methane quadrature refinement
also exceeds the prescribed per-atom shift gate. An alternative Critic2
Yu–Trinkle grid investigation does not yet establish matching converged basin
populations. These are open scientific gates, not grounds for widening tolerances
or changing validation labels. See the [readiness audit](../project/0.12-readiness.md).
