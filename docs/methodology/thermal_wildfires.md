# Active Wildfires, Fire Radiative Power & Post-Fire Burn Severity

## Executive & Scientific Summary

Wildfires represent catastrophic Earth system disturbances that threaten human settlements, cause severe ecological damage, and emit massive quantities of greenhouse gases and aerosols. Spaceborne remote sensing provides dual capabilities across the wildfire lifecycle:
1. **Real-Time Active Fire Detection & Fire Radiative Power (FRP)**: Detecting flaming combustion fronts at sub-kilometer spatial resolutions and quantifying instantaneous combustion rates (MW) in real time (Wooster 2003; Wooster et al. 2005; Schroeder et al. 2014; Giglio et al. 2016).
2. **Post-Fire Burn Severity & Ecosystem Impact Assessment**: Mapping vegetation canopy mortality, charring, and soil degradation using multi-temporal optical difference indices (Key & Benson 2006; Parks et al. 2014), aligned with European Forest Fire Information System (EFFIS) and USGS standards.

The `eo-mcp` wildfire intelligence suite provides `@eo_tool` implementations for `detect_active_wildfires` and `calculate_burn_severity`.

---

## 1. Physical & Radiative Transfer Principles

### 1.1 Planck's Radiation Law & Wien's Displacement
All physical bodies above absolute zero emit thermal electromagnetic radiation described by Planck's law:

$$B_\lambda(T) = \frac{2 h c^2}{\lambda^5 \left(e^{\frac{h c}{\lambda k_B T}} - 1\right)}$$

Where $h$ is Planck's constant, $c$ is the speed of light, and $k_B$ is Boltzmann's constant.

According to **Wien's Displacement Law**, the wavelength of peak spectral radiance ($\lambda_{\max}$) is inversely proportional to absolute thermodynamic temperature $T$:

$$\lambda_{\max} = \frac{b}{T} \quad (b \approx 2898\ \mu\text{m}\cdot\text{K})$$

- **Ambient Background Earth Surface ($T \approx 300\text{ K}$):** Emits radiation peaking in the thermal infrared window at $\lambda_{\max} \approx 9.7\ \mu\text{m}$.
- **Flaming Wildfire Combustion ($T \approx 800\text{--}1200\text{ K}$):** The emission peak shifts dramatically to the mid-infrared (MIR) atmospheric window at $\lambda_{\max} \approx 2.4\text{--}3.9\ \mu\text{m}$.

```
Spectral Radiance (W / m^2 / sr / um)
    ^
    |          Active Fire (T = 1000 K)
    |             /\   [Peaks at ~2.9 um in MIR]
    |            /  \
    |           /    \
    |          /      \
    |         /        \       Ambient Earth Background (T = 300 K)
    |        /          \            /\   [Peaks at ~9.7 um in TIR]
    |       /            \          /  \
    +------+--------------+--------+----+--------------------> Wavelength (um)
           1              3.9      8    11
```

Because radiance in the mid-infrared ($3.9\ \mu\text{m}$) increases as the fourth-to-fifth power of temperature ($L_{\text{MIR}} \propto T^4\text{--}T^5$), even a sub-pixel fire covering only $0.01\%\text{--}0.1\%$ of a 375m satellite pixel will trigger an immense brightness temperature jump ($\Delta T \gg 10\text{ K}$) in the mid-infrared channel, while the longwave thermal channel ($11\ \mu\text{m}$) remains largely unperturbed.

### 1.2 Post-Fire Spectral Shifts & Canopy Charring
Healthy forest canopies reflect strongly in the near-infrared ($\approx 840\text{ nm}$) due to mesophyll scattering and absorb in the shortwave infrared ($\approx 2200\text{ nm}$) due to canopy foliage moisture. When a severe wildfire burns through a forest:
- The photosynthetic canopy structure is incinerated, causing a steep decline in near-infrared reflectance ($\rho_{\text{NIR}} \downarrow$).
- Foliage moisture is completely evaporated and the ground is coated in black/gray carbonaceous char and ash, causing a substantial increase in shortwave infrared reflectance ($\rho_{\text{SWIR2}} \uparrow$).

