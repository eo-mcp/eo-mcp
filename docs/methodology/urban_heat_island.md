# Urban Heat Island, Thermal Inversion & Land Surface Temperature

## Executive & Scientific Summary

Urbanization replaces natural vegetated landscapes with impervious surfaces such as asphalt roads, concrete pavements, and brick/metal buildings. These materials possess low solar albedo, high thermal admittance, and reduced evapotranspiration, creating the **Urban Heat Island (UHI)** effect: urban areas experience significantly elevated surface and air temperatures compared to surrounding rural baselines. Under the EU Urban Agenda and World Health Organization (WHO) Heat Health Action Plans, mapping urban thermal hotspots is critical to safeguarding vulnerable urban populations and guiding climate-adaptive urban greening.

The `eo-mcp` thermal intelligence engine (`analyze_urban_heat_island`) implements a single-channel radiative transfer inversion model based on:
1. **Planck Function Inversion**: Converting top-of-atmosphere (TOA) thermal infrared spectral radiances into brightness temperature ($T_B$) using sensor-specific calibration constants.
2. **Fractional Vegetation Cover (FVC / $P_v$) Estimation**: Deriving sub-pixel vegetative canopy fractions from NDVI dynamics (Valor & Caselles 1996).
3. **NDVI-Threshold Land Surface Emissivity Retrieval**: Determining high-resolution surface emissivity ($\varepsilon$) across water, bare soil, mixed impervious surfaces, and dense vegetation (Sobrino et al. 2004; 2008).
4. **Single-Channel Land Surface Temperature (LST) Inversion**: Correcting for surface emissivity and atmospheric transmission to compute absolute kinetic surface temperature ($T_s$) in Celsius (Jiménez-Muñoz et al. 2009).
5. **Urban Thermal Anomaly & UHI Intensity Mapping**: Quantifying spatial thermal disparities between densely built urban cores and rural surrounding baselines.

---

## 1. Physical & Radiative Transfer Principles

### 1.1 The Thermal Infrared Radiative Transfer Equation
In the thermal infrared atmospheric window ($10.0\text{--}12.5\ \mu\text{m}$), spaceborne radiometers record spectral radiance $L_\lambda$ governed by the radiative transfer equation for a non-scattering, cloud-free atmosphere:

$$L_\lambda = \left[\varepsilon_\lambda B_\lambda(T_s) + (1 - \varepsilon_\lambda) L_\lambda^\downarrow\right] \tau_\lambda + L_\lambda^\uparrow$$

Where:
- $\varepsilon_\lambda$ is the directional spectral emissivity of the terrestrial surface.
- $B_\lambda(T_s)$ is the blackbody spectral radiance emitted at surface kinetic temperature $T_s$.
- $\tau_\lambda$ is the atmospheric transmittance.
- $L_\lambda^\downarrow$ is the downwelling atmospheric thermal radiance.
- $L_\lambda^\uparrow$ is the upwelling atmospheric path thermal radiance.

```
+-------------------------------------------------------------------+
|                        TIRS SENSOR AT TOA                         |
+-------------------------------------------------------------------+
                                  ^
                                  |  Total Radiance L_lambda
+---------------------------------+---------------------------------+
|                       ATMOSPHERE (tau_lambda)                     |
|                                                                   |
|   Upwelling Path Radiance (L_up) ^        | Downwelling Radiance  |
|                                  |        | (L_down)              |
|                                  |        v                       |
+----------------------------------+--------------------------------+
|                         EARTH SURFACE                             |
|                                                                   |
|   Surface Emitted:  eps * B(T_s) ^        ^ Reflected Downwelling:|
|                                  |        | (1 - eps) * L_down    |
+----------------------------------+--------+-----------------------+
```

### 1.2 Surface Energy Balance in Urban Environments
The surface temperature $T_s$ of an urban pixel is determined by the net surface energy balance:

$$R_n = H + \lambda E + G + \Delta Q_A$$

Where:
- $R_n = (1 - \alpha) S^\downarrow + L^\downarrow - L^\uparrow$ is net radiation.
- $H$ is the turbulent sensible heat flux to the atmosphere.
- $\lambda E$ is latent heat flux (evapotranspiration from vegetation and open water).
- $G$ is ground conduction heat storage.
- $\Delta Q_A$ is anthropogenic waste heat flux (air conditioning exhaust, vehicle engines, industrial processes).

In heavily built urban centers, latent heat flux $\lambda E$ drops near zero due to the absence of transpiring vegetation and permeable soils. Excess solar energy is partitioned into sensible heat $H$ and thermal storage $G$, driving urban surface temperatures $5^\circ\text{C}\text{--}12^\circ\text{C}$ above vegetated rural baselines.

---

## 2. Exact Mathematical Formulations

### 2.1 Top-of-Atmosphere Radiance to Brightness Temperature ($T_B$)
Raw digital numbers from Landsat 8/9 Thermal Infrared Sensor (TIRS Band 10) are converted to spectral radiance $L_\lambda$ and inverted via the Planck function:

$$L_\lambda = M_L \cdot \text{DN} + A_L$$

$$T_B = \frac{K_2}{\ln\left(\frac{K_1}{L_\lambda} + 1\right)}$$

Where calibration constants for Landsat 8/9 TIRS Band 10 ($\lambda = 10.895\ \mu\text{m}$) are:
- $M_L = 0.0003342\ \text{W}/(\text{m}^2\cdot\text{sr}\cdot\mu\text{m})/\text{DN}$
- $A_L = 0.1\ \text{W}/(\text{m}^2\cdot\text{sr}\cdot\mu\text{m})$
- $K_1 = 774.8853\ \text{W}/(\text{m}^2\cdot\text{sr}\cdot\mu\text{m})$
- $K_2 = 1321.0789\ \text{K}$

### 2.2 Fractional Vegetation Cover ($P_v$ / FVC - Valor & Caselles 1996)
Sub-pixel vegetation abundance controls the mixture of soil, vegetation, and man-made structures:

$$P_v = \left(\frac{\text{NDVI} - \text{NDVI}_{\text{soil}}}{\text{NDVI}_{\text{veg}} - \text{NDVI}_{\text{soil}}}\right)^2$$

Where standard empirical endmembers are:
- $\text{NDVI}_{\text{soil}} = 0.20$ (bare soil and impervious surfaces).
- $\text{NDVI}_{\text{veg}} = 0.50$ (fully vegetated, closed-canopy endmember).
- Clamped strictly: $P_v = 0.0$ when $\text{NDVI} \le 0.20$; $P_v = 1.0$ when $\text{NDVI} \ge 0.50$.

### 2.3 Surface Emissivity Retrieval ($\varepsilon$ - Sobrino et al. 2004; 2008)
Surface emissivity is estimated using the NDVI-threshold method:

$$\varepsilon = \begin{cases}
0.995 & \text{if } \text{NDVI} < 0.0 \quad (\text{Open Water}) \\
0.960 & \text{if } 0.0 \le \text{NDVI} < 0.20 \quad (\text{Bare Soil / Asphalt / Concrete}) \\
0.970 + 0.018 \cdot P_v & \text{if } 0.20 \le \text{NDVI} \le 0.50 \quad (\text{Mixed Urban-Vegetation}) \\
0.985 & \text{if } \text{NDVI} > 0.50 \quad (\text{Dense Vegetative Canopy})
\end{cases}$$

### 2.4 Single-Channel Land Surface Temperature ($T_s$ - Jiménez-Muñoz et al. 2009)
The kinetic Land Surface Temperature ($T_s$ in Kelvin) is retrieved by correcting brightness temperature $T_B$ for surface emissivity $\varepsilon$:

$$T_s = \frac{T_B}{1 + \left(\frac{\lambda \cdot T_B}{\rho}\right) \ln \varepsilon}$$

Where:
- $\lambda = 10.895\ \mu\text{m}$ (central effective wavelength of TIRS Band 10).
- $\rho = \frac{h \cdot c}{k_B} = 1.438 \times 10^{-2}\ \text{m}\cdot\text{K} = 14380\ \mu\text{m}\cdot\text{K}$.

Conversion to Celsius:

$$T_s\ [^\circ\text{C}] = T_s\ [\text{K}] - 273.15$$

### 2.5 Urban Heat Island Intensity ($\text{UHI}$)
To quantify the thermal elevation of the urban core relative to surrounding rural zones:

$$\text{UHI} = \bar{T}_{s, \text{urban}} - \bar{T}_{s, \text{rural}}$$

Where rural baseline pixels are identified by high vegetative fraction ($P_v > 0.60$ or $\text{NDVI} > 0.50$), and urban pixels correspond to built-up impervious surfaces ($P_v < 0.20$ or $\text{NDVI} < 0.20$).

---

## 3. Sensor Band Configurations & Spatial Resolutions

| Satellite Sensor | Band ID | Spectral Range ($\mu$m) | Native Spatial Resolution | Resampled Product Resolution | Primary Analytical Role |
|------------------|---------|-------------------------|---------------------------|------------------------------|-------------------------|
| **Landsat 8/9 TIRS** | Band 10 | $10.60\text{--}11.19\ \mu\text{m}$ | 100 m | 30 m | Thermal infrared radiance, brightness temperature $T_B$ |
| **Landsat 8/9 TIRS** | Band 11 | $11.50\text{--}12.51\ \mu\text{m}$ | 100 m | 30 m | Secondary thermal channel (susceptible to stray light) |
| **Landsat 8/9 OLI** | Band 4 (Red) | $0.64\text{--}0.67\ \mu\text{m}$ | 30 m | 30 m | Chlorophyll absorption for FVC calculation |
| **Landsat 8/9 OLI** | Band 5 (NIR) | $0.85\text{--}0.88\ \mu\text{m}$ | 30 m | 30 m | Mesophyll scattering for FVC calculation |
| **Sentinel-2 MSI** | Band 4 / 8 | $0.665\ \mu\text{m}$ / $0.842\ \mu\text{m}$ | 10 m | 10 m | High-resolution cross-sensor NDVI sharpening |

