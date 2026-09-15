# Surface Water Dynamics, Reservoirs & Hydrological Drought

## Executive & Scientific Summary

Freshwater scarcity, climate change-induced multi-year droughts, and unsustainable agricultural abstractions pose existential threats to global water security, agricultural food production, and hydroelectric energy generation. Sustainable Development Goal (SDG) Target 6.6 mandates international monitoring and protection of water-related ecosystems, while the European Union Water Framework Directive (WFD 2000/60/EC) requires systematic assessment of surface water status and reservoir storage.

The `eo-mcp` hydrological intelligence engine (`analyze_reservoir_drought` and `detect_water_sar`) integrates multi-decadal optical satellite observations and high-resolution synthetic aperture radar (SAR) to quantify:
1. **Multi-Decadal Surface Water Dynamics & Transition Modeling**: Tracking long-term shifts in permanent, seasonal, and desiccated water bodies using the European Commission Joint Research Centre (EC JRC) global surface water methodology (Pekel et al. 2016, Nature).
2. **Reservoir Surface Area & Volumetric Depletion**: Quantifying percentage contraction of water body surface extent ($\Delta A\%$) and integrating area-elevation hypsometric profiles for storage volume estimation.
3. **All-Weather Dual-Polarization SAR Water Delineation**: Penetrating persistent cloud cover during monsoon flood peaks and winter storms using Sentinel-1 C-band specular backscatter thresholding (Twele et al. 2016; Bioresita et al. 2018).

---

## 1. Physical & Radiative Transfer Principles

### 1.1 Optical Absorption vs. Specular Radar Scattering
Water exhibits distinctive, complementary physical interactions across the electromagnetic spectrum:

- **Optical Reflectance (VNIR/SWIR):** Pure liquid water strongly absorbs near-infrared and shortwave infrared radiation ($> 800\text{ nm}$), with absorption coefficients increasing by four orders of magnitude between the blue band ($0.45\ \mu\text{m}$) and the shortwave infrared ($1.6\ \mu\text{m}$). Consequently, in Modified Normalized Difference Water Index (MNDWI) imagery, open water bodies appear intensely bright against absorbing soils and vegetation.
- **Microwave Radar Backscatter (SAR C-Band):** Calm open water surfaces act as near-ideal **specular reflectors** for microwave radar pulses ($\lambda \approx 5.55\text{ cm}$). Rather than scattering energy back toward the satellite antenna, the incident radar wave bounces forward away from the sensor. The resulting radar cross section is extremely low ($\sigma^0_{\text{VV}} < -16.0\text{ dB}$ to $-24.0\text{ dB}$), appearing as crisp, pitch-black regions in radar imagery.

```
OPTICAL (Clear Day):
Sun --------> Water Surface --------> Total SWIR Absorption (Water appears black in SWIR)

MICROWAVE SAR (All-Weather / Night):
Radar Pulse --------> Smooth Water Surface --------> Specular Forward Reflection
(Away from satellite antenna -> Zero backscatter return -> Water appears black in SAR)
```

### 1.2 Hydrological Drought & Reservoir Shoreline Retreat
As reservoir water levels drop during prolonged droughts:
- The perimeter shoreline recedes toward the central bathymetric thalweg.
- Submerged mudflats and littoral sediments dry out, shifting their spectral signature from low-reflectance saturated mud to high-reflectance dry bare soil.
- The transition from permanent water to seasonal water, and ultimately to lost water, creates an observable spatial progression across decadal satellite records.

---

## 2. Exact Mathematical Formulations

### 2.1 Multi-Decadal Water Occurrence & Transition Matrix (Pekel et al. 2016)
For any spatial pixel $(x, y)$, let $N_{\text{valid}}(x, y)$ be the total count of clear-sky satellite observations across a multi-year epoch, and $N_{\text{water}}(x, y)$ be the count of observations classified as water.

1. **Water Occurrence Frequency ($O$):**
   $$O(x, y) = \frac{N_{\text{water}}(x, y)}{N_{\text{valid}}(x, y)} \times 100\%$$

2. **Hydrological Water Classes:**
   - **Permanent Water:** $O(x, y) \ge 80\%$ (inundated continuously throughout the year).
   - **Seasonal / Ephemeral Water:** $20\% \le O(x, y) < 80\%$ (inundated during rainy season or flood cycles).
   - **Non-Water / Terrestrial:** $O(x, y) < 20\%$.