Evaluating the pre-to-post-fire shift in the Normalized Burn Ratio isolates fire-induced canopy mortality from seasonal vegetative changes.

---

## 2. Exact Mathematical Formulations

### 2.1 Contextual Thermal Anomaly Detection (Giglio et al. 2016; Schroeder et al. 2014)
A pixel $(x, y)$ is evaluated using the brightness temperature difference between the mid-infrared ($T_4$ at $3.74\text{--}3.96\ \mu\text{m}$) and longwave infrared ($T_{11}$ at $11.0\text{--}11.45\ \mu\text{m}$):

$$\Delta T_{4-11} = T_4 - T_{11}$$

A candidate pixel is confirmed as an active fire hotspot if:
1. Absolute threshold test: $T_4 > 360\text{ K}$ (day) or $T_4 > 320\text{ K}$ (night).
2. Contextual background test:
   $$T_4 > \bar{T}_{4,\text{bg}} + 3.0 \cdot \sigma_{4,\text{bg}}$$
   $$\Delta T_{4-11} > \overline{\Delta T}_{4-11,\text{bg}} + 3.5 \cdot \sigma_{\Delta T,\text{bg}}$$
   Where $\bar{T}_{4,\text{bg}}$ and $\sigma_{4,\text{bg}}$ are the mean and standard deviation of valid non-fire background pixels in a dynamically expanding contextual window ($5 \times 5$ up to $21 \times 21$ pixels).

### 2.2 Fire Radiative Power (FRP) & Biomass Combustion (Wooster 2003; 2005)
Fire Radiative Power ($\text{FRP}$) quantifies the instantaneous rate of radiant heat energy emitted by combustion across all wavelengths:

$$\text{FRP} = \frac{A_{\text{pixel}} \cdot \sigma_{\text{SB}}}{a_{\text{MIR}}} \left(L_4 - \bar{L}_{4,\text{bg}}\right)\quad [\text{MW}]$$

Where:
- $A_{\text{pixel}}$ is the ground pixel area ($0.14\text{ km}^2$ for VIIRS 375m; $1.0\text{ km}^2$ for MODIS 1km).
- $\sigma_{\text{SB}} = 5.6704 \times 10^{-8}\ \text{W}/(\text{m}^2\cdot\text{K}^4)$ is the Stefan-Boltzmann constant.
- $a_{\text{MIR}} \approx 3.0 \times 10^{-9}\ \text{W}/(\text{m}^2\cdot\text{sr}\cdot\mu\text{m}\cdot\text{K}^4)$ is an empirical sensor-specific radiance fitting constant.
- $L_4$ and $\bar{L}_{4,\text{bg}}$ are the pixel and background mid-infrared spectral radiances.

**Combustion Rate Scaling:**
Wooster et al. (2005) proved that integrating FRP over time yields Fire Radiative Energy ($\text{FRE}$ in MJ), which is directly proportional to the total dry biomass fuel combusted ($M_{\text{fuel}}$ in kg):

$$M_{\text{fuel}} = C_{\text{biomass}} \cdot \text{FRE} = C_{\text{biomass}} \cdot \int_{t_1}^{t_2} \text{FRP}(t) dt$$

Where $C_{\text{biomass}} = 0.368 \pm 0.015\ \text{kg dry matter / MJ}$.

### 2.3 Post-Fire Burn Severity: dNBR and RBR
The Normalized Burn Ratio (NBR) is calculated as:

$$\text{NBR} = \frac{\rho_{\text{NIR}} - \rho_{\text{SWIR2}}}{\rho_{\text{NIR}} + \rho_{\text{SWIR2}}}$$

1. **Difference Normalized Burn Ratio (dNBR - Key & Benson 2006):**
   $$\text{dNBR} = \text{NBR}_{\text{pre}} - \text{NBR}_{\text{post}}$$

