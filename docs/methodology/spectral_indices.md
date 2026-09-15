# Multispectral Optical Indices & Vegetation Dynamics

## Executive & Scientific Summary

Multispectral optical vegetation and water indices form the cornerstone of terrestrial and hydrological remote sensing. By computing normalized band ratios across discrete regions of the solar reflective spectrum (0.4 to 2.5 µm), these indices isolate target biophysical signals while minimizing first-order multiplicative noise caused by topographic illumination variations, solar zenith angle changes, and atmospheric attenuation.

The `eo-mcp` spectral index engine (`calculate_spectral_index`) provides verified, calibrated implementations of five canonical spectral indices:
1. **Normalized Difference Vegetation Index (NDVI)**: Photosynthetically active biomass, canopy greenness, and vegetation health.
2. **Normalized Difference Water Index (NDWI - McFeeters 1996)**: Open surface water delineation and hydrographic boundary mapping.
3. **Normalized Difference Water Index (NDWI - Gao 1996)**: Vegetation canopy liquid water content and foliage water stress.
4. **Modified Normalized Difference Water Index (MNDWI - Xu 2006)**: Open water extraction with active suppression of built-up urban noise.
5. **Normalized Burn Ratio (NBR - Key & Benson 2006)**: Canopy moisture and post-wildfire charcoal/ash contrast.
6. **Enhanced Vegetation Index (EVI - Huete et al. 2002)**: High-biomass canopy monitoring with soil background adjustment and atmospheric aerosol resistance.

---

## 1. Physical & Radiative Transfer Principles

The spectral reflectance curve of healthy green vegetation is governed by two distinct cellular mechanisms:
- **Visible Wavelengths (0.40–0.70 µm):** Dominated by strong biochemical absorption by leaf photosynthetic pigments. Chlorophyll $a$ and $b$ absorb strongly in the blue ($\sim 0.45\ \mu\text{m}$) and red ($\sim 0.66\ \mu\text{m}$) bands, reflecting moderately in the green band ($\sim 0.55\ \mu\text{m}$).
- **Near-Infrared Wavelengths (0.70–1.30 µm):** Characterized by high scattering and low absorption within the internal spongy mesophyll leaf tissue. Multiple refraction across hydrated cell wall-air interfaces produces high diffuse reflectance ($40\%\text{--}60\%$).

The steep transition between the red absorption trough and the near-infrared reflectance plateau is termed the **Red Edge** ($0.68\text{--}0.75\ \mu\text{m}$). The ratio between red and near-infrared reflectance directly correlates with chlorophyll concentration and Leaf Area Index (LAI).

```
Reflectance (%)
  60 |                             +----------------- (NIR Plateau: Mesophyll Scattering)
     |                            /
  40 |                           /
     |                          / (Red Edge)
  20 |     (Green Peak)        /
     |        /\              /
   0 +-------/--\------------/----------------------- (Red Trough: Chlorophyll Absorption)
    0.4     0.5  0.6        0.7        0.8        0.9   Wavelength (um)
```

In contrast, clear liquid water exhibits moderate reflectance in visible wavelengths (blue/green) and strong absorption in the near-infrared and shortwave infrared ($> 0.8\ \mu\text{m}$), where liquid water absorption coefficients increase by orders of magnitude. Hydrocarbon and dry soil surfaces reflect moderately across visible and SWIR bands without exhibiting the characteristic vegetative red edge.

---

## 2. Exact Mathematical Formulations

### 2.1 Normalized Difference Vegetation Index (NDVI)
Formulated by Rouse et al. (1974) and validated by Tucker (1979):

$$\text{NDVI} = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}}}$$

Where:
- $\rho_{\text{NIR}}$ is the bottom-of-atmosphere (BOA) reflectance in the near-infrared band ($\approx 840\text{--}865\text{ nm}$).
- $\rho_{\text{Red}}$ is the BOA reflectance in the red chlorophyll absorption band ($\approx 640\text{--}670\text{ nm}$).
- Dynamic range: $[-1.0, +1.0]$. Values $> 0.20$ indicate green vegetation; values $> 0.60$ represent dense, healthy canopies.

