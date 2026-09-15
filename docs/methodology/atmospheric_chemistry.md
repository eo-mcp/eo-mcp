# Atmospheric Chemistry, Tropospheric Emissions & Air Quality

## Executive & Scientific Summary

Anthropogenic emissions of nitrogen dioxide ($\text{NO}_2$), carbon monoxide ($\text{CO}$), methane ($\text{CH}_4$), and sulfur dioxide ($\text{SO}_2$) are primary drivers of urban smog, acid deposition, respiratory illness, and radiative forcing. Under the EU Ambient Air Quality Directive (2008/50/EC) and the newly enacted EU Methane Regulation (2024/1787), high-frequency spaceborne surveillance of trace gas concentrations is required to verify industrial compliance and monitor transboundary pollution transport.

The `eo-mcp` atmospheric intelligence suite (`monitor_atmospheric_emissions`) integrates spaceborne spectrometer measurements from the European Space Agency's Copernicus Sentinel-5 Precursor (S5P) TROPOspheric Monitoring Instrument (TROPOMI) with ground-truth validation from OpenAQ monitoring networks, based on:
1. **Differential Optical Absorption Spectroscopy (DOAS)**: High-resolution spectral fitting isolating narrow molecular absorption bands from broadband atmospheric scattering (Veefkind et al. 2012).
2. **Tropospheric-Stratospheric Column Separation**: Data assimilation techniques removing high-altitude stratospheric background columns to isolate boundary layer pollution (van Geffen et al. 2020).
3. **Radiative Transfer Air Mass Factor (AMF) Conversions**: Converting slant column densities to vertical column densities using local albedo, terrain elevation, and chemistry-transport profile look-up tables.
4. **European Air Quality Index (AQI) Benchmarking**: Quantitative stratification into Clean, Moderate, Poor, and Hazardous air quality tiers.

---

## 1. Physical & Radiative Transfer Principles

### 1.1 The Beer-Lambert-Bouguer Law & DOAS Inversion
As solar radiation enters Earth's atmosphere, reflects from the surface, and travels to the spaceborne sensor, it undergoes absorption by atmospheric gases and extinction by Rayleigh (molecular) and Mie (aerosol and cloud) scattering.

The transmission of radiation through the atmosphere is governed by the Beer-Lambert law:

$$I(\lambda) = I_0(\lambda) \exp\left(-\sum_i \sigma_i(\lambda) \int \rho_i(s) ds - \tau_{\text{scat}}(\lambda)\right)$$

Where:
- $I(\lambda)$ is the observed Top-of-Atmosphere backscattered radiance.
- $I_0(\lambda)$ is the extraterrestrial solar irradiance measured by TROPOMI's daily solar calibration port.
- $\sigma_i(\lambda)$ is the absorption cross-section of gas molecule $i$ ($\text{m}^2/\text{molecule}$).
- $\rho_i(s)$ is the number density along light path $s$.
- $\tau_{\text{scat}}(\lambda)$ is the optical thickness from Rayleigh and aerosol scattering.

Differential Optical Absorption Spectroscopy (DOAS) separates the extinction cross-section into a slowly varying broadband component $\sigma_{i,0}(\lambda)$ (representing Rayleigh/Mie scattering and surface albedo) and a rapidly varying narrow-band differential component $\sigma_i'(\lambda)$ (representing quantum electronic/vibrational transitions):

$$\sigma_i(\lambda) = \sigma_{i,0}(\lambda) + \sigma_i'(\lambda)$$

Taking the natural logarithm of the ratio between solar irradiance and backscattered radiance removes broadband effects via low-order polynomial subtraction $P(\lambda)$:

$$\tau_{\text{diff}}(\lambda) = \ln\left(\frac{I_0(\lambda)}{I(\lambda)}\right) - P(\lambda) = \sum_i \sigma_i'(\lambda) \cdot N_{s, i}$$

Where $N_{s, i} = \int \rho_i(s) ds$ is the **Slant Column Density** ($\text{molecules}/\text{cm}^2$ or $\text{mol}/\text{m}^2$) along the effective photon path.

```
       Sun
         \
          \  Incident Solar Beam
           \
            V
   ============================= Top of Atmosphere (TOA)
             \
              \  Stratospheric Absorption
               \
   ----------------------------- Tropopause (~10-15 km)
                 \
                  \  Tropospheric Pollution Layer
                   \  (NO2, CO, SO2, CH4)
                    \
   ~~~~~~~~~~~~~~~~~~V~~~~~~~~~~ Earth Surface (Albedo A_s)
                      \
                       \  Reflected & Multi-Scattered Photons
                        \
                         ^
                          \
                           \  TROPOMI Sensor
                            \
```

---

## 2. Exact Mathematical Formulations