2. **Relativized Burn Ratio (RBR - Parks et al. 2014):**
   In regions with sparse pre-fire vegetation (e.g., arid shrublands, rocky slopes), pre-fire NBR is low, which artificially limits maximum dNBR. The Relativized Burn Ratio solves this by scaling against pre-fire canopy moisture:
   $$\text{RBR} = \frac{\text{dNBR}}{\text{NBR}_{\text{pre}} + 1.001}$$

### 2.4 EFFIS & USGS Burn Severity Classification
In accordance with the European Forest Fire Information System (EFFIS) and USGS protocols, `eo-mcp` classifies post-fire damage into standardized ecological severity tiers:

| Severity Class | dNBR Range | Ecological Damage Description |
|----------------|------------|--------------------------------|
| **Enhanced Regrowth** | $\text{dNBR} < -0.10$ | Post-fire flush, unburned herbaceous recovery |
| **Unburned / Stable** | $-0.10 \le \text{dNBR} < 0.10$ | Little or no change, unburned forest patches |
| **Low Severity** | $0.10 \le \text{dNBR} < 0.27$ | Surface litter scorched, canopy green and unburned |
| **Moderate Severity** | $0.27 \le \text{dNBR} < 0.66$ | Trees partially scorched, substantial surface fuel consumed |
| **High Severity** | $\text{dNBR} \ge 0.66$ | Deep organic layer consumed, canopy completely charred/killed |

---

## 3. Sensor Band Configurations & Spatial Resolutions

| Mission & Instrument | Band ID | Central $\lambda$ ($\mu$m) | Bandwidth ($\mu$m) | Resolution (m) | Primary Wildfire Function |
|----------------------|---------|---------------------------|-------------------|----------------|---------------------------|
| **VIIRS (S-NPP / NOAA-20/21)** | Band I4 | $3.74\ \mu\text{m}$ | $0.38$ | 375 m | Active fire thermal anomaly detection |
| **VIIRS (S-NPP / NOAA-20/21)** | Band I5 | $11.45\ \mu\text{m}$ | $1.90$ | 375 m | Background terrestrial surface temperature |
| **MODIS (Terra / Aqua)** | Band 21/22 | $3.96\ \mu\text{m}$ | $0.06$ | 1000 m | High-range fire detection (up to 500 K) |
| **MODIS (Terra / Aqua)** | Band 31 | $11.03\ \mu\text{m}$ | $0.50$ | 1000 m | Contextual background reference |
| **Sentinel-2 MSI** | Band 8 | $0.842\ \mu\text{m}$ | $0.115$ | 10 m | Near-infrared mesophyll reflection (pre/post NBR) |
| **Sentinel-2 MSI** | Band 12 | $2.190\ \mu\text{m}$ | $0.180$ | 20 m | Shortwave infrared char/ash absorption (pre/post NBR) |
| **Landsat 8/9 OLI** | Band 5 | $0.865\ \mu\text{m}$ | $0.030$ | 30 m | Near-infrared reflection (pre/post NBR) |
| **Landsat 8/9 OLI** | Band 7 | $2.200\ \mu\text{m}$ | $0.190$ | 30 m | Shortwave infrared reflection (pre/post NBR) |

---

## 4. Algorithmic Implementation in `eo-mcp`

The fire intelligence engine is implemented in `src/eo_mcp/core/wildfire.py` and exposed via `@eo_tool` functions `detect_active_wildfires` and `calculate_burn_severity`.

### 4.1 NASA FIRMS Active Fire Ingestion & Clustering
```python
# src/eo_mcp/core/wildfire.py

def fetch_firms_hotspots(
    bbox: List[float],
    days: int = 2,
    source: str = "VIIRS_NOAA20_NRT"
) -> List[Dict[str, Any]]:
    """Query live NASA FIRMS active fire hotspots.
    
    Parses latitude, longitude, brightness temperature (Kelvin),
    Fire Radiative Power (MW), acquisition time, and confidence.
    """
    ...


def cluster_fire_perimeters(
    hotspots: List[Dict[str, Any]],
    eps_km: float = 2.5,
    min_samples: int = 2
) -> List[Dict[str, Any]]:
    """Cluster discrete thermal hotspots into active fire perimeters using DBSCAN."""
    ...
```

