# Coastal Dynamics, Shoreline Extraction & Erosion Metrics

## Executive & Scientific Summary

Coastal zones represent some of the most dynamic, economically vital, and climate-vulnerable environments on Earth. Monitoring decadal shoreline retreat, beach erosion, and coastal accretion is essential for spatial planning, coastal defense infrastructure, and compliance with the EU Integrated Coastal Zone Management (ICZM) recommendation and the EU Climate Adaptation Strategy.

The `eo-mcp` coastal dynamics engine (`analyze_coastal_erosion`) automates satellite-derived shoreline extraction and quantitative erosion rate computation based on:
1. **Modified Normalized Difference Water Index (MNDWI)**: Sharp land-water boundary contrast using Green and SWIR spectral bands (Xu 2006).
2. **Otsu Non-Parametric Histogram Thresholding**: Unsupervised, adaptive between-class variance maximization for bimodal image segmentation (Otsu 1979).
3. **Sub-Pixel Boundary Extraction**: Morphological gradient operations tracing instantaneous waterlines (Vos et al. 2019, CoastSat).
4. **Digital Shoreline Analysis System (DSAS) Transects**: Perpendicular transects cast from an offshore or onshore baseline, calculating Net Shoreline Movement (NSM) and End Point Rate (EPR) in meters per year (Thieler et al. 2009; Himmelstoss et al. 2018).

---

## 1. Physical & Radiative Transfer Principles

### 1.1 The Optical Land-Water Boundary
The boundary between water and land produces one of the most prominent discontinuities in optical remote sensing. 
- In the visible green band ($\sim 560\text{ nm}$), clear coastal waters reflect $5\%\text{--}10\%$ of incident radiation, while beach sand reflects $20\%\text{--}40\%$.
- In the shortwave infrared band ($\sim 1610\text{ nm}$), liquid water absorbs virtually all incident photons ($\rho_{\text{SWIR}} \approx 0.00\text{--}0.01$), whereas quartz sand, coastal dunes, and urban infrastructure reflect brightly ($\rho_{\text{SWIR}} \ge 0.30$).

Computing the normalized ratio between green and SWIR (MNDWI) yields an intensely bimodal histogram: water pixels exhibit high positive values ($\text{MNDWI} \ge +0.20$), while land pixels exhibit strongly negative values ($\text{MNDWI} \le -0.20$).

```
Histogram Frequency
    ^
    |          Land Class                       Water Class
    |         (Dry Beach/Soil)                 (Coastal Ocean)
    |             /\                                /\
    |            /  \                              /  \
    |           /    \      Optimal Threshold     /    \
    |          /      \           t*             /      \
    |         /        \          |             /        \
    +--------/----------\---------|------------/----------\----> MNDWI
           -0.8        -0.4      0.0         +0.4       +0.8
```

### 1.2 Wave Runup & Hydrodynamic Tidal Fluctuations
The instantaneous waterline recorded by a satellite sensor is a function of both morphological beach elevation and hydrodynamic conditions:
- **Tidal Elevation ($z_{\text{tide}}$):** On shallow-sloping sandy beaches (beach slope $\beta \approx 0.02\text{--}0.05$), a 1-meter vertical tidal excursion shifts the horizontal waterline seaward or landward by:
  $$\Delta x_{\text{tide}} = \frac{\Delta z_{\text{tide}}}{\tan \beta} \approx 20\text{--}50\text{ meters}$$
- **Wave Runup ($R_{2\%}$):** Dynamic setup and swash excursion driven by breaking ocean swell.

Consequently, multidecadal erosion trend assessment requires comparing satellite observations across consistent tidal stages or averaging multiple seasonal acquisitions to eliminate high-frequency oceanographic noise.

---

## 2. Exact Mathematical Formulations

### 2.1 Modified Normalized Difference Water Index (MNDWI)
Formulated by Xu (2006):

$$\text{MNDWI} = \frac{\rho_{\text{Green}} - \rho_{\text{SWIR1}}}{\rho_{\text{Green}} + \rho_{\text{SWIR1}} + \epsilon}$$

Where $\epsilon = 10^{-6}$ prevents zero-division errors over deep shadow or null data.

### 2.2 Otsu Bimodal Variance Maximization (1979)
Let the pixel values of the MNDWI array be represented in $L$ gray levels $\{1, 2, \dots, L\}$. The normalized histogram probability distribution is $p_i = n_i / N$, where $\sum_{i=1}^L p_i = 1$.

