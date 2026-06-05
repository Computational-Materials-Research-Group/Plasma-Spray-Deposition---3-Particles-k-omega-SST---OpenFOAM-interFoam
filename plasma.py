# -*- coding: utf-8 -*-
"""
Created on Fri Jun  5 10:25:41 2026

@author: Akshansh Mishra
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plasma Spray Deposition - 3 Particles (k-omega SST)
====================================================
Particle material : Yttria-Stabilised Zirconia (YSZ) - common TBC coating
Carrier gas       : Argon plasma (high-temperature, low viscosity)
Particle radius   : 25 um  (50 um diameter - typical plasma spray powder)
Impact speed      : 250 m/s downward  (plasma spray typical: 100-400 m/s)
Rotation          : mild spin ~1e5 rad/s (in-flight tumbling)
Domain            : 300 x 300 um  (wide enough for 3 laterally-spaced particles)
End time          : 800 ns  (all 3 particles impact within this window)

3 Particles layout (X positions spread across domain width):
  Particle 0: centre (75 um,  240 um)  Vy=-250 m/s  omega=+1e5 rad/s (CCW)
  Particle 1: centre (150 um, 260 um)  Vy=-250 m/s  omega=-1e5 rad/s (CW)
  Particle 2: centre (225 um, 250 um)  Vy=-250 m/s  omega=+1e5 rad/s (CCW)

Staggered Y positions mimic realistic in-flight dispersion/arrival timing.

Reynolds number (per particle):
  Re = V * D / nu_gas = 250 * 50e-6 / 5e-6 = 2,500  (turbulent at this scale)

Turbulence initial conditions (k-omega SST):
  I = 0.08  (8% - higher than single-shot; plasma jet is more turbulent)
  L = 0.07 * D = 3.5 um
  k     = 1.5 * (V*I)^2 = 1.5 * (250*0.08)^2 = 600 m^2/s^2
  omega = k^0.5 / (Cmu^0.25 * L)
        = 24.49 / (0.5477 * 3.5e-6)
        = ~12.77e6 rad/s
  nut   = k / omega = ~4.70e-5 m^2/s

WSL run sequence:
    blockMesh
    python3 generateRotatingU.py
    setFields
    interFoam
    touch plasmaSpray3Particles.foam
"""

import shutil
from pathlib import Path

OUT = Path("C:/Users/pedit/Downloads/plasmaSpray3Particles")

# ── Plasma spray physical parameters ─────────────────────────────────────────
V_IMPACT = 250.0       # m/s  impact speed (all particles same speed here)
D_PART   = 50e-6       # m    particle diameter (50 um)
R_PART   = D_PART / 2  # m    particle radius

# Carrier gas: hot argon plasma (~5000 K -> nu ~ 5e-6 m^2/s)
NU_GAS   = 5e-6        # m^2/s  kinematic viscosity of plasma gas

# ── 3-particle definitions ────────────────────────────────────────────────────
# Each entry: (cx_m, cy_m, vx_m/s, vy_m/s, omega_rad/s)
#   cx, cy  : initial centre in metres
#   vx      : horizontal velocity component (lateral drift)
#   vy      : vertical velocity (negative = downward)
#   omega   : angular velocity (+ = CCW, - = CW)
PARTICLES = [
    {"cx":  75e-6, "cy": 240e-6, "vx":  5.0, "vy": -V_IMPACT, "omega":  1e5},
    {"cx": 150e-6, "cy": 260e-6, "vx":  0.0, "vy": -V_IMPACT, "omega": -1e5},
    {"cx": 225e-6, "cy": 250e-6, "vx": -5.0, "vy": -V_IMPACT, "omega":  1e5},
]

N_PARTICLES = len(PARTICLES)

# ── Turbulence initial values (based on plasma jet conditions) ────────────────
I_TURB     = 0.08                             # 8% turbulent intensity
L_TURB     = 0.07 * D_PART                   # = 3.5e-6 m
K_INIT     = 1.5 * (V_IMPACT * I_TURB) ** 2  # = 600.0 m^2/s^2
CMU        = 0.09
OMEGA_INIT = (K_INIT ** 0.5) / (CMU**0.25 * L_TURB)
NUT_INIT   = K_INIT / OMEGA_INIT

