# Scientific Foundations & Methodology Overview

## Executive & Scientific Summary

The `eo-mcp` platform is an open-source, standardized Model Context Protocol (MCP) server that empowers artificial intelligence agents and human researchers to perform quantitative Earth Observation (EO) analysis directly across planetary data archives. Unlike black-box geospatial wrappers or purely heuristic visualization scripts, `eo-mcp` grounds every analytical capability in peer-reviewed physical principles, radiative transfer models, and international standards established by space agencies including the European Space Agency (ESA), the National Aeronautics and Space Administration (NASA), the United States Geological Survey (USGS), and the European Commission Joint Research Centre (EC JRC).

Modern satellite remote sensing operates across diverse regimes of the electromagnetic spectrum—from visible and near-infrared (VNIR) optical reflectance, shortwave infrared (SWIR), and thermal infrared (TIR) emissions, to active microwave Synthetic Aperture Radar (SAR) backscatter, satellite altimetry, and atmospheric absorption spectroscopy. Each regime requires rigorous mathematical modeling to convert raw digital numbers (DN) or top-of-atmosphere (TOA) radiances into physically meaningful biophysical variables, such as surface reflectance ($\rho$), land surface temperature ($T_s$), fire radiative power ($\text{FRP}$), radar cross section ($\sigma^0$), or vertical trace gas column densities ($N_v$).

This methodology documentation suite provides a comprehensive, publication-grade reference for the physical derivations, sensor configurations, algorithmic implementations, and validation benchmarks implemented across all analytical tools in `eo-mcp`.

---

## 1. Comprehensive Scientific Capability & Sensor Matrix

The following matrix connects each analytical tool in `eo-mcp` to its primary operational satellites, sensor instruments, physical mechanisms, canonical citations, and European Union / international policy frameworks.