Partitioning the histogram into two classes $C_0$ (land: pixels $\le t$) and $C_1$ (water: pixels $> t$):
- **Class Probabilities:**
  $$\omega_0(t) = \sum_{i=1}^t p_i, \quad \omega_1(t) = \sum_{i=t+1}^L p_i = 1 - \omega_0(t)$$
- **Class Means:**
  $$\mu_0(t) = \sum_{i=1}^t \frac{i \cdot p_i}{\omega_0(t)}, \quad \mu_1(t) = \sum_{i=t+1}^L \frac{i \cdot p_i}{\omega_1(t)}$$
- **Total Mean:**
  $$\mu_T = \omega_0(t) \mu_0(t) + \omega_1(t) \mu_1(t)$$
- **Between-Class Variance ($\sigma_B^2$):**
  $$\sigma_B^2(t) = \omega_0(t) \omega_1(t) \left[\mu_0(t) - \mu_1(t)\right]^2$$

The optimal waterline segmentation threshold $t^*$ maximizes $\sigma_B^2(t)$:

$$t^* = \arg\max_{1 \le t < L} \sigma_B^2(t)$$

The binary surface water mask $W(x, y)$ is:

$$W(x, y) = \begin{cases} 1 & \text{if } \text{MNDWI}(x, y) \ge t^* \\ 0 & \text{if } \text{MNDWI}(x, y) < t^* \end{cases}$$

### 2.3 Morphological Shoreline Boundary Delineation
The vector shoreline is extracted as the one-pixel boundary of the binary water mask:

$$\partial W = W \setminus \text{erode}(W, K)$$

Where $K$ is a $3 \times 3$ structuring element, and $\setminus$ represents the set difference operator.

### 2.4 DSAS Shoreline Change Metrics (Thieler et al. 2009; Himmelstoss et al. 2018)
A reference baseline is established parallel to the general coastal trend (either onshore or offshore). Perpendicular transects $\mathcal{T}_i$ are cast at uniform alongshore intervals $\Delta y = 50\text{--}100\text{ m}$.

For each transect $i$:
1. **Net Shoreline Movement (NSM):** The total distance in meters between the historical baseline intersection $x_{\text{hist}}$ (acquired at year $t_{\text{hist}}$) and the modern shoreline intersection $x_{\text{recent}}$ (acquired at year $t_{\text{recent}}$):

$$\text{NSM}_i = \left(x_{\text{baseline}} - x_{\text{recent}, i}\right) \cdot \Delta s - \left(x_{\text{baseline}} - x_{\text{hist}, i}\right) \cdot \Delta s$$

Where $\Delta s$ is the ground pixel resolution. By sign convention:
- $\text{NSM} < 0$: Landward retreat (Erosion).
- $\text{NSM} > 0$: Seaward advance (Accretion).

2. **End Point Rate (EPR):** Shoreline displacement normalized by elapsed elapsed time $\Delta t = t_{\text{recent}} - t_{\text{hist}}$:

$$\text{EPR}_i = \frac{\text{NSM}_i}{\Delta t}\quad [\text{m/year}]$$

3. **Hazard Categorization in `eo-mcp`:**
   - **`CRITICAL_EROSION`:** $\text{EPR} < -2.0\text{ m/year}$
   - **`MODERATE_EROSION`:** $-2.0 \le \text{EPR} < -0.5\text{ m/year}$
   - **`STABLE`:** $-0.5 \le \text{EPR} \le +0.5\text{ m/year}$
   - **`ACCRETION`:** $\text{EPR} > +0.5\text{ m/year}$

---

## 3. Sensor Band Configurations & Spatial Resolutions

| Parameter | Copernicus Sentinel-2 MSI | USGS/NASA Landsat 8/9 OLI |
|-----------|---------------------------|---------------------------|
| **Green Band** | Band 3 ($560\text{ nm}$, $10\text{ m}$) | Band 3 ($561\text{ nm}$, $30\text{ m}$) |
| **SWIR1 Band** | Band 11 ($1610\text{ nm}$, $20\text{ m}$) | Band 6 ($1609\text{ nm}$, $30\text{ m}$) |
| **Panchromatic Band** | None (10m native visible) | Band 8 ($590\text{ nm}$, $15\text{ m}$ pan-sharpening) |
| **Resampling Strategy** | Band 11 bilinearly aligned to 10m grid | Native 30m grid |
| **Sub-Pixel Precision** | $\pm 5.0\text{--}7.5\text{ m}$ with Otsu thresholding | $\pm 10.0\text{--}15.0\text{ m}$ |

---

## 4. Algorithmic Implementation in `eo-mcp`