### 2.2 Normalized Difference Water Index (NDWI - McFeeters 1996)
Formulated by McFeeters (1996) for open water delineation:

$$\text{NDWI}_{\text{McFeeters}} = \frac{\rho_{\text{Green}} - \rho_{\text{NIR}}}{\rho_{\text{Green}} + \rho_{\text{NIR}}}$$

Where:
- $\rho_{\text{Green}}$ is reflectance in the green band ($\approx 560\text{ nm}$), where water reflects moderately.
- $\rho_{\text{NIR}}$ is reflectance in the near-infrared band ($\approx 840\text{ nm}$), where water strongly absorbs.
- Positive values ($\text{NDWI} > 0$) typically designate open surface water, while terrestrial vegetation and dry soils yield negative values.

### 2.3 Normalized Difference Water Index (NDWI - Gao 1996)
Formulated by Gao (1996) for vegetation canopy liquid water:

$$\text{NDWI}_{\text{Gao}} = \frac{\rho_{\text{NIR}} - \rho_{\text{SWIR1}}}{\rho_{\text{NIR}} + \rho_{\text{SWIR1}}}$$

Where:
- $\rho_{\text{SWIR1}}$ is reflectance in the shortwave infrared water absorption band ($\approx 1240\text{--}1610\text{ nm}$).
- Reflects the moisture status of internal leaf foliage, serving as an early indicator of vegetative drought stress.

### 2.4 Modified Normalized Difference Water Index (MNDWI - Xu 2006)
Formulated by Xu (2006) to overcome urban false-positive water classifications:

$$\text{MNDWI} = \frac{\rho_{\text{Green}} - \rho_{\text{SWIR1}}}{\rho_{\text{Green}} + \rho_{\text{SWIR1}}}$$

Where:
- $\rho_{\text{SWIR1}}$ replaces the NIR band. Built-up impervious surfaces (asphalt, concrete, roofing) possess significantly higher reflectance in SWIR1 than in NIR.
- Consequently, urban built-up land yields distinctly negative MNDWI values, eliminating the false water detections prevalent in McFeeters NDWI over urbanized coastal zones.

### 2.5 Normalized Burn Ratio (NBR - Key & Benson 2006)
Formulated by Key & Benson (2006) for fire effects monitoring:

$$\text{NBR} = \frac{\rho_{\text{NIR}} - \rho_{\text{SWIR2}}}{\rho_{\text{NIR}} + \rho_{\text{SWIR2}}}$$

Where:
- $\rho_{\text{SWIR2}}$ is reflectance in the shortwave infrared band centered at $\approx 2200\text{ nm}$.
- Healthy vegetation reflects strongly in NIR and absorbs in SWIR2. Burned areas and charred soil absorb strongly in NIR (due to destroyed leaf structure) and reflect brightly in SWIR2 (due to exposed soil, rock, and desiccated charcoal).

### 2.6 Enhanced Vegetation Index (EVI - Huete et al. 2002)
Formulated by Huete et al. (2002) to optimize vegetation monitoring over high-biomass regions while correcting for soil background reflectance and atmospheric aerosol scattering:

$$\text{EVI} = G \cdot \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + C_1 \cdot \rho_{\text{Red}} - C_2 \cdot \rho_{\text{Blue}} + L}$$

Where:
- $G = 2.5$ is the gain factor.
- $C_1 = 6.0$ is the aerosol resistance coefficient for the red band.
- $C_2 = 7.5$ is the aerosol resistance coefficient for the blue band ($\approx 490\text{ nm}$).
- $L = 1.0$ is the canopy background soil adjustment factor.
- The blue band dynamically monitors atmospheric aerosol differential scattering, providing stability through atmospheric haze.

---

## 3. Sensor Band Mappings & Spatial Resolutions

The table below delineates the exact sensor band assignments and native spatial sampling intervals across Copernicus Sentinel-2 MSI and USGS/NASA Landsat 8/9 OLI:

| Spectral Channel | Wavelength Regime | Sentinel-2A/B MSI Band | Central $\lambda$ (nm) | Resolution (m) | Landsat 8/9 OLI Band | Central $\lambda$ (nm) | Resolution (m) | Primary Physical Purpose |
|------------------|-------------------|------------------------|------------------------|----------------|----------------------|------------------------|----------------|--------------------------|
| **Coastal Aerosol** | VNIR | Band 1 | 443 | 60 | Band 1 | 443 | 30 | Atmospheric aerosol retrieval, coastal ocean color |
| **Blue** | VNIR | Band 2 | 490 | 10 | Band 2 | 482 | 30 | Atmospheric aerosol correction in EVI, water penetration |
| **Green** | VNIR | Band 3 | 560 | 10 | Band 3 | 561 | 30 | Chlorophyll reflectance peak, open water mapping (NDWI, MNDWI) |
| **Red** | VNIR | Band 4 | 665 | 10 | Band 4 | 655 | 30 | Chlorophyll absorption trough (NDVI, EVI) |
| **Red Edge 1** | VNIR | Band 5 | 705 | 20 | — | — | — | Chlorophyll content, leaf nitrogen modeling |
| **Red Edge 2** | VNIR | Band 6 | 740 | 20 | — | — | — | Canopy structure, senescence onset |
| **Red Edge 3** | VNIR | Band 7 | 783 | 20 | — | — | — | Biomass estimation, LAI scaling |
| **NIR (Broad)** | VNIR | Band 8 | 842 | 10 | Band 5 | 865 | 30 | Spongy mesophyll scattering (NDVI, NDWI, EVI) |
| **NIR (Narrow)** | VNIR | Band 8A | 865 | 20 | Band 5 | 865 | 30 | Atmospheric water vapor reference, precise LAI |
| **Water Vapor** | SWIR | Band 9 | 945 | 60 | Band 9 (Cirrus) | 1373 | 30 | Atmospheric moisture correction, thin cirrus detection |
| **SWIR 1** | SWIR | Band 11 | 1610 | 20 | Band 6 | 1609 | 30 | Canopy liquid water (Gao NDWI), built-up suppression (MNDWI) |
| **SWIR 2** | SWIR | Band 12 | 2190 | 20 | Band 7 | 2201 | 30 | Burn scar detection (NBR), rock/mineral identification |

---

## 4. Algorithmic Implementation in `eo-mcp`

The computational workflows for spectral indices reside in `src/eo_mcp/core/spectral.py` and are exposed to MCP clients via the `@eo_tool` `calculate_spectral_index` in `src/eo_mcp/server.py`.

### 4.1 Numerical Implementations
```python
# src/eo_mcp/core/spectral.py

def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Calculate Normalized Difference Vegetation Index (NDVI).
    
    Guards against zero-division using np.errstate, returning NaN for
    unilluminated or null pixels. Output is clipped strictly to [-1.0, 1.0].
    """
    denominator = nir + red
    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi = np.where(denominator != 0, (nir - red) / denominator, np.nan)
    return np.clip(ndvi, -1.0, 1.0)


def compute_evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Calculate Enhanced Vegetation Index (EVI) with Huete et al. (2002) constants.
    
    EVI = 2.5 * (NIR - Red) / (NIR + 6.0 * Red - 7.5 * Blue + 1.0)
    """
    denominator = nir + 6.0 * red - 7.5 * blue + 1.0
    with np.errstate(divide='ignore', invalid='ignore'):
        evi = np.where(denominator != 0, 2.5 * (nir - red) / denominator, np.nan)
    return np.clip(evi, -1.0, 1.0)
```