### 4.2 Multi-Temporal Burn Severity Grid Computation
```python
# src/eo_mcp/core/wildfire.py

def calculate_burn_severity_dnbr(
    pre_nir: np.ndarray,
    pre_swir: np.ndarray,
    post_nir: np.ndarray,
    post_swir: np.ndarray,
    pixel_size_m: float = 20.0
) -> Dict[str, Any]:
    """Calculate dNBR and RBR grids, stratifying into EFFIS/USGS severity tiers.
    
    Dynamically aligns Sentinel-2 Band 8 (10m) to Band 12 (20m) grid using
    bilinear spline interpolation.
    """
    ...
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Thermal Detector Saturation over Intense Fire Fronts
Extreme mega-fires emitting radiant heat temperatures $> 380\text{ K}$ can saturate standard mid-infrared detectors (e.g., VIIRS I4 saturates at $367\text{ K}$).
- **Mitigation in `eo-mcp`:** NASA FIRMS algorithm switches dynamically to low-gain channels (e.g., VIIRS M13 channel with saturation threshold $> 650\text{ K}$) to preserve accurate FRP calculations over intense fronts.

### 5.2 Solar Specular Glint & Bare Soil False Alarms
Unvegetated dry lakebeds, solar panel installations, and metal rooftops can generate high solar specular reflection in mid-infrared wavelengths during clear midday passes, triggering false active fire detections.
- **Mitigation in `eo-mcp`:** Candidate hotspots undergo water-mask cross-referencing and solar geometry rejection (rejection if solar zenith angle is within $10^\circ$ of specular alignment).

### 5.3 Phenological Shift vs. Fire Severity
In Mediterranean or semi-arid ecosystems, a multi-month separation between pre-fire and post-fire imagery can capture seasonal drought senescence (summer drying), producing false positive dNBR values.
- **Mitigation in `eo-mcp`:** The tool computes the Relativized Burn Ratio (RBR) and recommends selecting anniversary-date pre-fire imagery (same calendar month one year prior) to eliminate seasonal phenological drift.

---

## 6. Peer-Reviewed References

- **Schroeder, W., Oliva, P., Giglio, L., & Csiszar, I. A. (2014).** The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment. *Remote Sensing of Environment*, 143, 85–96. [DOI: 10.1016/j.rse.2013.12.008](https://doi.org/10.1016/j.rse.2013.12.008)
- **Giglio, L., Schroeder, W., & Justice, C. O. (2016).** The collection 6 MODIS active fire detection algorithm and fire products. *Remote Sensing of Environment*, 178, 31–41. [DOI: 10.1016/j.rse.2016.02.054](https://doi.org/10.1016/j.rse.2016.02.054)
- **Wooster, M. J. (2003).** Fire radiative energy for quantitative study of biomass burning: Derivation from the BIRD experimental satellite and comparison to MODIS fire products. *Remote Sensing of Environment*, 86(1), 83–107. [DOI: 10.1016/S0034-4257(03)00070-1](https://doi.org/10.1016/S0034-4257(03)00070-1)
- **Wooster, M. J., Roberts, G., Perry, G. L. W., & Kaufman, Y. J. (2005).** Retrieval of biomass combustion rates and totals from fire radiative power observations: FRP derivation and calibration relationships. *Journal of Geophysical Research: Atmospheres*, 110(D24), D24311. [DOI: 10.1029/2005JD006318](https://doi.org/10.1029/2005JD006318)
- **Key, C. H., & Benson, N. C. (2006).** Landscape Assessment (LA): Sampling and analysis methods. *FIREMON: Fire Effects Monitoring and Inventory System*, USDA Forest Service GTR-RMRS-164-CD, pp. LA 1–55. [USDA Treesearch](https://www.fs.usda.gov/treesearch/pubs/24503)
- **Parks, S. A., Dillon, G. K., & Miller, C. (2014).** A new metric for quantifying burn severity: The Relativized Burn Ratio. *Remote Sensing*, 6(3), 1827–1844. [DOI: 10.3390/rs6031827](https://doi.org/10.3390/rs6031827)
