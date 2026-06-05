# Plasma Spray Deposition - 3 Particles k-omega SST - OpenFOAM interFoam

<p align="center">
  <img src="https://img.shields.io/badge/OpenFOAM-2412-blue?style=for-the-badge&logo=gnu&logoColor=white"/>
  <img src="https://img.shields.io/badge/Solver-interFoam-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Turbulence-k--omega%20SST-red?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/VOF-Two%20Phase-purple?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Particles-3-yellow?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/ParaView-Visualization-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey?style=for-the-badge"/>
</p>

<p align="center">
  A 2D Volume-of-Fluid (VOF) simulation of <b>three rotating YSZ particles simultaneously
  depositing onto a rigid substrate</b> at 250 m/s in an argon plasma carrier gas, with full
  turbulence modelling via k-omega SST, using OpenFOAM's <code>interFoam</code> solver.
  At Re = 2,500 per particle the flow is turbulent, producing counter-rotating vortex pairs
  in the gaps between adjacent splats, lateral merging of spreading lamellae, and asymmetric
  splat boundaries driven by individual particle spins -- physics entirely absent in the
  laminar assumption.
</p>

<img width="1008" height="772" alt="plasma spray" src="https://github.com/user-attachments/assets/7a1443e3-2d6f-4f27-b94f-5ad87d4cab56" />

---

## Why Turbulence

The Reynolds number for each particle in the plasma carrier gas is:

```
Re = V * D / nu_gas = 250 * 50e-6 / 5e-6 = 2,500
```

Re = 2,500 is firmly turbulent at this micro-scale (transition for bluff bodies ~1,000).
The laminar assumption suppresses all wake instability and inter-particle vortex interaction.
At this Re the physical flow produces turbulent wakes behind each in-flight particle and
complex jetting behaviour at impact. k-omega SST captures the near-wall behaviour at the
substrate and the separated flow around each molten droplet correctly.

---

## Why Three Particles

Single-particle simulations miss the defining feature of plasma spray: **overlapping and
merging splats**. Three particles allow direct observation of:

- Lateral squirt jets where adjacent splats collide
- Pore formation in gaps between landing sites
- Counter-rotating vortex pairs (P0 CCW, P1 CW, P2 CCW) creating upward jets
- The staggered arrival sequence that mimics real spray stream dispersion

---

## Turbulence Model: k-omega SST

k-omega SST (Menter 1994) blends k-omega near walls with k-epsilon in the freestream.
It is the standard choice for:

- Separated flows around bluff bodies (particle in plasma crossflow)
- Adverse pressure gradient boundary layers at the substrate
- Flows with strong rotation and streamline curvature
- Multi-body configurations with inter-body wake interactions

### Initial Turbulence Values

Computed from turbulent intensity I = 8% (elevated for plasma jet conditions) and
length scale L = 0.07 * D:

| Parameter | Formula | Value | Unit |
|-----------|---------|-------|------|
| Intensity | I = 0.08 | 8 | % |
| Length scale | L = 0.07 * D | 3.5 | um |
| Turb. kinetic energy | k = 1.5 * (V*I)^2 | 600.0 | m^2/s^2 |
| Spec. dissipation | omega = k^0.5 / (Cmu^0.25 * L) | ~1.28e7 | rad/s |
| Turb. viscosity | nut = k / omega | ~4.70e-5 | m^2/s |

---

## Physics

- Two-phase incompressible VOF transport via the `alpha.particle` phase-fraction field
- Rigid-body rotation initial condition stamped cell-by-cell via Python helper script
- k-omega SST Reynolds-Averaged turbulence modelling with wall functions
- PIMPLE pressure-velocity coupling with 2 outer correctors and momentum predictor
- Counter-rotating vortex pairs in the gaps between adjacent particles during free-fall
- Lateral splat merging and pore formation at the substrate surface
- Asymmetric splat shapes driven by individual particle spin directions
- Surface tension included (sigma = 0.5 N/m); relevant at these impact velocities for YSZ
- Staggered Y positions produce slightly different arrival times at the substrate