---

## 4. Algorithmic Implementation in `eo-mcp`

The thermal analysis engine is implemented in `src/eo_mcp/core/thermal.py` and exposed via `@eo_tool` `analyze_urban_heat_island` in `src/eo_mcp/server.py`.

### 4.1 LST Radiative Transfer Inversion
```python
# src/eo_mcp/core/thermal.py

def calculate_land_surface_temperature(
    thermal_band: np.ndarray,
    red_band: np.ndarray,
    nir_band: np.ndarray,
    pixel_size_m: float = 30.0,
    wavelength_um: float = 10.895
) -> Dict[str, Any]:
    """Calculate Land Surface Temperature (LST) and Urban Heat Island metrics.
    
    Inverts Planck equation to brightness temperature, computes FVC from NDVI,
    estimates Sobrino emissivity, and returns mean/min/max LST in Celsius.
    """
    # 1. Compute NDVI and FVC
    ndvi = compute_ndvi(nir_band, red_band)
    pv = np.clip(((ndvi - 0.2) / (0.5 - 0.2)) ** 2, 0.0, 1.0)
    
    # 2. Piecewise emissivity estimation
    emissivity = np.where(ndvi < 0.0, 0.995,
                 np.where(ndvi < 0.2, 0.960,
                 np.where(ndvi <= 0.5, 0.970 + 0.018 * pv, 0.985)))
                 
    # 3. Invert to kinetic surface temperature (Celsius)
    rho = 14380.0  # um * K
    lst_k = tb_k / (1.0 + (wavelength_um * tb_k / rho) * np.log(emissivity))
    lst_c = lst_k - 273.15
    ...
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Landsat 8 TIRS Band 11 Stray Light Effect
Landsat 8 TIRS suffers from out-of-field stray light artifacting, particularly in Band 11, where thermal radiation from outside the sensor's instant field of view scatters onto the focal plane.
- **Mitigation in `eo-mcp`:** `eo-mcp` exclusively utilizes **Band 10** for single-channel LST inversion, as USGS calibration teams demonstrated that Band 10 stray light calibration error is $< 0.5\text{ K}$ after stray-light correction, whereas split-window algorithms utilizing Band 11 exhibit greater residual uncertainty.

### 5.2 Skin Temperature ($T_s$) vs. 2-Meter Air Temperature ($T_{\text{air}}$)
Satellite radiometers measure the radiative **surface skin temperature** ($T_s$) of rooftops, pavements, and tree canopies. This can differ substantially from the $2\text{-meter}$ ambient canopy layer air temperature ($T_{\text{air}}$) measured by weather stations:
- On sunny summer afternoons, dark asphalt skin temperature can reach $55^\circ\text{C}\text{--}60^\circ\text{C}$ while air temperature is $35^\circ\text{C}$.
- **Mitigation in `eo-mcp`:** Output metrics clearly label results as Surface Urban Heat Island (SUHI / $T_s$) rather than canopy air temperature.

### 5.3 Building Geometry & Microclimate Shadows
In dense urban canyons, high-rise buildings cast deep geometric shadows. Shaded street pavements remain much cooler than sunlit rooftops, introducing sharp sub-pixel thermal gradients.
- **Mitigation in `eo-mcp`:** High-resolution spatial aggregation and percentile metrics ($p_{10}, p_{50}, p_{90}$) provide robust characterization of canyon thermal microclimates.

---

## 6. Peer-Reviewed References

- **Valor, E., & Caselles, V. (1996).** Mapping land surface emissivity from NDVI: Application to European, African, and South American areas. *Remote Sensing of Environment*, 57(3), 167–184. [DOI: 10.1016/0034-4257(96)00039-9](https://doi.org/10.1016/0034-4257(96)00039-9)
- **Sobrino, J. A., Jiménez-Muñoz, J. C., & Paolini, L. (2004).** Land surface temperature retrieval from LANDSAT TM 5. *Remote Sensing of Environment*, 90(4), 434–440. [DOI: 10.1016/j.rse.2004.02.003](https://doi.org/10.1016/j.rse.2004.02.003)
- **Sobrino, J. A., Jiménez-Muñoz, J. C., Sòria, G., Romaguera, M., Guanter, L., Moreno, J., Plaza, A., & Martínez, P. (2008).** Land surface emissivity retrieval from different VNIR and TIR sensors. *IEEE Transactions on Geoscience and Remote Sensing*, 46(2), 316–327. [DOI: 10.1109/TGRS.2007.904834](https://doi.org/10.1109/TGRS.2007.904834)
- **Jiménez-Muñoz, J. C., Cristóbal, J., Sobrino, J. A., Sòria, G., Ninyerola, M., & Pons, X. (2009).** Revision of the single-channel algorithm for land surface temperature retrieval from Landsat thermal-infrared data. *IEEE Transactions on Geoscience and Remote Sensing*, 47(1), 339–349. [DOI: 10.1109/TGRS.2008.2007125](https://doi.org/10.1109/TGRS.2008.2007125)