| # | Tool Name | Analytical Domain | Primary Sensors & Constellations | Physical & Mathematical Foundation | Canonical Foundational Reference | Modern Validation Benchmark | Policy & Regulatory Framework |
|---|-----------|-------------------|-----------------------------------|-----------------------------------|-----------------------------------|------------------------------|-------------------------------|
| **1** | `calculate_spectral_index` | Multispectral Optical Indices | Sentinel-2 MSI, Landsat 8/9 OLI, MODIS | Chlorophyll absorption, mesophyll scattering, SWIR water absorption | Rouse et al. (1974); Tucker (1979); McFeeters (1996); Gao (1996) | Huete et al. (2002); Xu (2006) | Common Agricultural Policy (CAP); EU Biodiversity Strategy 2030 |
| **2** | `detect_dark_vessels` | Maritime Radar Surveillance | Sentinel-1 C-SAR (IW mode) | Microwave C-band backscatter, CA-CFAR thresholding, AIS cross-correlation | Finn & Johnson (1968); Novak et al. (1993); Crisp (2004) | Stasolla & Greidanus (2016); Pelich et al. (2019) | EU Maritime Security Strategy (EUMSS); MSFD 2008/56/EC |
| **3** | `analyze_coastal_erosion` | Coastal Dynamics & Shorelines | Sentinel-2 MSI, Landsat 8/9 OLI | Waterline MNDWI segmentation, Otsu variance optimization, DSAS transects | Otsu (1979); Thieler et al. (2009) | Himmelstoss et al. (2018); Vos et al. (CoastSat, 2019) | EU Integrated Coastal Zone Management (ICZM); EU Adaptation Strategy |
| **4** | `simulate_sea_level_rise` | Coastal Inundation & Sea Level Rise | Copernicus DEM GLO-30, TanDEM-X | 8-connected hydrologic flood-fill, extreme total water level, vertical datum | Poulter & Halpin (2008); Gesch (2009) | Gesch (2018); Fox-Kemper et al. (IPCC AR6, 2021) | EU Floods Directive (2007/60/EC); UN SDG 13 (Climate Action) |
| **5** | `detect_active_wildfires` | Active Fires & Fire Radiative Power | VIIRS 375m (S-NPP, NOAA-20/21), MODIS 1km | Mid-infrared (3.9 µm) thermal radiance anomaly, Planck radiance inversion | Wooster (2003); Wooster et al. (2005) | Schroeder et al. (2014); Giglio et al. (2016) | Copernicus Emergency Management Service (CEMS); EU Civil Protection |
| **6** | `calculate_burn_severity` | Post-Fire Burn Severity & Scars | Sentinel-2 MSI, Landsat 8/9 OLI | NIR mesophyll collapse, SWIR charring absorption, dNBR and RBR metrics | Key & Benson (FIREMON, 2006) | Parks et al. (2014) | European Forest Fire Information System (EFFIS); EU Forest Strategy 2030 |
| **7** | `monitor_atmospheric_emissions` | Tropospheric Trace Gas Emissions | Sentinel-5P TROPOMI spectrometer | Differential Optical Absorption Spectroscopy (DOAS), Air Mass Factors | Veefkind et al. (2012) | van Geffen et al. (2020) | EU Ambient Air Quality Directive (2008/50/EC); EU Methane Reg. (2024/1787) |
| **8** | `analyze_reservoir_drought` | Surface Water Dynamics & Drought | Landsat multi-decadal series, Sentinel-2 MSI | Multi-decadal surface water recurrence, occurrence transition matrix | Pekel et al. (Nature 2016) | Busker et al. (2019) | EU Water Framework Directive (WFD 2000/60/EC); UN SDG 6.6 |
| **9** | `analyze_urban_heat_island` | Land Surface Temperature & UHI | Landsat 8/9 TIRS, Sentinel-2 (NDVI) | Thermal Radiative Transfer Equation (RTE), Planck inversion, FVC emissivity | Valor & Caselles (1996); Sobrino et al. (2004) | Sobrino et al. (2008); Jiménez-Muñoz et al. (2009) | EU Urban Agenda; WHO Heat Health Action Plans |
| **10** | `monitor_crop_phenology` | Agricultural Phenology Dynamics | Sentinel-2 MSI, Harmonized Landsat-Sentinel | Time-series filtering (TIMESAT), harmonic curve fitting, curvature extrema | Zhang et al. (2003); Jönsson & Eklundh (TIMESAT, 2004) | Bolton et al. (2020) | Common Agricultural Policy (CAP) Agri-Environmental Indicators |
| **11** | `get_elevation_profile` | Topographic Geodesy & Terrain | Copernicus DEM GLO-30 | Horn finite-difference surface normal gradient, slope and aspect extraction | Horn (1981); European Space Agency (2020) | Guth & Geoffroy (2021) | EU INSPIRE Directive; Copernicus Space Component Data Access |
| **12** | `detect_water_sar` | SAR Hydrological Water Delineation | Sentinel-1 C-SAR (VV/VH polarizations) | Microwave specular reflection away from radar sensor, bimodal backscatter | Twele et al. (2016) | Bioresita et al. (2018) | Copernicus Emergency Management Service Floods; EU Floods Directive |
| **13** | `assess_location_hazard` | Multi-Hazard Planetary Assessment | Multi-sensor federation (optical, SAR, DEM) | Turnkey composite evaluation linking inundation, fire, erosion, heat, and vessels | Composite across 10 core scientific domains | Composite across validation studies | EU Green Deal; Horizon Europe Climate Services Framework |
| **14** | `environmental_site_audit` | Environmental Baseline Audit | Multi-sensor federation (Sentinel-1/2/5P, DEM) | Comprehensive baseline auditing of vegetation, terrain, air quality, and water | Composite across 10 core scientific domains | Composite across validation studies | EU Environmental Impact Assessment (EIA) Directive 2011/92/EU |
| **15** | `run_geospatial_script` | Sandboxed Geospatial Compute | Client-provided geospatial raster/vector data | Sandboxed execution of NumPy, Rasterio, Shapely, and GeoPandas workflows | Open Geospatial Consortium (OGC) specifications | GDAL / GEOS architecture standards | Open Data & FAIR Scientific Data Principles |

---

## 2. Radiative Transfer & Physical Regimes

The analytical architecture of `eo-mcp` is organized around four core physical observation regimes:

```
+-----------------------------------------------------------------------------------+
|                           ELECTROMAGNETIC SPECTRUM REGIMES                        |
+--------------------------+-----------------------+--------------------------------+
| Regime                   | Wavelength Range      | Physical Interaction Mechanism |
+--------------------------+-----------------------+--------------------------------+
| Visible & Near-Infrared  | 0.4 - 1.0 um          | Electronic molecular transitions,|
| (VNIR)                   |                       | chlorophyll absorption,        |
|                          |                       | spongy mesophyll scattering    |
+--------------------------+-----------------------+--------------------------------+
| Shortwave Infrared       | 1.0 - 2.5 um          | Liquid water vibrational bands,|
| (SWIR)                   |                       | hydroxyl/clay absorption,      |
|                          |                       | post-fire charcoal contrast    |
+--------------------------+-----------------------+--------------------------------+
| Thermal Infrared         | 8.0 - 14.0 um         | Terrestrial blackbody emission,|
| (TIR)                    |                       | kinetic temperature,           |
|                          |                       | spectral emissivity            |
+--------------------------+-----------------------+--------------------------------+
| Microwave Synthetic      | 3.75 - 7.5 cm         | Coherent backscatter,          |
| Aperture Radar (SAR)     | (C-band: ~5.55 cm)    | surface roughness, dielectric  |
|                          |                       | constant, corner reflection    |
+--------------------------+-----------------------+--------------------------------+
```

### 2.1 Optical Radiance to Surface Reflectance
For optical multispectral sensors (Sentinel-2 MSI, Landsat 8/9 OLI), Top-of-Atmosphere (TOA) radiance $L_{\text{TOA}}$ includes significant contributions from Rayleigh atmospheric scattering and aerosol path radiance:

$$L_{\text{TOA}}(\lambda) = \frac{\rho_{\text{surf}}(\lambda) \cdot E_0(\lambda) \cdot \cos(\theta_s)}{\pi \cdot d_E^2} \cdot \tau_{\text{down}}(\lambda) \cdot \tau_{\text{up}}(\lambda) + L_{\text{path}}(\lambda)$$

Where:
- $\rho_{\text{surf}}(\lambda)$ is the bottom-of-atmosphere (BOA) surface reflectance.
- $E_0(\lambda)$ is the mean exo-atmospheric solar irradiance.
- $\theta_s$ is the solar zenith angle.
- $d_E$ is the Earth-Sun distance in astronomical units (AU).
- $\tau_{\text{down}}(\lambda)$ and $\tau_{\text{up}}(\lambda)$ are atmospheric downward and upward transmittances.
- $L_{\text{path}}(\lambda)$ is the atmospheric path radiance.

In `eo-mcp`, all spectral index and vegetation calculations prioritize Level-2A (L2A) surface reflectance products (BOA) retrieved from open cloud-optimized GeoTIFF (COG) catalogs, ensuring atmospheric scattering effects are rigorously compensated prior to ratio calculation.

### 2.2 Thermal Infrared Radiative Transfer
In the thermal infrared window (10.0–12.5 µm), the radiative transfer equation for a cloud-free atmosphere observed at sensor radiance $L_\lambda$ is modeled as:

$$L_\lambda = \left[\varepsilon_\lambda B_\lambda(T_s) + (1 - \varepsilon_\lambda) L_\lambda^\downarrow\right] \tau_\lambda + L_\lambda^\uparrow$$

Where:
- $\varepsilon_\lambda$ is the land surface emissivity.
- $B_\lambda(T_s)$ is the spectral Planck blackbody radiance at surface kinetic temperature $T_s$.
- $L_\lambda^\downarrow$ is the downward atmospheric downwelling thermal radiance.
- $L_\lambda^\uparrow$ is the upward atmospheric path thermal radiance.
- $\tau_\lambda$ is the atmospheric transmittance.

Inverting Planck's radiation law enables precise derivation of the top-of-atmosphere brightness temperature $T_B$, which is subsequently corrected for surface emissivity derived from fractional vegetation cover (FVC).

### 2.3 Synthetic Aperture Radar (SAR) Microwave Backscatter
Synthetic Aperture Radar operates independently of solar illumination and penetrates clouds and precipitation. The normalized radar cross section (NRCS, $\sigma^0$) describes the radar backscatter per unit surface area:

$$\sigma^0 = \frac{4 \pi}{\lambda^2} \cdot |S_{pq}|^2$$