---

## Geometry

```
  y=300um  _________________________________________ top (outlet)
           |                                       |
           |                                       |
           |  ( P0 )      ( P1 )      ( P2 )       |
           |  75um,240    150um,260   225um,250     |
           |  omega +1e5  omega -1e5  omega +1e5    |
           |  CCW         CW          CCW           |
           |                                       |
  y=0      |_______________________________________| substrate (wall)
           x=0                                  x=300um
```

| Boundary | Type | Role |
|----------|------|------|
| `bottom` | wall | Rigid no-slip substrate; wall functions for k, omega, nut |
| `sides` | patch | `pressureInletOutletVelocity` + `totalPressure` |
| `top` | patch | Open outlet |
| `frontAndBack` | empty | 2D planar simulation |

---

## Particle Layout

| Particle | Centre X | Centre Y | Vx | Vy | Spin | Direction |
|----------|----------|----------|----|----|------|-----------|
| P0 | 75 um | 240 um | +5.0 m/s | -250 m/s | +1e5 rad/s | CCW |
| P1 | 150 um | 260 um | 0.0 m/s | -250 m/s | -1e5 rad/s | CW |
| P2 | 225 um | 250 um | -5.0 m/s | -250 m/s | +1e5 rad/s | CCW |

Staggered Y positions (240, 260, 250 um) simulate realistic in-flight dispersion
and give P0 a slightly earlier impact than P1 and P2.
Lateral velocity components (Vx) reflect divergent trajectories from the spray nozzle.

---

## Rotation Physics

```
CCW spin (omega = +1e5 rad/s):          CW spin (omega = -1e5 rad/s):

        <- top moves right                      -> top moves left
   v left              right ^            ^ left              right v
        -> bottom moves left                     <- bottom moves right

Counter-rotating pair (P0 CCW + P1 CW):
  Between P0 and P1, both surfaces move in the same direction (rightward).
  This creates a co-operative jet directed upward in the gap.
  Physical consequence: reduced splat spreading in the gap -> potential pore site.

Counter-rotating pair (P1 CW + P2 CCW):
  Same mechanism, symmetric to the above.
```

Rotation velocity at any cell centre (x, y) inside particle p with centre (cx, cy):

```
Ux = Vx_p + (-omega_p * (y - cy))
Uy = Vy_p + ( omega_p * (x - cx))
```

Stamped by `generateRotatingU.py` as a `nonuniform List<vector>` internal field.
Gas cells outside all particles retain (0 0 0).

---

## Material Properties

### YSZ Particle (molten at ~2700 C)

| Parameter | Value | Unit |
|-----------|-------|------|
| Radius | 25 | um |
| Diameter | 50 | um |
| Impact velocity Vy | -250 | m/s |
| Tip speed \|omega\|*R | 2.5 | m/s |
| Density rho | 5900 | kg/m^3 |
| Kinematic viscosity nu | 2e-6 | m^2/s |
| Reynolds number Re | 2,500 | -- |

### Argon Plasma Gas (~5000 K)

| Parameter | Value | Unit |
|-----------|-------|------|
| Density rho | 0.22 | kg/m^3 |
| Kinematic viscosity nu | 5e-6 | m^2/s |

### Interface

| Parameter | Value | Unit |
|-----------|-------|------|
| Surface tension sigma | 0.5 | N/m |

---

## Domain and Time

| Parameter | Value |
|-----------|-------|
| Domain | 300 x 300 x 1 um |
| Cells | 300 x 300 x 1 = 90,000 |
| Cell size | 1 um/cell |
| End time | 800 ns |
| max Co | 0.4 |
| Write interval | 20 ns |
| Estimated wall time | 30 to 60 minutes |

---

## Numerical Method

