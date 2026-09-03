<a name="readme-top"></a>

<!--
Readme for the csiem_model_tfvaed_1.8 Cockburn Sound model
-->

<!-- PROJECT LOGO -->
<br />
<div align="center">

<h3 align="center">WAMSI Westport <em>Cockburn Sound Water Quality Model</em> — v1.8</h3>

  <p align="center">
    This repository houses the hydrodynamic-biogeochemical model for Cockburn Sound, a coastal embayment located near Perth, Western Australia.
    <br />
    <a href="https://SEAF-CS.github.io/csiem-science/"><strong>Explore the online manual »</strong></a>
    <br />
    <br />
    <a href="https://SEAF-CS.github.io/csiem-science/appendix-b-results-archive.html">View results archive</a>
    ·
    <a href="https://github.com/SEAF-CS/csiem_model_tfvaed_1.8/issues">Report Bug</a>
    ·
    <a href="https://github.com/SEAF-CS/csiem_model_tfvaed_1.8/issues">Request Feature</a>
  </p>
</div>

<br>

## About The Project

In 2022, the Western Australian Marine Science Institution (WAMSI) and Westport commissioned development of an independent hydrodynamic-biogeochemical model for [Cockburn Sound](https://en.wikipedia.org/wiki/Cockburn_Sound), located on the coast of Perth, Western Australia.

The model uses the [TUFLOW-FV](https://www.tuflow.com/products/tuflow-fv/) 3D finite-volume hydrodynamic model and the [AED](https://aquaticecodynamics.github.io/aed-science/) water quality model.

**Version 1.8 is the public reference simulation set.** It carries one canonical physics configuration — validated against the 1991 SMCWS field campaign and applied uniformly across every simulation — and, for the first time, extends the model back to the 1990s South Metropolitan Coastal Waters Study (SMCWS) era alongside the modern (2012–2024) years.

### What changed from 1.7

- **Canonical physics** (validated on the 1991 hindcast, now in every fvc): stability WL limit 15 m, 3D-cell depth threshold 0.5 m, global bottom roughness 0.03, horizontal viscosity/diffusivity 0.01 (limits 0.01–10), vertical viscosity/diffusivity floors 5.0e-5 / 9.0e-6, bulk latent heat 1.5e-3, shortwave albedo 0.09, diffusivity limiter dt 10 s. (The 1992/1994 hindcasts retain their validated seasonal latent-heat coefficient of 1.4e-3.)
- **Bathymetry overrides** (B-mesh runs): Success and Minstrel channel depths from the 2025 EIA survey, and the Swan-mouth tidal-choke fix restoring tidal transmission through the Blackwall throat.
- **1990s SMCWS hindcasts** added (B010 mesh, HD): Aug 1991, Mar–May 1992, Nov 1993–Dec 1994, with era-correct forcing (BARRA-PH weather, climatology/HYCOM ocean, corrected OBC polygons, Narrows-climatology river salinity, pre-Dawesville Peel-Harvey exchange, 1990s SDOOL flows).
- **Vertical layering** unified on the geometric-stretch scheme (`SEP_zlayer_0p6_0p75_geo_001.csv`) in all domain configurations.
- **Peel-Harvey exchange** now enters via both ocean entrances (Mandurah Channel + Dawesville Cut, 50:50) in all post-1994 simulations; pre-1994 simulations use the Mandurah Channel only (the Cut opened April 1994).
- **B010-mesh initial conditions** corrected (previously pointed at B009-mesh files).
- **Mangles Bay inflow** (Lake Richmond / Rockingham main drain, GLM-modelled outflow) enabled in all simulations.
- All outputs now archive under `output_archive/1.8.0/`.

## Built With

[![TUFLOW-FV](https://img.shields.io/badge/TUFLOW--FV-2025.2-yellow)](https://tuflow.com/products/tuflow-fv/)
[![AED](https://img.shields.io/badge/AED-2.3-brightgreen)](https://aquatic.science.uwa.edu.au/research/models/AED/quickstart.html)

## Getting Started

This repository contains the version-controlled model configuration. The large boundary-condition forcing store (the *environment repo*) is **not** tracked in git — it is referenced by the bc include files through the `$ENV_REPO` environment variable (TUFLOW-FV ≥2023.1 expands `$VAR` in control files).

### Prerequisites

- An active TUFLOW-FV binary and licence (download from [BMT TUFLOW](https://www.tuflow.com/products/tuflow-fv/)).
- The compatible AED plugin (FV-AED) from [UWA-AED](https://aquatic.science.uwa.edu.au/research/models/AED/quickstart.html).

### Cloning and executing the model

1. Clone this repo:
   ```sh
   git clone https://github.com/SEAF-CS/csiem_model_tfvaed_1.8.git
   ```
2. Obtain the forcing store and point `$ENV_REPO` at it:
   ```sh
   export ENV_REPO=/path/to/environment_repo
   ```
   Project machines: `G:\CSIEM\V1.7\MODEL\csiem_model_tfvaed_1.7\model_components\environment_repo` (shared on-prem mirror). External users: fetch the `bc_repo` from the Pawsey S3 project store (see `csiem_model_tools`).
3. Run a simulation from its `model_runs` folder with the provided launcher (sets `$ENV_REPO`, CPU/GPU options and the AED library):
   ```sh
   cd model_runs/HD
   ./run_tuflowfv_vm.sh csiem_B010_19910720_19910831.fvc
   ```

## Repository structure

| Folder                     | Content                                                                     |
| -------------------------- | --------------------------------------------------------------------------- |
| **model_components/includes**  | model configuration include files (domain, bc, ic, turbulence, wq, output) |
| **model_components/gis_repo**  | meshes, layers, bathymetry overrides, benthic zones, projections           |
| **model_components/environment_repo** | *(untracked)* large forcing files, referenced via `$ENV_REPO`       |
| **model_modifier_library**     | licensed-industry intakes/discharges and scenario modifiers               |
| **model_runs/HD · WQ · ECO · ST** | main simulation control files + run launcher                           |
| **output_archive**             | *(untracked)* simulation outputs, versioned per release (`1.8.0/…`)       |

## The 1.8 reference simulation set

| Period               | Mesh  | HD | WQ | ECO | Notes                                        |
| -------------------- | ----- |----|----|-----|----------------------------------------------|
| Jul–Aug 1991         | B010  | ✓  |    |     | SMCWS winter hindcast (validated)            |
| Feb–May 1992         | B010  | ✓  |    |     | SMCWS autumn hindcast                        |
| Nov 1993 – Dec 1994  | B010  | ✓  |    |     | SMCWS/HYCOM hindcast, pre/post Dawesville    |
| 2012–13 … 2023–24    | A002  | ✓  | ✓  |     | seven modern years                           |
| 2012–13, 2020–24     | B010  | ✓  | ✓  |     | modern years on the B mesh                   |
| Nov 2022 – Apr 2024  | A002/B010 |  |  | ✓  | full ecosystem configuration                 |

File naming: `csiem_{mesh}_{start}_{end}[_WQ|_ECO].fvc`; includes follow `{type}_{source}_{period}.fvc`.

## Analysis

Model inputs and outputs are processed with the [`csiem-marvl`](https://github.com/SEAF-CS/csiem-marvl) validation toolbox. Please contact the developers for further information.

## Contributing

Contributions from the user and developer community are welcome and **greatly appreciated**! Fork the repo and open a pull request, or open an issue with the tag "enhancement".

## Contact

Matt Hipsey - matt.hipsey@uwa.edu.au

Project link: [CSIEM online manual](https://SEAF-CS.github.io/csiem-science/)

## Acknowledgments

- Funding from the [WAMSI Westport Research Program](https://wamsi.org.au/research/programs/wamsi-westport-marine-science-program/)
- Gayan Gunaratne, Louise Bruce and the [BMT](https://www.tuflow.com/) software team
- Brendan Busch & Peisheng Huang from the [AED](https://aed.see.uwa.edu.au/) research group
- Oceanographic models from Ivica Janeković & Chari Pattiaratchi from the [UWA Oceans Institute](https://www.uwa.edu.au/oceans-institute)

<p align="right">(<a href="#readme-top">back to top</a>)</p>