Where $S_{pq}$ represents the scattering matrix element for transmitted polarization $q$ and received polarization $p$ (e.g., VV or VH). 
- **Smooth Water Surfaces:** Act as specular reflectors, scattering incoming microwave energy away from the monostatic radar antenna, resulting in deeply attenuated backscatter ($\sigma^0_{\text{VV}} < -16\text{ dB}$).
- **Vessel Structures:** Act as dihedral and trihedral corner reflectors, returning strong coherent backscatter ($\sigma^0_{\text{VV}} \gg 0\text{ dB}$) that rises prominently above surrounding ocean clutter.
- **Biogenic and Hydrocarbon Slicks:** Dampen capillary and short gravity waves through the Marangoni effect, creating stark dark patches ($\sigma^0_{\text{VV}} < -22\text{ dB}$) against ambient sea clutter.

---

## 3. High-Performance Architectural Patterns in `eo-mcp`

### 3.1 Zero-Config Public Cloud Streaming
`eo-mcp` connects directly to open STAC APIs (SpatioTemporal Asset Catalog) and AWS / NASA / Planetary Computer public cloud archives:
- **Earth Search by Element 84:** Sentinel-2 L2A COGs on AWS S3 (`s3://sentinel-cogs`).
- **Planetary Computer STAC:** Landsat 8/9 Collection 2 Level-2, Copernicus DEM GLO-30.
- **NASA FIRMS Open API:** Live thermal hotspots from VIIRS and MODIS.
- **Copernicus Data Space Ecosystem (CDSE):** Sentinel-1 SAR and Sentinel-5P TROPOMI.

### 3.2 Windowed COG Streaming via HTTP Range Requests
Rather than downloading multi-gigabyte satellite granules (e.g., a standard 600 MB Sentinel-2 SAFE zip or 1 GB Landsat archive), `eo-mcp` uses Rasterio's GDAL virtual file system (`/vsicurl/`) and HTTP GET range requests. It streams only the exact sub-window bounded by the user's region of interest (ROI):
- Reduces network transfer by $>98\%$.
- Enables sub-second retrieval of 10-meter resolution spectral and elevation arrays.
- Eliminates local disk caching bottlenecks.

---

## 4. Navigation to Domain Methodology Chapters

For exhaustive derivations, sensor specifications, code walkthroughs, and verified literature citations, consult the individual methodology chapters:

1. [Multispectral Optical Indices (`spectral_indices.md`)](spectral_indices.md) — Mathematical formulations for NDVI, NDWI, MNDWI, NBR, and EVI; sensor band mappings and saturation mechanics.
2. [Maritime SAR & Target Detection (`maritime_radar.md`)](maritime_radar.md) — CA-CFAR derivation, radar cross section backscatter physics, vessel size estimation, and AIS transponder cross-correlation.
3. [Coastal Dynamics & Shoreline Retreat (`coastal_dynamics.md`)](coastal_dynamics.md) — Otsu automated waterline thresholding, DSAS baseline perpendicular transects, and multidecadal erosion metrics.
4. [Inundation & Digital Elevation Models (`inundation_dem.md`)](inundation_dem.md) — 8-connected hydrologic flood-fill modeling, Copernicus DEM GLO-30 vertical error propagation, and IPCC AR6 sea-level rise scenarios.
5. [Wildfire Radiative Power & Burn Severity (`thermal_wildfires.md`)](thermal_wildfires.md) — Mid-infrared 3.9 µm thermal anomaly detection, Fire Radiative Power (FRP) scaling, and dNBR/RBR severity classification.
6. [Atmospheric Chemistry & Air Quality (`atmospheric_chemistry.md`)](atmospheric_chemistry.md) — Sentinel-5P TROPOMI DOAS column density retrieval, Air Mass Factors, and European Air Quality thresholds.
7. [Surface Water Dynamics & Drought (`surface_water_drought.md`)](surface_water_drought.md) — JRC global surface water recurrence transition matrix, reservoir hypsometry, and multi-temporal water shrinkage.
8. [Urban Heat Island & Land Surface Temperature (`urban_heat_island.md`)](urban_heat_island.md) — Radiative transfer single-channel LST inversion, Sobrino emissivity estimation, and urban thermal anomaly mapping.
9. [Crop Phenology Dynamics (`crop_phenology.md`)](crop_phenology.md) — Multi-temporal vegetation index filtering, TIMESAT smoothing algorithms, and curvature extremum phenological milestone extraction.
10. [Authoritative Scientific References (`references.md`)](references.md) — Complete bibliographic compilation of all 40 verified peer-reviewed publications and institutional reports.
11. [BibTeX Database (`references.bib`)](references.bib) — Machine-readable BibTeX database with complete verified DOIs.