| Aspect | Choice |
|--------|--------|
| Solver | `interFoam` (VOF, incompressible two-phase) |
| Turbulence | k-omega SST (RAS) |
| Wall treatment | `kqRWallFunction`, `omegaWallFunction`, `nutkWallFunction` |
| Wall distance | `meshWave` (required by k-omega SST blending) |
| Time integration | Euler |
| Pressure-velocity | PIMPLE, 2 outer correctors, momentum predictor on |
| Divergence (momentum) | `Gauss linearUpwind grad(U)` |
| Divergence (alpha) | `Gauss vanLeer` (bounded) |
| Divergence (k, omega) | `Gauss upwind` (bounded, positive definite) |
| Linear solver (p) | PCG + DIC |
| Linear solver (U, k, omega) | PBiCG + DILU |

---

## Key Differences vs Single-Particle Laminar Case

| Aspect | Single Laminar | 3-Particle Turbulent (this case) |
|--------|---------------|----------------------------------|
| `turbulenceProperties` | `laminar` | `RAS kOmegaSST` |
| Extra fields | none | `k`, `omega`, `nut` |
| `fvSchemes` | no wallDist | `wallDist { method meshWave; }` |
| `fvSolution` | U only | U, UFinal, k, kFinal, omega, omegaFinal |
| `momentumPredictor` | no | yes |
| `nOuterCorrectors` | 1 | 2 |
| Particles | 1 | 3 (laterally spaced) |
| setFieldsDict regions | 1 `sphereToCell` | 3 `sphereToCell` entries |
| `generateRotatingU.py` | single ball loop | loop over PARTICLES list |
| Phase name | `alpha.ball` | `alpha.particle` |
| Domain width | 200 um | 300 um |
| Splat shape | smooth, symmetric | inter-particle jetting and merging |
| Gap physics | absent | counter-rotating vortex pairs |
| Wall clock time | ~5 min | ~30 to 60 min |

---

## Impact Timeline

| Time (ns) | Event |
|-----------|-------|
| 0 | P0 at (75, 240) um, P1 at (150, 260) um, P2 at (225, 250) um |
| 0 to 600 | Free-fall; k-omega SST wakes form behind each particle |
| 0 to 800 | Counter-rotating vortex pairs visible between P0-P1 and P1-P2 |
| ~960 | P0 first contact (240 um / 250 m/s) |
| ~980 | P2 contact (250 um / 250 m/s) |
| ~1040 | P1 contact (260 um / 250 m/s) -- lands on partially-spread P0 and P2 splats |
| 960 to 1200+ | Lateral jetting; P0 and P2 splats spread inward and merge under P1 |
| Throughout | Upward squirt jet in gap between P0 and P1; pore site formation |

---

## Repository Structure

```
plasmaSpray3Particles/
|
|-- plasmaSpray3Particles.py           # Main case generator (run on Windows)
|
|-- 0/
|   |-- alpha.particle                 # Phase fraction (YSZ = 1, gas = 0)
|   |-- U                              # Velocity (overwritten by generateRotatingU.py)
|   |-- p_rgh                          # Modified pressure
|   |-- k                              # Turbulent kinetic energy
|   |-- omega                          # Specific dissipation rate
|   |-- nut                            # Turbulent kinematic viscosity
|
|-- constant/
|   |-- transportProperties            # YSZ + Ar plasma properties, sigma=0.5
|   |-- turbulenceProperties           # RAS kOmegaSST
|   |-- g                              # Gravity (0 0 0)
|
|-- system/
|   |-- controlDict                    # endTime=8e-7, maxCo=0.4
|   |-- fvSchemes                      # vanLeer alpha, upwind k/omega, wallDist meshWave
|   |-- fvSolution                     # PIMPLE + all Final solvers + pRefCell
|   |-- blockMeshDict                  # 300x300x1 um
|   |-- setFieldsDict                  # 3x sphereToCell stamps alpha.particle=1
|
|-- generateRotatingU.py               # AUTO-GENERATED - writes 0/U for all 3 particles
|-- README.md                          # This file
```