### 2.1 Tropospheric-Stratospheric Separation (van Geffen et al. 2020)
For nitrogen dioxide ($\text{NO}_2$), a substantial reservoir resides in the stratosphere ($15\text{--}35\text{ km}$). The total slant column density $N_s$ is a linear combination of stratospheric and tropospheric components:

$$N_s = N_{s, \text{strat}} + N_{s, \text{trop}} = N_{v, \text{strat}} \cdot M_{\text{strat}} + N_{v, \text{trop}} \cdot M_{\text{trop}}$$

Where:
- $N_{v, \text{strat}}$ is the stratospheric vertical column density, estimated over clean remote maritime sectors using the TM5-MP global chemistry transport model data assimilation.
- $M_{\text{strat}}$ and $M_{\text{trop}}$ are the stratospheric and tropospheric **Air Mass Factors (AMF)**.

The target **Vertical Tropospheric Column Density** ($N_{v, \text{trop}}$) is derived as:

$$N_{v, \text{trop}} = \frac{N_s - N_{v, \text{strat}} \cdot M_{\text{strat}}}{M_{\text{trop}}}$$

### 2.2 Tropospheric Air Mass Factor Formulation
The tropospheric Air Mass Factor ($M_{\text{trop}}$) accounts for the optical geometry, terrain height, surface albedo, and vertical profile of the trace gas:

$$M_{\text{trop}} = M_{\text{geom}} \int_0^{z_{\text{trop}}} m(z, A_s, p_s) \cdot S(z) dz$$

Where:
- $M_{\text{geom}} = \frac{1}{\cos \theta_0} + \frac{1}{\cos \theta_v}$ is the geometric air mass factor for solar zenith angle $\theta_0$ and viewing zenith angle $\theta_v$.
- $m(z)$ are altitude-dependent box air mass factors (weighting functions) computed using the DAK (Doubling-Adding KNMI) radiative transfer model.
- $A_s$ is the Lambertian surface albedo.
- $p_s$ is surface atmospheric pressure.
- $S(z)$ is the normalized trace gas shape profile ($\int S(z) dz = 1$).

### 2.3 Regulatory Thresholds & Air Quality Classification
In `eo-mcp`, tropospheric column densities are converted to SI units ($\mu\text{mol}/\text{m}^2$) and evaluated against European Air Quality thresholds:

| Trace Gas Species | Chemical Formula | Clean Baseline ($\mu\text{mol}/\text{m}^2$) | Moderate Quality ($\mu\text{mol}/\text{m}^2$) | Poor / Plume Alert ($\mu\text{mol}/\text{m}^2$) | Primary Emission Sources |
|-------------------|------------------|---------------------------------------------|-----------------------------------------------|------------------------------------------------|--------------------------|
| **Nitrogen Dioxide** | $\text{NO}_2$ | $< 50$ | $50\text{--}150$ | $> 150$ | Fossil fuel combustion, vehicular exhaust, power plants |
| **Carbon Monoxide** | $\text{CO}$ | $< 25,000$ | $25,000\text{--}40,000$ | $> 40,000$ | Incomplete combustion, biomass burning, industrial flaring |
| **Sulfur Dioxide** | $\text{SO}_2$ | $< 200$ | $200\text{--}800$ | $> 800$ | Coal-fired generation, metal smelting, volcanic degassing |
| **Methane** | $\text{CH}_4$ | $< 1,850\text{ ppb}$ | $1,850\text{--}1,920\text{ ppb}$ | $> 1,920\text{ ppb}$ | Oil & gas leaks, coal mines, landfills, enteric fermentation |

---

## 3. Sensor Band Configurations & Spatial Resolutions

The Copernicus Sentinel-5 Precursor (S5P) carries the TROPOMI push-broom grating spectrometer operating in four distinct optical bands:

| Spectral Band | Spectral Range (nm) | Spectral Resolution (nm) | Native Spatial Resolution (km$^2$) | Target Trace Gases |
|---------------|---------------------|--------------------------|-----------------------------------|-------------------|
| **UV 1 / UV 2** | $270\text{--}370\text{ nm}$ | $0.45\text{--}0.50\text{ nm}$ | $3.5 \times 28\text{ km}$ (UV1) / $3.5 \times 5.5\text{ km}$ | $\text{O}_3$ profile, $\text{SO}_2$, Aerosol Index |
| **Visible (VIS)** | $370\text{--}500\text{ nm}$ | $0.55\text{ nm}$ | $3.5 \times 5.5\text{ km}$ | $\text{NO}_2$, $\text{HCHO}$, Glyoxal, $\text{O}_3$ column |
| **Near-Infrared (NIR)** | $675\text{--}775\text{ nm}$ | $0.38\text{ nm}$ | $3.5 \times 5.5\text{ km}$ | Cloud parameters ($\text{O}_2$-A band), Aerosol layer height |
| **Shortwave Infrared (SWIR)** | $2305\text{--}2385\text{ nm}$ | $0.25\text{ nm}$ | $5.5 \times 7.0\text{ km}$ | $\text{CO}$, $\text{CH}_4$, Water vapor ($\text{H}_2\text{O}$) |