3. **Surface Water Transition Matrix ($\mathcal{M}$):**
   Comparing a historical baseline epoch $T_{\text{hist}}$ with a modern epoch $T_{\text{recent}}$:
   $$\mathcal{M}(x, y) = \begin{cases}
   \text{Permanent} & \text{if } O_{\text{hist}} \ge 80\% \land O_{\text{recent}} \ge 80\% \\
   \text{Lost Water (Desiccated)} & \text{if } O_{\text{hist}} \ge 80\% \land O_{\text{recent}} < 20\% \\
   \text{New Water (Flooded/Dam)} & \text{if } O_{\text{hist}} < 20\% \land O_{\text{recent}} \ge 80\% \\
   \text{Seasonal Drying} & \text{if } O_{\text{hist}} \ge 80\% \land 20\% \le O_{\text{recent}} < 80\%
   \end{cases}$$

### 2.2 Reservoir Surface Area Contraction & Drought Metrics
Let $A_{\text{baseline}}$ be the historic surface water area (hectares) at nominal conservation capacity, and $A_{\text{recent}}$ be the modern observed surface water extent.

1. **Percentage Area Contraction ($\Delta A\%$):**
   $$\Delta A\% = \frac{A_{\text{recent}} - A_{\text{baseline}}}{A_{\text{baseline}}} \times 100\%$$

2. **Drought Depletion Severity:**
   - **`NORMAL`:** $\Delta A\% \ge -10\%$ (Surface area within $10\%$ of conservation pool).
   - **`MODERATE_DROUGHT`:** $-30\% \le \Delta A\% < -10\%$ (Noticeable reservoir margin drawdown).
   - **`SEVERE_DROUGHT`:** $-60\% \le \Delta A\% < -30\%$ (Critical reservoir contraction).
   - **`CRITICAL_DESICCATION`:** $\Delta A\% < -60\%$ (Catastrophic water loss, imminent storage failure).

### 2.3 Hypsometric Area-Elevation-Volume Approximation
When a digital elevation model of the exposed reservoir basin is available, storage volume $V$ is computed by numerical integration of the hypsometric surface area-elevation curve $A(z)$:

$$V = \int_{z_{\min}}^{z_{\text{water}}} A(z) dz \approx \sum_{i=1}^{K-1} \frac{1}{3} \Delta z_i \left(A_i + A_{i+1} + \sqrt{A_i \cdot A_{i+1}}\right)$$

Where $A_i$ is the surface area at contour elevation $z_i$, and $\Delta z_i = z_{i+1} - z_i$.

### 2.4 Dual-Polarization SAR Water Masking (Twele et al. 2016; Bioresita et al. 2018)
In Sentinel-1 C-SAR products, water exhibits low backscatter in both VV and VH channels. Because cross-polarization (VH) is less sensitive to wind-induced surface roughness than co-polarization (VV), a combined dual-polarization condition is evaluated:

$$\sigma^0_{\text{VV}} < -16.0\text{ dB} \quad \text{OR} \quad \sigma^0_{\text{VH}} < -24.0\text{ dB}$$

$$\text{WaterMask}(x, y) = \left[\sigma^0_{\text{VV}}(x, y) < T_{\text{water}}\right] \land \left[\text{Slope}(x, y) < 5.0^\circ\right]$$

Where the terrain slope constraint ($\text{Slope} < 5^\circ$) eliminates false detections caused by radar shadows on steep mountain slopes.

---

## 3. Sensor Configurations & Spatial Resolutions

| Mission & Sensor | Temporal Record | Spatial Resolution | Cloud Penetration | Primary Hydrological Function |
|------------------|-----------------|--------------------|-------------------|--------------------------------|
| **Landsat 5/7/8/9 (TM/ETM+/OLI)** | 1984 – Present ($40+$ years) | 30 m | No (Optical) | Multi-decadal baseline recurrence, historical drought analysis |
| **Copernicus Sentinel-2A/B (MSI)** | 2015 – Present | 10 m (Green) / 20 m (SWIR) | No (Optical) | High-resolution reservoir margin delineation, littoral wetland vegetation |
| **Copernicus Sentinel-1A/C (C-SAR)** | 2014 – Present | 10 m (IW GRD pixel spacing) | **Yes (All-Weather, Day/Night)** | Cloud-penetrating emergency flood tracking, monsoon season reservoir refill |
| **Copernicus DEM GLO-30** | Baseline 2011–2015 | 30 m | N/A | Bathymetric hypsometry, terrain shadow masking |