---

## How to Run

### Requirements

- OpenFOAM v2412: https://openfoam.com
- Python 3.x: https://python.org
- ParaView v5.x: https://paraview.org
- WSL2 (Windows Subsystem for Linux)

### Step 1 -- Generate the case (Windows)

```bash
python plasmaSpray3Particles.py
```

Console output confirms particle layout and turbulence values:

```
  Particles:
    P0: ( 75.0,  240.0) um  Vy=-250 m/s  Vx=+5.0 m/s  omega=+1.00e+05 rad/s  tip=2.5 m/s
    P1: (150.0,  260.0) um  Vy=-250 m/s  Vx=+0.0 m/s  omega=-1.00e+05 rad/s  tip=2.5 m/s
    P2: (225.0,  250.0) um  Vy=-250 m/s  Vx=-5.0 m/s  omega=+1.00e+05 rad/s  tip=2.5 m/s
  k_init   = 600.00 m^2/s^2
  om_init  = 1.277e+07 rad/s
  nut_init = 4.699e-05 m^2/s
```

### Step 2 -- Copy to WSL

```bash
cp -r /mnt/c/Users/pedit/Downloads/plasmaSpray3Particles ~/
cd ~/plasmaSpray3Particles
```

### Step 3 -- Source OpenFOAM

```bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
```

### Step 4 -- Generate mesh

```bash
blockMesh
```

Expected: 90,000 cells, bounding box `(0,0,0) -> (300um, 300um, 1um)`.

### Step 5 -- Stamp rotation velocity field

```bash
python3 generateRotatingU.py
```

Expected:

```
  Particle 0 cell count: ~1963 / 90000
  Particle 1 cell count: ~1963 / 90000
  Particle 2 cell count: ~1963 / 90000
  Written: 0/U
```

Verify:

```bash
grep "internalField" 0/U
# Must show: internalField   nonuniform List<vector>
```

### Step 6 -- Stamp phase fraction

```bash
setFields
```

Expected: three circular regions of `alpha.particle = 1`.

### Step 7 -- Run in background (recommended, takes 30 to 60 min)

```bash
nohup interFoam > log.interFoam 2>&1 &
tail -f log.interFoam
```

### Step 8 -- Visualise

```bash
touch plasmaSpray3Particles.foam
cp -r ~/plasmaSpray3Particles /mnt/c/Users/pedit/Downloads/plasmaSpray3Particles_results
```

---

## Visualization in ParaView

### Setup

1. `File > Open` -> `plasmaSpray3Particles.foam` -> **OpenFOAMReader** -> Apply
2. `Filters -> Cell Data to Point Data` -> Apply

### Option A -- Splat shape and merging

```
Colour field : alpha.particle
Colour map   : Blue-Red
Press Play
-> Three separate circles collapse toward substrate
-> P0 and P2 splats spread inward; central gap closes
-> P1 arrives later onto partially-spread neighbours
-> Squirt jets visible at inter-splat collision fronts
```

### Option B -- Velocity field and rotation dipoles

```
Colour field : U -> Component X
Rescale      : Custom range -10 to +10 m/s
Colour map   : Cool to Warm
-> Blue-red dipole inside each particle (rotation)
-> P0 (CCW) and P1 (CW) dipoles mirror each other
-> Upward velocity jet in gap between particles after impact
```

### Option C -- Turbulent kinetic energy

```
Colour field : k
Colour map   : Rainbow
-> High k at each particle surface during free-fall
-> k peaks at substrate surface on impact
-> Three separate impact zones merge into single high-k region
```

### Option D -- Turbulent viscosity (wake and gap visualisation)

```
Colour field : nut
-> nut elevated in each particle wake
-> Counter-rotating gap regions show elevated nut between P0-P1 and P1-P2
-> Substrate nut spikes mark the three impact zones
```