*Note on Resolution:* S5P operational spatial resolution was upgraded on 6 August 2019 from $7.0 \times 5.5\text{ km}^2$ to $5.5 \times 3.5\text{ km}^2$ in the along-track direction.

---

## 4. Algorithmic Implementation in `eo-mcp`

The atmospheric processing pipeline is implemented in `src/eo_mcp/core/emissions.py` and exposed via `@eo_tool` `monitor_atmospheric_emissions` in `src/eo_mcp/server.py`.

### 4.1 TROPOMI STAC Discovery & Ingestion
```python
# src/eo_mcp/core/emissions.py

def query_sentinel5p_emissions(
    bbox: List[float],
    gas: str = "NO2",
    datetime_range: str = "2024-07-01/2024-07-05",
    qa_threshold: float = 0.50
) -> Dict[str, Any]:
    """Query Copernicus Sentinel-5P TROPOMI Level-2 trace gas products.
    
    Filters pixels by qa_value >= qa_threshold (eliminating cloudy pixels).
    Converts raw column densities to micromoles per square meter (umol/m^2).
    """
    ...
```

### 4.2 OpenAQ In-Situ Validation Cross-Correlation
```python
# src/eo_mcp/core/emissions.py

def fetch_openaq_ground_truth(
    bbox: List[float],
    parameter: str = "no2",
    datetime_range: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve ground-level regulatory air quality station measurements (OpenAQ API).
    
    Cross-references satellite tropospheric column densities (umol/m^2) with
    surface in-situ concentrations (ug/m^3 or ppm).
    """
    ...
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Cloud Obscuration & Quality Flagging (`qa_value`)
Because visible and ultraviolet radiation cannot penetrate optical clouds, TROPOMI trace gas retrievals over cloudy pixels exhibit severe errors.
- **Mitigation in `eo-mcp`:** Every retrieval enforces strict quality assurance filtering using the operational S5P quality flag:
  $$\text{qa\_value} \ge 0.50 \quad (\ge 0.75 \text{ for cloud-free clear-sky scenes})$$
  Pixels with cloud radiance fraction $> 0.30$ or affected by snow/ice albedo errors are automatically excluded from spatial averaging.

### 5.2 Boundary Layer Mixing & Topography
TROPOMI measures the **vertically integrated column density** ($\mu\text{mol}/\text{m}^2$) rather than surface concentration ($\mu\text{g}/\text{m}^3$). A high columnar reading can reflect a dispersed plume aloft (e.g., long-range biomass smoke) rather than severe surface air breathing hazards.
- **Mitigation in `eo-mcp`:** The tool integrates OpenAQ ground-truth in-situ stations, allowing users to verify whether elevated satellite columns correspond to surface breathing air pollution spikes.

### 5.3 Surface Albedo Sensitivity over Urban Surfaces
Air Mass Factors are acutely sensitive to surface reflectance ($A_s$). High-albedo concrete can cause underestimation of column densities if the surface albedo climatology is uncalibrated.
- **Mitigation in `eo-mcp`:** S5P processing incorporates the high-resolution TROPOMI surface albedo climatology derived at $0.1^\circ \times 0.1^\circ$ resolution, minimizing localized urban albedo bias.

---

## 6. Peer-Reviewed References

- **Veefkind, J. P., Aben, I., McMullan, K., Förster, H., de Vries, J., Otter, G., Claas, J., Eskes, H. J., de Haan, J. F., Kleipool, Q., van Weele, M., Hasekamp, O., Hoogeveen, R., Landgraf, J., Snel, R., Tol, P., Ingmann, P., Voors, R., Kruizinga, B., Vink, R., Visser, H., & Levelt, P. F. (2012).** TROPOMI on the ESA Sentinel-5 Precursor: A GMES mission for global observations of the atmospheric composition for climate, air quality and ozone layer applications. *Remote Sensing of Environment*, 120, 70–83. [DOI: 10.1016/j.rse.2011.09.027](https://doi.org/10.1016/j.rse.2011.09.027)
- **van Geffen, J., Boersma, K. F., Eskes, H., Sneep, M., ter Linden, M., Zara, M., & Veefkind, J. P. (2020).** S5P TROPOMI NO2 slant column retrieval: Method, stability, uncertainties and comparisons with OMI. *Atmospheric Measurement Techniques*, 13(3), 1315–1335. [DOI: 10.5194/amt-13-1315-2020](https://doi.org/10.5194/amt-13-1315-2020)