The coastal analytics engine resides in `src/eo_mcp/core/coastal.py` and is invoked through `@eo_tool` `analyze_coastal_erosion` in `src/eo_mcp/server.py`.

### 4.1 Otsu Water Segmentation
```python
# src/eo_mcp/core/coastal.py

def extract_water_mask_otsu(mndwi: np.ndarray) -> Tuple[np.ndarray, float]:
    """Segment water using Otsu bimodal variance maximization.
    
    Returns:
        Tuple of (boolean water mask, calculated optimal float threshold).
    """
    valid = mndwi[~np.isnan(mndwi)]
    if len(valid) == 0:
        return np.zeros_like(mndwi, dtype=bool), 0.0
    
    # Compute 256-bin histogram between valid min and max
    # Maximizes between-class variance sigma_B^2
    ...
```

### 4.2 Transect Shoreline Erosion Metrics
```python
# src/eo_mcp/core/coastal.py

def compute_transect_erosion_rates(
    hist_water: np.ndarray,
    recent_water: np.ndarray,
    delta_years: float,
    pixel_size_m: float = 10.0,
    num_transects: int = 20
) -> Dict[str, Any]:
    """Compute alongshore perpendicular transects using DSAS principles.
    
    Calculates Net Shoreline Movement (NSM) and End Point Rate (EPR)
    across regularly spaced coastal profiles.
    """
    ...
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Breaking Wave Whitecaps & Swash Foam
Breaking surf zones and whitecaps contain entrained air bubbles that scatter solar radiation across all wavelengths, producing high reflectance in both green and SWIR. This can suppress MNDWI values over the immediate surf zone, causing the algorithm to classify whitecaps as land.
- **Mitigation in `eo-mcp`:** Morphological closing filters join discontinuous water segments along the outer surf line, and multitemporal composite filtering averages out short-period wave swash.

### 5.2 Astronomical Tidal Offsets
Comparing a satellite image captured at low astronomical tide with one captured at high astronomical tide introduces apparent horizontal displacement that reflects water level rather than sediment loss.
- **Mitigation in `eo-mcp`:** When analyzing decadal coastal erosion over multi-year intervals ($\Delta t \ge 5\text{--}10\text{ years}$), long-term sediment loss signals typically exceed the magnitude of tidal excursions, and multi-year seasonal averaging dampens tidal phase bias.

### 5.3 Steep Rocky Cliffs vs. Dissipative Sandy Beaches
On vertical rocky cliffs (e.g., chalk or basalt headlands), shoreline change is episodic (catastrophic rockfall) with negligible horizontal excursion between events. On flat, dissipative sandy barrier islands, shorelines fluctuate dynamically in response to storm seasons.
- **Mitigation in `eo-mcp`:** Transect statistical summaries include standard deviation and minimum/maximum retreat values to differentiate uniform beach migration from localized cliff collapse.

---

## 6. Peer-Reviewed References

- **Thieler, E. R., Himmelstoss, E. A., Zichichi, J. L., & Ergul, A. (2009).** Digital Shoreline Analysis System (DSAS) version 4.0—An ArcGIS extension for calculating shoreline change. *U.S. Geological Survey Open-File Report 2008-1278*, 72 p. [DOI: 10.3133/ofr20081278](https://doi.org/10.3133/ofr20081278)
- **Himmelstoss, E. A., Henderson, R. E., Kratzmann, M. G., & Farris, A. S. (2018).** Digital Shoreline Analysis System (DSAS) version 5.0 user guide. *U.S. Geological Survey Open-File Report 2018-1179*, 110 p. [DOI: 10.3133/ofr20181179](https://doi.org/10.3133/ofr20181179)
- **Vos, K., Splinter, K. D., Harley, M. D., Simmons, J. A., & Turner, I. L. (2019).** CoastSat: A Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. *Environmental Modelling & Software*, 122, 104528. [DOI: 10.1016/j.envsoft.2019.104528](https://doi.org/10.1016/j.envsoft.2019.104528)
- **Otsu, N. (1979).** A threshold selection method from gray-level histograms. *IEEE Transactions on Systems, Man, and Cybernetics*, 9(1), 62–66. [DOI: 10.1109/TSMC.1979.4310076](https://doi.org/10.1109/TSMC.1979.4310076)
- **Xu, H. (2006).** Modification of normalised difference water index (NDWI) to enhance open water features in remotely sensed imagery. *International Journal of Remote Sensing*, 27(14), 3025–3033. [DOI: 10.1080/01431160600589179](https://doi.org/10.1080/01431160600589179)