### Option E -- Splat boundary evolution (contour filter)

```
Filters -> Contour
Contour by : alpha.particle
Isosurface value : 0.5
-> Clean splat edge tracking
-> Watch three contours merge into a single connected lamellar splat
```

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Entry method not found in wallDist` | k-omega SST needs wall distance | Add `wallDist { method meshWave; }` to fvSchemes |
| `Entry UFinal not found` | nOuterCorrectors > 1 requires Final entries | Add UFinal, kFinal, omegaFinal to fvSolution solvers |
| `Courant = 0` throughout | generateRotatingU.py not run in WSL | Run `python3 generateRotatingU.py` inside WSL case dir |
| `internalField uniform (0 0 0)` | Rotation script ran on Windows not WSL | Always run from `~/plasmaSpray3Particles` in WSL |
| k or omega goes negative | Time step too large early on | Reduce maxCo to 0.3 or initial deltaT to 1e-12 |
| Only one or two particles visible | setFields ran before generateRotatingU.py | Re-run in correct order: generateRotatingU -> setFields -> interFoam |
| alpha.particle overshoots above 1 | Interface compression too aggressive | Reduce cAlpha to 0.5 in fvSolution alpha.particle block |
| Very high iteration count on p_rgh | Density jump at YSZ/plasma interface | Normal; cumulative continuity error ~1e-7 is acceptable |

---

## Extending the Model

| Extension | What to change |
|-----------|----------------|
| More particles | Add entries to `PARTICLES` list in `plasmaSpray3Particles.py`; all files regenerate automatically |
| Different particle sizes | Add per-particle `"radius"` key and update setFieldsDict and generateRotatingU.py accordingly |
| Higher Reynolds number | Increase V or D; reduce nu_gas |
| Different turbulence model | Change `RASModel kOmegaSST` to `kEpsilon` or `realizableKE` |
| LES instead of RANS | Change `simulationType` to `LES`; add SGS model |
| Finer mesh for better splat resolution | Increase NX, NY to 600x600 |
| Oblique impact angle | Add larger `vx` components to individual particles |
| Rough substrate | Replace `bottom wall` with a grooved blockMeshDict |
| Thermal effects | Switch to `compressibleInterFoam` with energy equation |
| Elastic substrate | Couple with `solidDisplacementFoam` |

---

## Citation

```bibtex
@software{mishra_2026_plasmaspray3p,
  author    = {Mishra, A.},
  title     = {Plasma Spray Deposition - 3 Particles k-omega SST - OpenFOAM interFoam},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20554416},
  url       = {https://doi.org/10.5281/zenodo.20554416}
}
```

> Mishra, A. (2026). *Plasma Spray Deposition - 3 Particles k-omega SST - OpenFOAM interFoam*. Zenodo. https://doi.org/10.5281/zenodo.20554416

---

## Author

**akshansh11**
GitHub: https://github.com/akshansh11

---

## License

<p align="center">
  <a rel="license" href="http://creativecommons.org/licenses/by-nc/4.0/">
    <img alt="Creative Commons Licence" style="border-width:0; margin: 12px 0;"
      src="https://licensebuttons.net/l/by-nc/4.0/88x31.png"/>
  </a>
  <br/>
  <a rel="license" href="http://creativecommons.org/licenses/by-nc/4.0/">
    Creative Commons Attribution-NonCommercial 4.0 International License
  </a>
</p>

This work is licensed under a **Creative Commons Attribution-NonCommercial 4.0 International License**.

You are free to:
- **Share** -- copy and redistribute the material in any medium or format
- **Adapt** -- remix, transform, and build upon the material

Under the following terms:
- **Attribution** -- You must give appropriate credit to akshansh11 and link to this repository
- **NonCommercial** -- You may not use the material for commercial purposes

Copyright (c) 2026 akshansh11. All rights reserved for commercial use.