---

## 4. Algorithmic Implementation in `eo-mcp`

The reservoir drought and SAR water engines are implemented in `src/eo_mcp/core/drought.py` and `src/eo_mcp/core/sar.py`, exposed via `@eo_tool` functions `analyze_reservoir_drought` and `detect_water_sar`.

### 4.1 Surface Water Contraction & Desiccation Analysis
```python
# src/eo_mcp/core/drought.py

def analyze_water_body_drought(
    bbox: List[float],
    historical_year: int = 2018,
    recent_year: int = 2024,
    pixel_size_m: float = 30.0
) -> Dict[str, Any]:
    """Quantify multi-temporal reservoir surface water contraction.
    
    Extracts baseline vs. recent water masks, computes transition metrics
    (permanent, lost, new water), and assigns drought severity status.
    """
    ...
```

### 4.2 Sentinel-1 SAR Water Detection
```python
# src/eo_mcp/core/sar.py

def detect_water_mask(sar_db: np.ndarray, threshold_db: float = -16.0) -> Tuple[np.ndarray, float]:
    """Detect open water surfaces using calibrated SAR decibel thresholding.
    
    Water exhibits low backscatter due to microwave specular reflection.
    Returns boolean water mask and coverage percentage.
    """
    valid_mask = ~np.isnan(sar_db)
    water = (sar_db < threshold_db) & valid_mask
    water_pct = (np.sum(water) / np.sum(valid_mask)) * 100.0 if np.sum(valid_mask) > 0 else 0.0
    return water, float(water_pct)
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Wind-Induced Surface Roughening in SAR
Strong winds ($> 8\text{--}10\text{ m/s}$) over large open reservoirs generate surface gravity waves. These waves trigger Bragg resonance scattering, elevating radar backscatter from $-20\text{ dB}$ up to $-12\text{ dB}$, which can cause water omission in simple thresholding.
- **Mitigation in `eo-mcp`:** The algorithm checks dual-polarization ($\text{VH}$) data, which is less sensitive to wind roughening, and supports adaptive regional threshold adjustment.

### 5.2 Radar Terrain Shadow Look-Alikes
Steep mountain terrain facing away from the radar antenna receives no microwave illumination (radar shadow). Radar shadows yield zero returned energy ($\sigma^0 < -25\text{ dB}$), appearing identical to calm water.
- **Mitigation in `eo-mcp`:** Terrain slope and aspect derived from Copernicus DEM GLO-30 mask out terrain cells with slope $\ge 5^\circ$ before evaluating water masks.

### 5.3 Dense Aquatic Vegetation & Algal Blooms
Dense floating macrophytes (e.g., water hyacinth, *Eichhornia crassipes*) or intense phytoplankton blooms create a vegetative canopy over the water surface, elevating NIR reflectance and depressing MNDWI.
- **Mitigation in `eo-mcp`:** Optical MNDWI is coupled with multi-temporal water occurrence history, recognizing vegetated reservoir margins as water-covered when historic recurrence remains high.

---

## 6. Peer-Reviewed References

- **Pekel, J.-F., Cottam, A., Gorelick, N., & Belward, A. S. (2016).** High-resolution mapping of global surface water and its long-term changes. *Nature*, 540(7633), 418–422. [DOI: 10.1038/nature20584](https://doi.org/10.1038/nature20584)
- **Twele, A., Cao, W., Plank, S., & Martinis, S. (2016).** Sentinel-1-based flood mapping: A fully automated processing chain. *International Journal of Remote Sensing*, 37(13), 2990–3004. [DOI: 10.1080/01431161.2016.1192304](https://doi.org/10.1080/01431161.2016.1192304)
- **Bioresita, F., Puissant, A., Stumpf, A., & Malet, J.-P. (2018).** A method for automatic and rapid mapping of water surfaces from Sentinel-1 imagery. *Remote Sensing*, 10(2), 217. [DOI: 10.3390/rs10020217](https://doi.org/10.3390/rs10020217)