### 4.2 Statistical Summary Extraction
For every bounding box query, `calculate_array_stats` extracts spatial metrics including `mean`, `min`, `max`, `std`, and valid pixel count:
```python
# src/eo_mcp/core/spectral.py

def calculate_array_stats(arr: np.ndarray) -> Dict[str, Any]:
    valid = arr[~np.isnan(arr)]
    if len(valid) == 0:
        return {"mean": None, "min": None, "max": None, "std": None, "valid_pixels": 0}
    return {
        "mean": float(np.mean(valid)),
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "std": float(np.std(valid)),
        "valid_pixels": int(len(valid))
    }
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Asymptotic NDVI Saturation over High-Biomass Canopies
In temperate forests, tropical rainforests, and dense agricultural crops where the Leaf Area Index ($\text{LAI}$) exceeds $3.0\ \text{m}^2/\text{m}^2$, red band reflectance reaches an asymptotic minimum ($\rho_{\text{Red}} \approx 0.02\text{--}0.03$), since almost all incident red photons are absorbed by upper canopy leaves. Consequently, further increases in biomass cannot produce significant drops in red reflectance, causing NDVI to plateau at values between $0.85$ and $0.92$.
- **Mitigation in `eo-mcp`:** When assessing closed-canopy forests or mature crop canopies, users are directed to compute **EVI**, which incorporates a feedback factor $L=1.0$ and blue aerosol correction to preserve linearity up to $\text{LAI} > 6.0$.

### 5.2 Atmospheric Aerosols & Sub-Pixel Clouds
Thin cirrus clouds, aerosol plumes, and maritime haze scatter shorter visible wavelengths (Rayleigh and Mie scattering), artificially inflating red and blue reflectance while leaving NIR relatively unaffected. This depresses NDVI.
- **Mitigation in `eo-mcp`:** The STAC discovery provider (`eo_mcp/providers/stac.py`) filters scenes by maximum cloud cover threshold (`max_cloud_cover <= 20%`). When streaming Sentinel-2 COGs, the Level-2A Scene Classification Layer (SCL) enables masking of cloud shadows (class 3), clouds (classes 8, 9, 10), and snow (class 11).

### 5.3 Zero Division & Floating Point Precision
Over shadow voids, deep open water bodies, or sensor dropouts, sums of near-zero spectral reflectances can cause numerical instability or division-by-zero exceptions.
- **Mitigation in `eo-mcp`:** Vectorized computations evaluate denominators within NumPy `errstate(divide='ignore', invalid='ignore')` blocks and explicitly replace zero-denominator elements with `np.nan` prior to array clamping.

---

## 6. Peer-Reviewed References

- **Tucker, C. J. (1979).** Red and photographic infrared linear combinations for monitoring vegetation. *Remote Sensing of Environment*, 8(2), 127–150. [DOI: 10.1016/0034-4257(79)90013-0](https://doi.org/10.1016/0034-4257(79)90013-0)
- **Rouse, J. W., Haas, R. H., Schell, J. A., & Deering, D. W. (1974).** Monitoring vegetation systems in the Great Plains with ERTS. *Third Earth Resources Technology Satellite-1 Symposium*, NASA SP-351, 1, 309–317. NASA Accession No. N74-30724.
- **McFeeters, S. K. (1996).** The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. *International Journal of Remote Sensing*, 17(7), 1425–1432. [DOI: 10.1080/01431169608948714](https://doi.org/10.1080/01431169608948714)
- **Gao, B.-C. (1996).** NDWI—A normalized difference water index for remote sensing of vegetation liquid water from space. *Remote Sensing of Environment*, 58(3), 257–266. [DOI: 10.1016/S0034-4257(96)00067-3](https://doi.org/10.1016/S0034-4257(96)00067-3)
- **Xu, H. (2006).** Modification of normalised difference water index (NDWI) to enhance open water features in remotely sensed imagery. *International Journal of Remote Sensing*, 27(14), 3025–3033. [DOI: 10.1080/01431160600589179](https://doi.org/10.1080/01431160600589179)
- **Huete, A., Didan, K., Miura, T., Rodriguez, E. P., Gao, X., & Ferreira, L. G. (2002).** Overview of the radiometric and biophysical performance of the MODIS vegetation indices. *Remote Sensing of Environment*, 83(1–2), 195–213. [DOI: 10.1016/S0034-4257(02)00096-2](https://doi.org/10.1016/S0034-4257(02)00096-2)
- **Key, C. H., & Benson, N. C. (2006).** Landscape Assessment (LA): Sampling and analysis methods. *FIREMON: Fire Effects Monitoring and Inventory System*, USDA Forest Service GTR-RMRS-164-CD, pp. LA 1–55. [USDA Treesearch](https://www.fs.usda.gov/treesearch/pubs/24503)
