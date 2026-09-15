# Crop Phenology Dynamics & Multi-Temporal Trajectory Analysis

## Executive & Scientific Summary

Agricultural food security, crop yield forecasting, and compliance with the European Union Common Agricultural Policy (CAP) require continuous, automated tracking of crop growth cycles. Satellite vegetation index time-series provide an objective, non-destructive method for observing field-scale canopy development, identifying critical phenological growth stages, and detecting drought- or frost-induced vegetative anomalies.

The `eo-mcp` phenology intelligence engine (`monitor_crop_phenology`) implements multi-temporal curve fitting and phenological milestone extraction based on:
1. **Time-Series Reconstruction & Smoothing**: Eliminating cloud contamination, aerosol noise, and sensor viewing geometry artifacts using asymmetric Gaussian and adaptive double logistic function fitting (Jönsson & Eklundh 2004, TIMESAT).
2. **Dynamic Amplitude Thresholding & Curvature Extremum Extraction**: Detecting Start of Season (SOS / greenup), Peak of Season (POS / maximum canopy biomass), and End of Season (EOS / senescence/harvest) (Zhang et al. 2003).
3. **Seasonal Integral & Biomass Proxy Calculation**: Integrating the area under the seasonal trajectory curve to estimate total vegetative productivity and photosynthetic duration.
4. **Climatological Anomaly Benchmarking**: Computing day-of-year (DOY) departures and cumulative biomass anomalies relative to long-term multi-year baselines.

---

## 1. Physical & Radiative Transfer Principles

### 1.1 The Crop Vegetative Growth Cycle
As an annual crop develops from germination to harvest, its biochemical composition and structural canopy architecture undergo predictable morphological transitions:
1. **Emergence & Early Vegetative Stage:** Low soil cover; spectral reflectance is dominated by the background soil curve ($\text{NDVI} \approx 0.15\text{--}0.25$).
2. **Stem Elongation & Canopy Expansion (Greenup):** Rapid production of chlorophyll-rich leaves and leaf layers. Red absorption increases while near-infrared mesophyll scattering escalates steeply.
3. **Anthesis & Heading (Peak of Season):** Full canopy closure ($\text{LAI} \ge 3.5\text{--}5.0$). Photosynthetic capacity peaks; NDVI reaches its seasonal maximum ($\text{NDVI}_{\max} \ge 0.75\text{--}0.90$).
4. **Grain Filling & Senescence:** Chlorophyll breaks down; leaves yellow and dry out. Near-infrared mesophyll reflectance collapses as internal cell structures desiccate.
5. **Harvest:** Abrupt drop to bare soil baseline or crop residue reflectance.

```
NDVI
  1.0 |                           Peak of Season (POS)
      |                                  /\
  0.8 |                                 /  \
      |                                /    \
  0.6 |                               /      \
      |        Start of Season (SOS) /        \  End of Season (EOS)
  0.4 |               +-------------+          +------------+
      |              /                                       \
  0.2 |  Bare Soil  /                                         \  Harvest
      +------------+-------------------------------------------+---------> Time (DOY)
      Jan         Mar            May          Jul             Sep        Nov
```

### 1.2 Satellite Time-Series Noise Dynamics
Raw satellite observations are frequently contaminated by residual sub-pixel clouds, cloud shadows, and variable atmospheric aerosol scattering. Because these atmospheric contaminants almost universally **depress** vegetation index values, the raw time series exhibits asymmetrical negative spikes. Rigorous phenological modeling requires upper-envelope filtering algorithms that favor upper-bound envelope values over depressed outliers.

---

## 2. Exact Mathematical Formulations

### 2.1 Double Logistic Time-Series Fitting (Jönsson & Eklundh 2004)
To model the unimodal rise and fall of seasonal crop greenness, `eo-mcp` fits a double logistic function $f(t)$ to the multi-temporal observations:

$$f(t) = c_1 + \frac{c_2}{1 + \exp\left(-c_3 (t - c_4)\right)} - \frac{c_2}{1 + \exp\left(-c_5 (t - c_6)\right)}$$

Where:
- $t$ is the day of year ($\text{DOY} \in [1, 365]$).
- $c_1$ represents the minimum base vegetation index (soil background).
- $c_2$ represents the seasonal amplitude ($\text{NDVI}_{\max} - c_1$).
- $c_3$ and $c_5$ govern the rate of greenup and senescence transitions.
- $c_4$ and $c_6$ represent the inflection dates (DOY) of maximum greenup and senescence rates.

### 2.2 Dynamic Amplitude Thresholding (Zhang et al. 2003)
Rather than relying on arbitrary fixed NDVI thresholds (which fail across varying soil types and climate zones), phenological transition dates are extracted using dynamic relative amplitude:

$$\text{Threshold}(k) = \text{NDVI}_{\min} + k \cdot \left(\text{NDVI}_{\max} - \text{NDVI}_{\min}\right)$$

Where $k \in (0, 1)$ is the relative amplitude fraction (typically $k = 0.20$ or $20\%$):
- **Start of Season (SOS):** The day of year when the fitted curve crosses $\text{Threshold}(0.20)$ with a positive slope ($\frac{df}{dt} > 0$).
- **Peak of Season (POS):** The day of year corresponding to the global maximum of the fitted profile:
  $$\text{POS} = \arg\max_t f(t)$$
- **End of Season (EOS):** The day of year when the fitted curve drops below $\text{Threshold}(0.20)$ with a negative slope ($\frac{df}{dt} < 0$).
- **Length of Season (LOS):** Total duration of the active vegetative period:
  $$\text{LOS} = \text{EOS} - \text{SOS}\quad [\text{days}]$$

### 2.3 Curvature Extremum Rate Method
Alternatively, Zhang et al. (2003) defined transition dates by finding the local extrema of the rate of change of curvature $K(t)$:

$$K(t) = \frac{\frac{d^2 f}{dt^2}}{\left(1 + \left(\frac{df}{dt}\right)^2\right)^{3/2}}$$

The local maxima and minima of $\frac{dK}{dt}$ correspond to the precise timing of canopy greenup initiation, maturity, senescence onset, and physiological dormancy.

### 2.4 Seasonal Biomass Proxy (Seasonal Integral)
The total seasonal biomass production is proportional to the integrated area under the curve between SOS and EOS, above the soil baseline:

$$\text{Integral}_{\text{season}} = \int_{\text{SOS}}^{\text{EOS}} \left(f(t) - \text{NDVI}_{\min}\right) dt$$

### 2.5 Climatological Phenological Anomalies
Departures from long-term normal conditions indicate drought stress, heatwaves, or unseasonable frosts:

$$\Delta \text{SOS} = \text{SOS}_{\text{observed}} - \overline{\text{SOS}}_{\text{baseline}}\quad [\text{days}]$$

$$\Delta \text{Biomass}\% = \frac{\text{Integral}_{\text{season}} - \overline{\text{Integral}}_{\text{baseline}}}{\overline{\text{Integral}}_{\text{baseline}}} \times 100\%$$

- A positive $\Delta \text{SOS} > +14\text{ days}$ indicates delayed planting or cold spring dormancy.
- A negative $\Delta \text{Biomass} < -20\%$ indicates significant crop yield failure or vegetative drought.

---

## 3. Sensor Configurations & Temporal Cadence

| Satellite System | Constellation Size | Revisit Time | Spatial Resolution | Multispectral Bands for Phenology |
|------------------|--------------------|--------------|--------------------|-----------------------------------|
| **Copernicus Sentinel-2** | 2 satellites (2A/2B) | 5 days (equator) | 10 m / 20 m | Band 4 (Red), Band 8 (NIR), Red Edge (B5/B6/B7) |
| **Landsat 8 & 9 (OLI)** | 2 satellites | 8 days (offset) | 30 m | Band 4 (Red), Band 5 (NIR) |
| **Harmonized Landsat-Sentinel (HLS)** | Virtual constellation | 2–3 days | 30 m (gridded) | Surface reflectance cross-calibrated to Sentinel-2 MSI |
| **MODIS (Terra / Aqua)** | 2 satellites | 1 day (daily) | 250 m / 500 m | Band 1 (Red), Band 2 (NIR) - Historical baseline |

---

## 4. Algorithmic Implementation in `eo-mcp`

The phenology trajectory engine is implemented in `src/eo_mcp/core/phenology.py` and exposed via `@eo_tool` `monitor_crop_phenology` in `src/eo_mcp/server.py`.

### 4.1 Trajectory Fitting & Milestone Extraction
```python
# src/eo_mcp/core/phenology.py

def analyze_crop_phenology_trajectory(
    observations: List[Dict[str, Any]],
    target_year: int = 2024,
    amplitude_fraction: float = 0.20
) -> Dict[str, Any]:
    """Extract agricultural phenology milestones (SOS, POS, EOS, LOS).
    
    Fits seasonal profile using double logistic smoothing, calculates
    dynamic threshold crossings, and derives seasonal integral.
    """
    # 1. Sort observations by Day of Year (DOY)
    # 2. Extract NDVI min and max
    # 3. Derive dynamic threshold = min + amplitude_fraction * (max - min)
    # 4. Identify SOS, POS, EOS and compute seasonal biomass integral
    ...
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Cloud Gaps During Critical Spring Greenup
In temperate and equatorial agricultural zones, persistent cloud cover during early spring or monsoon seasons can produce $30\text{--}45\text{ day}$ data voids, obscuring the rapid greenup phase.
- **Mitigation in `eo-mcp`:** The tool ingests dense multi-sensor time-series by combining Sentinel-2A, Sentinel-2B, and Landsat 8/9 observations into a single harmonized time series, reducing average revisit gaps to $\le 3\text{ days}$.

### 5.2 Smallholder Field Fragmentation & Mixed Pixels
In regions with fragmented smallholder farming (field sizes $< 0.5\text{ ha}$), a 30m Landsat pixel spans multiple fields with differing crop varieties, planting dates, and irrigation schedules.
- **Mitigation in `eo-mcp`:** High-resolution 10-meter Sentinel-2 Red/NIR bands resolve individual field parcels down to $0.1\text{ ha}$, isolating distinct crop phenologies.

### 5.3 Multi-Cropping Cycles (Double / Triple Cropping)
In subtropical and irrigated agricultural zones (e.g., the Nile Delta, Punjab, or Mekong Basin), farmers harvest two or three distinct crops per calendar year (e.g., winter wheat followed by summer rice).
- **Mitigation in `eo-mcp`:** The algorithm evaluates multiple local maxima across the annual cycle, separating individual cropping seasons rather than forcing a single annual envelope.

---

## 6. Peer-Reviewed References

- **Jönsson, P., & Eklundh, L. (2004).** TIMESAT—A program for analyzing time-series of satellite sensor data. *Computers & Geosciences*, 30(8), 833–845. [DOI: 10.1016/j.cageo.2004.05.006](https://doi.org/10.1016/j.cageo.2004.05.006)
- **Zhang, X., Friedl, M. A., Schaaf, C. B., Strahler, A. H., Hodges, J. C. F., Gao, F., Reed, B. C., & Huete, A. (2003).** Monitoring vegetation phenology using MODIS. *Remote Sensing of Environment*, 84(3), 471–475. [DOI: 10.1016/S0034-4257(02)00135-9](https://doi.org/10.1016/S0034-4257(02)00135-9)