# ── Domain ────────────────────────────────────────────────────────────────────
# 300 x 300 um to accommodate 3 laterally spread particles
DOMAIN_X_UM = 300   # micrometres
DOMAIN_Y_UM = 300
NX          = 300
NY          = 300


# ─────────────────────────────────────────────────────────────────────────────
def w(rel, txt):
    """Write a text file relative to OUT, creating parent dirs as needed."""
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', newline='\n', encoding='utf-8') as f:
        f.write(txt)
    print("  wrote:", rel)


# ─────────────────────────────────────────────────────────────────────────────
def make_control_dict():
    w("system/controlDict", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     interFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         8e-7;
deltaT          1e-11;
writeControl    adjustableRunTime;
writeInterval   2e-8;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable yes;
adjustTimeStep  yes;
maxCo           0.4;
maxAlphaCo      0.4;
maxDeltaT       1e-8;
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_fv_schemes():
    w("system/fvSchemes", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}

ddtSchemes       { default Euler; }
gradSchemes      { default Gauss linear; }
divSchemes
{
    div(rhoPhi,U)        Gauss linearUpwind grad(U);
    div(phi,alpha)       Gauss vanLeer;
    div(phirb,alpha)     Gauss linear;
    div(phi,k)           Gauss upwind;
    div(phi,omega)       Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes     { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes        { default corrected; }

wallDist
{
    method meshWave;
}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_fv_solution():
    w("system/fvSolution", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}

solvers
{
    "alpha.particle.*"
    {
        nAlphaCorr      2;
        nAlphaSubCycles 2;
        cAlpha          1;
    }

    "pcorr.*" { solver PCG;   preconditioner DIC;  tolerance 1e-5;  relTol 0;    }
    p_rgh      { solver PCG;  preconditioner DIC;  tolerance 1e-7;  relTol 0.05; }
    p_rghFinal { solver PCG;  preconditioner DIC;  tolerance 1e-7;  relTol 0;    }
    U          { solver PBiCG; preconditioner DILU; tolerance 1e-6;  relTol 0;   }
    UFinal     { solver PBiCG; preconditioner DILU; tolerance 1e-6;  relTol 0;   }

    k
    {
        solver          PBiCG;
        preconditioner  DILU;
        tolerance       1e-6;
        relTol          0;
    }
    kFinal
    {
        solver          PBiCG;
        preconditioner  DILU;
        tolerance       1e-6;
        relTol          0;
    }
    omega
    {
        solver          PBiCG;
        preconditioner  DILU;
        tolerance       1e-6;
        relTol          0;
    }
    omegaFinal
    {
        solver          PBiCG;
        preconditioner  DILU;
        tolerance       1e-6;
        relTol          0;
    }
}

PIMPLE
{
    momentumPredictor        yes;
    nOuterCorrectors         2;
    nCorrectors              3;
    nNonOrthogonalCorrectors 1;
    pRefCell                 0;
    pRefValue                0;
}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_block_mesh_dict():
    w("system/blockMeshDict", f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}

scale 1e-6;

vertices
(
    (0              0              0)
    ({DOMAIN_X_UM}  0              0)
    ({DOMAIN_X_UM}  {DOMAIN_Y_UM}  0)
    (0              {DOMAIN_Y_UM}  0)
    (0              0              1)
    ({DOMAIN_X_UM}  0              1)
    ({DOMAIN_X_UM}  {DOMAIN_Y_UM}  1)
    (0              {DOMAIN_Y_UM}  1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({NX} {NY} 1) simpleGrading (1 1 1)
);

edges ();

boundary
(
    bottom       {{ type wall;  faces ((0 1 5 4)); }}
    sides        {{ type patch; faces ((0 4 7 3)(1 2 6 5)); }}
    top          {{ type patch; faces ((3 7 6 2)); }}
    frontAndBack {{ type empty; faces ((0 3 2 1)(4 5 6 7)); }}
);
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_setfields_dict():
    """Generate one sphereToCell region per particle."""
    regions_lines = []
    for idx, p in enumerate(PARTICLES):
        cx = p["cx"]
        cy = p["cy"]
        regions_lines.append(f"""\
    // Particle {idx}
    sphereToCell
    {{
        centre  ({cx:.4e} {cy:.4e} 0);
        radius  {R_PART:.4e};
        fieldValues
        (
            volScalarFieldValue alpha.particle 1
        );
    }}
""")
    regions_block = "\n".join(regions_lines)

    w("system/setFieldsDict", f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      setFieldsDict;
}}

defaultFieldValues
(
    volScalarFieldValue alpha.particle 0
);

regions
(
{regions_block}
);
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_transport_properties():
    # YSZ particle: rho~5900 kg/m^3, nu~2e-6 m^2/s (molten at ~2700 C)
    # Plasma gas (Ar): rho~0.22 kg/m^3 at 5000 K, nu~5e-6 m^2/s
    w("constant/transportProperties", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}

// YSZ (Yttria-Stabilised Zirconia) molten particle properties at ~2700 C
// Ar plasma carrier gas properties at ~5000 K
phases (particle gas);
particle { transportModel Newtonian; nu 2e-6;  rho 5900; }
gas      { transportModel Newtonian; nu 5e-6;  rho 0.22; }

// Surface tension YSZ/Ar plasma - low due to high temperature
sigma 0.5;
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_turbulence_properties():
    w("constant/turbulenceProperties", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      turbulenceProperties;
}

simulationType  RAS;

RAS
{
    RASModel    kOmegaSST;
    turbulence  on;
    printCoeffs on;
}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_g():
    w("constant/g", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       uniformDimensionedVectorField;
    object      g;
}
dimensions  [0 1 -2 0 0 0 0];
value       (0 0 0);
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_alpha():
    w("0/alpha.particle", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      alpha.particle;
}
dimensions      [0 0 0 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    bottom       { type zeroGradient; }
    sides        { type inletOutlet; inletValue uniform 0; value uniform 0; }
    top          { type inletOutlet; inletValue uniform 0; value uniform 0; }
    frontAndBack { type empty; }
}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_p_rgh():
    w("0/p_rgh", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p_rgh;
}
dimensions      [1 -1 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    bottom       { type fixedFluxPressure; value uniform 0; }
    sides        { type totalPressure; p0 uniform 0; value uniform 0; }
    top          { type totalPressure; p0 uniform 0; value uniform 0; }
    frontAndBack { type empty; }
}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_u_placeholder():
    """Placeholder 0/U (overwritten by generateRotatingU.py)."""
    w("0/U", """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{
    bottom       { type noSlip; }
    sides        { type pressureInletOutletVelocity; value uniform (0 0 0); }
    top          { type pressureInletOutletVelocity; value uniform (0 0 0); }
    frontAndBack { type empty; }
}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_k():
    k_str = "{:.6e}".format(K_INIT)
    w("0/k", f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      k;
}}
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform {k_str};
boundaryField
{{
    bottom
    {{
        type            kqRWallFunction;
        value           uniform {k_str};
    }}
    sides
    {{
        type            inletOutlet;
        inletValue      uniform {k_str};
        value           uniform {k_str};
    }}
    top
    {{
        type            inletOutlet;
        inletValue      uniform {k_str};
        value           uniform {k_str};
    }}
    frontAndBack    {{ type empty; }}
}}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_omega():
    om_str = "{:.6e}".format(OMEGA_INIT)
    w("0/omega", f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      omega;
}}
dimensions      [0 0 -1 0 0 0 0];
internalField   uniform {om_str};
boundaryField
{{
    bottom
    {{
        type            omegaWallFunction;
        value           uniform {om_str};
    }}
    sides
    {{
        type            inletOutlet;
        inletValue      uniform {om_str};
        value           uniform {om_str};
    }}
    top
    {{
        type            inletOutlet;
        inletValue      uniform {om_str};
        value           uniform {om_str};
    }}
    frontAndBack    {{ type empty; }}
}}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_nut():
    nut_str = "{:.6e}".format(NUT_INIT)
    w("0/nut", f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      nut;
}}
dimensions      [0 2 -1 0 0 0 0];
internalField   uniform {nut_str};
boundaryField
{{
    bottom
    {{
        type            nutkWallFunction;
        value           uniform {nut_str};
    }}
    sides
    {{
        type            calculated;
        value           uniform {nut_str};
    }}
    top
    {{
        type            calculated;
        value           uniform {nut_str};
    }}
    frontAndBack    {{ type empty; }}
}}
""")


# ─────────────────────────────────────────────────────────────────────────────
def make_rotating_u_script():
    """
    Generate the helper script that writes a nonuniform 0/U field
    with correct rigid-body rotation + translation for EACH particle.
    Cells belonging to multiple particles (overlap) take the last particle's
    velocity - in practice the centres are far enough apart that overlap
    is zero at t=0.
    """

    # Serialise the particle list as Python literal data
    particle_data_lines = []
    for idx, p in enumerate(PARTICLES):
        particle_data_lines.append(
            f"    # Particle {idx}: CX={p['cx']*1e6:.1f}um "
            f"CY={p['cy']*1e6:.1f}um "
            f"omega={'%+.1e' % p['omega']} rad/s"
        )
        particle_data_lines.append(
            f"    {{"
            f"\"cx\": {p['cx']:.4e}, "
            f"\"cy\": {p['cy']:.4e}, "
            f"\"vx\": {p['vx']:.4e}, "
            f"\"vy\": {p['vy']:.4e}, "
            f"\"omega\": {p['omega']:.4e}"
            f"}},"
        )
    particle_block = "\n".join(particle_data_lines)

    script = f"""\
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# generateRotatingU.py  -  Plasma Spray 3-Particle version
# Run AFTER blockMesh, BEFORE setFields and interFoam.
# Writes 0/U with rigid-body rotation inside each particle.
# Cells NOT inside any particle get (0 0 0).

# ── Mesh parameters (must match blockMeshDict) ────────────────────────────────
NX  = {NX}
NY  = {NY}
DX  = {DOMAIN_X_UM}e-6 / NX   # = {DOMAIN_X_UM/NX:.2g} um per cell
DY  = {DOMAIN_Y_UM}e-6 / NY   # = {DOMAIN_Y_UM/NY:.2g} um per cell

# ── Particle radius (shared for all particles) ────────────────────────────────
R  = {R_PART:.4e}   # m  ({R_PART*1e6:.1f} um)
R2 = R * R

# ── Particle definitions ──────────────────────────────────────────────────────
# Each dict: cx, cy [m], vx, vy [m/s], omega [rad/s] (+ = CCW)
PARTICLES = [
{particle_block}
]

print("Building multi-particle velocity field for plasma spray...")
print(f"  Domain  : {DOMAIN_X_UM} x {DOMAIN_Y_UM} um  ({{NX}} x {{NY}} cells)")
print(f"  Radius  : {{R*1e6:.1f}} um per particle")
print(f"  Particles: {{len(PARTICLES)}}")
for i, p in enumerate(PARTICLES):
    tip = abs(p['omega']) * R
    print(f"  P{{i}}: centre=({{p['cx']*1e6:.1f}}, {{p['cy']*1e6:.1f}}) um  "
          f"Vimpact={{p['vy']:.0f}} m/s  omega={{p['omega']:+.1e}} rad/s  tip={{tip:.1f}} m/s")

n_cells = NX * NY
vels    = []
ball_counts = [0] * len(PARTICLES)

for j in range(NY):
    yc = (j + 0.5) * DY
    for i in range(NX):
        xc = (i + 0.5) * DX
        ux, uy = 0.0, 0.0
        # Check membership in each particle (last match wins for overlapping cells)
        for pidx, p in enumerate(PARTICLES):
            dx = xc - p['cx']
            dy = yc - p['cy']
            if dx*dx + dy*dy <= R2:
                # Rigid-body velocity: translation + rotation
                ux = p['vx'] + (-p['omega'] * dy)
                uy = p['vy'] + ( p['omega'] * dx)
                ball_counts[pidx] += 1
        vels.append((ux, uy))

print()
for i, cnt in enumerate(ball_counts):
    print(f"  Particle {{i}} cell count: {{cnt}} / {{n_cells}}")
print()

with open('0/U', 'w', newline='\\n', encoding='utf-8') as f:
    f.write('FoamFile\\n{{\\n')
    f.write('    version     2.0;\\n')
    f.write('    format      ascii;\\n')
    f.write('    class       volVectorField;\\n')
    f.write('    object      U;\\n')
    f.write('}}\\n\\n')
    f.write('dimensions      [0 1 -1 0 0 0 0];\\n\\n')
    f.write('internalField   nonuniform List<vector>\\n')
    f.write(f'{{n_cells}}\\n(\\n')
    for ux, uy in vels:
        f.write(f'({{ux:.6e}} {{uy:.6e}} 0)\\n')
    f.write(');\\n\\n')
    f.write('boundaryField\\n{{\\n')
    f.write('    bottom       {{ type noSlip; }}\\n')
    f.write('    sides        {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}\\n')
    f.write('    top          {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}\\n')
    f.write('    frontAndBack {{ type empty; }}\\n')
    f.write('}}\\n')

print("Written: 0/U")
print("Next: setFields  ->  interFoam")
"""

    out_path = OUT / 'generateRotatingU.py'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='\n', encoding='utf-8') as f:
        f.write(script)
    print("  wrote: generateRotatingU.py")


# ─────────────────────────────────────────────────────────────────────────────
def make_readme():
    particle_table = "\n".join([
        f"  P{i}: ({p['cx']*1e6:.0f}, {p['cy']*1e6:.0f}) um  "
        f"Vy={p['vy']:.0f} m/s  Vx={p['vx']:+.0f} m/s  "
        f"omega={p['omega']:+.2e} rad/s"
        for i, p in enumerate(PARTICLES)
    ])

    w("README.md", f"""\
# Plasma Spray Deposition - 3 Particles (k-omega SST) - OpenFOAM 2412

## Physical Setup

  Material  : YSZ (Yttria-Stabilised Zirconia) - typical TBC / thermal barrier coating
  Carrier   : Argon plasma gas (~5000 K, nu = 5e-6 m^2/s, rho = 0.22 kg/m^3)
  Particle D: {D_PART*1e6:.0f} um diameter  (radius {R_PART*1e6:.0f} um)
  Impact V  : {V_IMPACT:.0f} m/s

## Particle Layout

{particle_table}

  Staggered Y positions simulate realistic in-flight dispersion
  and slightly different arrival times at the substrate.

## Reynolds Number (per particle)

  Re = V * D / nu_gas = {V_IMPACT:.0f} * {D_PART:.0e} / {NU_GAS:.0e} = {V_IMPACT*D_PART/NU_GAS:.0f}
  -> Fully turbulent; k-omega SST required.

## Turbulence Model: k-omega SST

  I     = {I_TURB*100:.0f}%   (plasma jet is more turbulent than clean ballistic impact)
  L     = {L_TURB*1e6:.2f} um
  k     = {K_INIT:.1f} m^2/s^2
  omega = {OMEGA_INIT:.3e} rad/s
  nut   = {NUT_INIT:.3e} m^2/s

## Key Plasma Spray Physics Captured

  - Multiple simultaneous impacts: overlapping splat formation
  - Lateral spreading and merging of adjacent splats
  - Counter-rotating neighbours (P0 CCW, P1 CW, P2 CCW) create
    vortex interactions in the gaps between particles
  - Particle P1 arrives slightly later (higher Y start) -> impinges
    onto partially-spread splats from P0 and P2
  - Wake turbulence from leading particles affects trailing ones
    (realistic in dense plasma spray streams)

## Domain

  Width : {DOMAIN_X_UM} um
  Height: {DOMAIN_Y_UM} um
  Cells : {NX} x {NY} x 1 = {NX*NY:,}

## WSL Run Sequence

  cp -r /mnt/c/Users/pedit/Downloads/plasmaSpray3Particles ~/
  cd ~/plasmaSpray3Particles
  source /usr/lib/openfoam/openfoam2412/etc/bashrc
  blockMesh
  python3 generateRotatingU.py
  setFields
  interFoam
  touch plasmaSpray3Particles.foam

## ParaView Visualisation Tips

  Colour by: alpha.particle  -> splat shape and merging
  Colour by: U (mag)         -> impact jet and splashing velocity
  Colour by: k               -> turbulent KE; high at impact zones
  Colour by: nut             -> turbulent viscosity; wake between particles
  Filters -> Contour on alpha.particle (isovalue=0.5) -> splat boundary evolution
  Filters -> Glyph on U -> velocity arrows showing rotation dipoles

## To Add More Particles

  Edit the PARTICLES list in plasmaSpray3Particles.py.
  Each entry is a dict: cx, cy [m], vx, vy [m/s], omega [rad/s]
  setFieldsDict and generateRotatingU.py are generated automatically
  for however many particles are defined.
""")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 65)
    print("  PLASMA SPRAY DEPOSITION - {} PARTICLES (k-omega SST)".format(N_PARTICLES))
    print("=" * 65)
    print()
    print("  Particle D  = {:.0f} um".format(D_PART * 1e6))
    print("  Impact V    = {:.0f} m/s".format(V_IMPACT))
    print("  Re (per P)  = {:.0f}".format(V_IMPACT * D_PART / NU_GAS))
    print("  k_init      = {:.2f} m^2/s^2".format(K_INIT))
    print("  omega_init  = {:.3e} rad/s".format(OMEGA_INIT))
    print("  nut_init    = {:.3e} m^2/s".format(NUT_INIT))
    print()
    print("  Particles:")
    for i, p in enumerate(PARTICLES):
        tip = abs(p["omega"]) * R_PART
        print("    P{}: ({:5.0f}, {:5.0f}) um  Vy={:+.0f} m/s  "
              "Vx={:+.1f} m/s  omega={:+.1e} rad/s  tip={:.1f} m/s".format(
              i, p["cx"]*1e6, p["cy"]*1e6, p["vy"], p["vx"], p["omega"], tip))
    print()

    if OUT.exists():
        shutil.rmtree(OUT)
    for d in ['0', 'constant', 'system']:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    print("Directories created")

    print("\nSystem files...")
    make_control_dict()
    make_fv_schemes()
    make_fv_solution()
    make_block_mesh_dict()
    make_setfields_dict()

    print("\nConstant files...")
    make_transport_properties()
    make_turbulence_properties()
    make_g()

    print("\nInitial conditions...")
    make_alpha()
    make_p_rgh()
    make_u_placeholder()
    make_k()
    make_omega()
    make_nut()

    print("\nRotation script...")
    make_rotating_u_script()

    print("\nDocumentation...")
    make_readme()

    print()
    print("=" * 65)
    print("  DONE ->", OUT)
    print("=" * 65)
    print()
    print("WSL commands:")
    print("  cp -r /mnt/c/Users/pedit/Downloads/plasmaSpray3Particles ~/")
    print("  cd ~/plasmaSpray3Particles")
    print("  source /usr/lib/openfoam/openfoam2412/etc/bashrc")
    print("  blockMesh")
    print("  python3 generateRotatingU.py")
    print("  setFields")
    print("  interFoam")
    print("  touch plasmaSpray3Particles.foam")
    print()


if __name__ == "__main__":
    main()