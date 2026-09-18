# Maritime Radar Surveillance, Target Detection & Oil Slicks

## Executive & Scientific Summary

Maritime domain awareness requires 24/7, all-weather surveillance across vast, cloud-covered exclusive economic zones (EEZs) and international shipping lanes. Synthetic Aperture Radar (SAR) is the primary spaceborne instrument for maritime security because active microwave pulses penetrate dense cloud cover, precipitation, and darkness, operating independently of solar illumination.

The `eo-mcp` maritime intelligence engine (`detect_dark_vessels`) implements a multi-stage radar processing pipeline based on:
1. **Radar Cross Section (RCS) Backscatter Inversion**: Conversion of SAR intensities to normalized radar cross section ($\sigma^0$ in decibels).
2. **Two-Parameter Cell-Averaging Constant False Alarm Rate (CA-CFAR)**: Adaptive spatial statistical target detection over inhomogeneous ocean clutter (Finn & Johnson 1968; Novak et al. 1993; Crisp 2004).
3. **Automated Vessel Dimension & Heading Extraction**: Morphological clustering and inertia tensor analysis to estimate vessel length, beam, and orientation (Stasolla & Greidanus 2016).
4. **Spatio-Temporal AIS Transponder Cross-Correlation**: Great-circle kinematic association between radar detections and terrestrial/satellite Automatic Identification System (AIS) messages, classifying targets into `TRUSTED`, `DARK_VESSEL` (AIS deliberately deactivated or out of range), and `SPOOFED` (Pelich et al. 2019).
5. **Marangoni Hydrodynamic Oil Spill Delineation**: Detection of surfactant wave-damping slicks caused by illegal bilge dumping or tanker spills (Alpers & Hühnerfuss 1988).

---

## 1. Physical & Radiative Transfer Principles

### 1.1 Radar Backscatter Over the Ocean Surface
At microwave frequencies (Sentinel-1 C-band, frequency $f = 5.405\text{ GHz}$, wavelength $\lambda \approx 5.55\text{ cm}$), backscatter from the open ocean is governed primarily by **Bragg resonance scattering** with short capillary and gravity waves:

$$\lambda_B = \frac{\lambda}{2 \sin \theta_i}$$

Where $\lambda_B$ is the ocean wave wavelength resonant with incident radar wavelength $\lambda$ at local incidence angle $\theta_i$ ($29^\circ\text{--}46^\circ$ across the Sentinel-1 Interferometric Wide swath). Moderate wind fields generate centimeter-scale capillary ripples, producing diffuse backscatter in the $-18\text{ dB}$ to $-12\text{ dB}$ range for vertical-vertical (VV) polarization.

### 1.2 Dihedral & Trihedral Corner Scattering from Vessels
Man-made vessels constructed of conductive steel hulls, planar decks, and vertical bulkheads behave as **dihedral and trihedral corner reflectors**. Radar pulses undergo double or triple bounce reflections:
- An incident wave reflects from the horizontal sea surface onto the vertical hull, and bounces directly back to the satellite antenna.
- The resulting coherent backscatter yields extremely high normalized radar cross section values ($\sigma^0_{\text{VV}} \gg +10\text{ dB}$), appearing as intense bright points against the relatively dark ocean clutter background.

```
       Radar Antenna
           \     ^
            \   /  Coherent Double-Bounce
             \ /   Backscatter
              V
+-------------+
| Super-      |
| structure   |
|             |
+=============+===========             ~~~~~~~~ Sea Surface ~~~~~~~~
     Hull     |              \        /
              |               \      /
~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~V~~~~/~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

### 1.3 Marangoni Capillary Wave Damping (Oil Slicks)
When mineral oils or biogenic surfactants spread across the water surface, they form a monomolecular or thin film. The presence of this viscoelastic film creates surface tension gradients during wave deformation, triggering the **Marangoni effect** (Alpers & Hühnerfuss 1988). 
- Capillary and short gravity waves ($\lambda \approx 1\text{--}10\text{ cm}$) are heavily damped.
- The resonant Bragg scattering mechanism is eliminated.
- The surface becomes hydraulically smooth, reflecting microwave energy specularly away from the radar antenna.
- Oil slicks appear as conspicuous dark patches with deeply depressed backscatter ($\sigma^0_{\text{VV}} < -22.0\text{ dB}$).

---

## 2. Exact Mathematical Formulations

### 2.1 Radiometric Calibration to Decibel Backscatter ($\sigma^0$)
Raw digital numbers ($\text{DN}$) from Sentinel-1 Ground Range Detected (GRD) products are calibrated to sigma nought:

$$\sigma^0 = \frac{\text{DN}^2}{A_i^2}$$

$$\sigma^0\text{ [dB]} = 10 \log_{10}(\sigma^0 + \epsilon)$$

Where $A_i$ is the calibration lookup table gain value provided in product metadata, and $\epsilon = 10^{-10}$ is a numerical stabilizer preventing logarithmic singularity.

### 2.2 Sea-State Adaptive Cell-Averaging CFAR (CA-CFAR)
To detect vessels across varying wind conditions and sea states without manual threshold tuning, an adaptive concentric sliding window inspects each test cell $(x, y)$:

```
+-------------------------------------------------------+
|                TRAINING CLUTTER WINDOW                |
|       +---------------------------------------+       |
|       |              GUARD WINDOW             |       |
|       |       +---------------+       |       |       |
|       |       |   CELL UNDER  |       |       |       |
|       |       |   TEST (CUT)  |       |       |       |
|       |       +---------------+       |       |       |
|       |                               |       |       |
|       +---------------------------------------+       |
|                                                       |
+-------------------------------------------------------+
```

1. **Cell Under Test (CUT):** The central pixel evaluated for target presence.
2. **Guard Window ($W_{\text{guard}} \times W_{\text{guard}}$, default $3 \times 3$):** Pixels immediately surrounding the CUT excluded from clutter estimation to prevent vessel energy leakage into background statistics.
3. **Training Window ($W_{\text{train}} \times W_{\text{train}}$, default $15 \times 15$):** Outer sliding window measuring surrounding radar backscatter.
4. **Annular Clutter Region:** The valid clutter annulus formed by subtracting guard pixels from the training footprint:

$$\mu_{\text{annular}}(x,y) = \frac{1}{W_{\text{train}}^2 - W_{\text{guard}}^2} \left[ \sum_{(u,v) \in W_{\text{train}}} I(u,v) - \sum_{(u,v) \in W_{\text{guard}}} I(u,v) \right]$$

$$\sigma_{\text{annular}}(x,y) = \sqrt{\frac{1}{W_{\text{train}}^2 - W_{\text{guard}}^2} \left[ \sum_{(u,v) \in W_{\text{train}}} I^2(u,v) - \sum_{(u,v) \in W_{\text{guard}}} I^2(u,v) \right] - \mu_{\text{annular}}^2(x,y)}$$

#### Dynamic Sea-State Roughness Scaling ($\kappa_{\text{sea}}$)
Under elevated sea states (Beaufort scale 5+), wave crest breaking and sea spray induce heavy-tailed non-Rayleigh clutter, causing spurious false alarms in classical two-parameter CFAR. To maintain rigorous constant false alarm rates, `eo-mcp` applies a sea-state roughness multiplier $\kappa_{\text{sea}}$:

| Sea State Profile | Operational Criteria | Threshold Multiplier ($\kappa_{\text{sea}}$) |
| :--- | :--- | :--- |
| **`calm`** | Low wind / Capillary sea ($\sigma_{\text{sea}} < 1.8\text{ dB}$) | $\kappa_{\text{sea}} = 1.00$ |
| **`moderate`** | Moderate chop / 10–20 kt winds ($1.8 \le \sigma_{\text{sea}} \le 3.0\text{ dB}$) | $\kappa_{\text{sea}} = 1.10$ |
| **`rough`** | High sea state / Gale conditions ($\sigma_{\text{sea}} > 3.0\text{ dB}$) | $\kappa_{\text{sea}} = 1.25$ |
| **`auto`** | Image-wide background dispersion estimation: $\hat{\sigma} = \text{std}(\text{sar\_db})$ | Dynamically mapped |

The adaptive local detection threshold $T(x,y)$ is formulated as:

$$T(x,y) = \mu_{\text{annular}}(x,y) + \left(k_{\text{pfa}} \cdot \kappa_{\text{sea}}\right) \cdot \sigma_{\text{annular}}(x,y)$$

A pixel is flagged as a potential vessel detection if:

$$x_{\text{CUT}}(x,y) > T(x,y)$$

#### Signal-to-Clutter Ratio (SCR)
For each detected target cluster, `eo-mcp` extracts the localized Signal-to-Clutter Ratio (SCR) in decibels:

$$\text{SCR} = \sigma^0_{\text{peak}} - \mu_{\text{annular}} \quad \text{[dB]}$$

This enables downstream filtering of non-vessel radar artifacts and provides direct confidence scoring for coast guard operators.

### 2.3 Morphological Target Clustering & Vessel Sizing
Contiguous target pixels are grouped via connected component analysis. The vessel length $L_{\text{est}}$ and beam $W_{\text{est}}$ are calculated from the spatial covariance matrix (inertia tensor) of pixel coordinates $(x_k, y_k)$:

$$C = \begin{bmatrix} \text{Var}(x) & \text{Cov}(x, y) \\ \text{Cov}(x, y) & \text{Var}(y) \end{bmatrix}$$

Extracting the eigenvalues $\lambda_1 \ge \lambda_2$ of $C$:

$$L_{\text{est}} = 4 \cdot \sqrt{\lambda_1} \cdot \Delta s$$

$$W_{\text{est}} = 4 \cdot \sqrt{\lambda_2} \cdot \Delta s$$

Where $\Delta s$ is the ground pixel spacing (10 meters for Sentinel-1 IW GRD).

### 2.4 AIS Cross-Correlation & Dark Vessel Classification
For each detected SAR target at coordinates $(\phi_{\text{sar}}, \lambda_{\text{sar}})$, all candidate AIS transponder broadcasts within temporal window $\Delta t \le \pm 30\text{ minutes}$ are identified. The great-circle distance $d$ is computed via the Haversine formula:

$$d = 2 R_{\text{earth}} \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos \phi_{\text{sar}} \cos \phi_{\text{ais}} \sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$

- **`TRUSTED` Target:** $\min(d) \le 1.5\text{ km}$ AND reported AIS Speed Over Ground ($\text{SOG}$) is kinematically consistent.
- **`DARK_VESSEL` Target:** $\min(d) > 1.5\text{ km}$ or zero matching AIS transmissions in database. Flagged as a priority for coast guard interdiction.
- **`AIS_SPOOF` / Ghost Target:** An AIS transponder broadcasts active movement at $(\phi_{\text{ais}}, \lambda_{\text{ais}})$, but the corresponding SAR image exhibits no radar target above clutter ($x < T$), indicating transponder spoofing.

---

## 3. Sensor Configurations & Spatial Resolutions

| Parameter | Copernicus Sentinel-1A/C C-SAR | Specification / Operating Value |
|-----------|--------------------------------|---------------------------------|
| **Radar Center Frequency** | C-band | $5.405\text{ GHz}$ ($\lambda \approx 5.55\text{ cm}$) |
| **Primary Marine Acquisition Mode** | Interferometric Wide (IW) Swath | TOPSAR beam steering in azimuth |
| **Swath Width** | 250 km | Tri-subswath coverage (IW1, IW2, IW3) |
| **Polarimetric Channels** | Dual-polarization | $\text{VV} + \text{VH}$ or $\text{HH} + \text{HV}$ |
| **Ground Range Resolution** | GRD High Resolution (HR) | $20\text{ m} \times 22\text{ m}$ (equivalent 10m pixel spacing) |
| **Equivalent Number of Looks (ENL)**| 4.4 | Speckle reduction in multilook GRD |
| **Incidence Angle Range** | $29.1^\circ\text{ to }46.0^\circ$ | Near-range to far-range incidence |
| **Revisit Frequency** | 6 days (constellation) | Equator coverage cycle |

---

## 4. Algorithmic Implementation in `eo-mcp`

The maritime intelligence pipeline is implemented in `src/eo_mcp/core/maritime.py` and exposed via `@eo_tool` `detect_dark_vessels` in `src/eo_mcp/server.py`.

### 4.1 CA-CFAR Detector
```python
# src/eo_mcp/core/maritime.py

def cfar_vessel_detector(
    sar_db: np.ndarray,
    guard_window_size: int = 3,
    training_window_size: int = 15,
    pfa_factor: float = 3.5,
    min_cluster_pixels: int = 3,
    max_cluster_pixels: int = 500,
    sea_state: str = "auto"
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Sea-state adaptive concentric Cell-Averaging CFAR detector.
    
    Computes local sliding background clutter statistics via annular uniform
    filters (excluding guard window). Dynamically scales the PFA multiplier based on 
    sea-state roughness ('auto', 'calm', 'moderate', 'rough').
    
    Extracts centroid, estimated length/width, peak RCS, and localized SCR (dB).
    """
    # Computes annular clutter mean and variance via 2D convolution
    # Applies sea_state roughness multiplier kappa_sea
    # Thresholds CUT > local_mean + (pfa_factor * kappa_sea) * local_std
    # Labels connected target components and extracts vessel geometry & SCR
    ...
```

### 4.2 AIS Spatial Cross-Matching
```python
# src/eo_mcp/core/maritime.py

def correlate_sar_with_ais(
    sar_targets: List[Dict[str, Any]],
    ais_records: List[Dict[str, Any]],
    bbox: List[float],
    distance_threshold_km: float = 1.5
) -> Dict[str, Any]:
    """Correlate detected radar targets with live/cached AIS transponder feeds.
    
    Assigns status:
    - 'TRUSTED': Valid AIS transponder within distance_threshold_km.
    - 'DARK_VESSEL': Strong radar target without corresponding AIS transponder.
    """
    ...
```

### 4.3 Oil Slick Detection
```python
# src/eo_mcp/core/maritime.py

def detect_oil_spill_slicks(
    sar_db: np.ndarray,
    slick_threshold_db: float = -22.0,
    min_slick_pixels: int = 50
) -> List[Dict[str, Any]]:
    """Detect low-backscatter oil spill slicks caused by Marangoni capillary damping."""
    slick_mask = sar_db < slick_threshold_db
    # Connected component labeling and geometric contour extraction
    ...
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Radar Speckle Noise (Granular Interference)
Because SAR is a coherent imaging system, constructive and destructive interference among de-phased sub-resolution scatterers produces granular **speckle noise**. 
- **Mitigation in `eo-mcp`:** `sar_db` arrays are processed through spatial averaging filters (multilooking) and connected component minimum area thresholds (`min_cluster_pixels >= 3`). Isolated bright speckle spikes are discarded before target extraction.

### 5.2 Environmental Wind & Sea State Extremes
- **Low Wind Regimes ($< 3\text{ m/s}$):** Without wind to generate capillary waves, natural ocean backscatter drops into the noise floor ($\sigma^0 < -22\text{ dB}$), creating natural dark patches ("look-alikes") that mimic oil slicks.
- **High Sea States ($> 15\text{ m/s}$, Sea State $\ge 6$):** Wave breaking and sea spray generate intense, chaotic clutter with high spatial variance, increasing false alarms in the CA-CFAR detector.
- **Mitigation in `eo-mcp`:** The detection threshold scales dynamically with local clutter standard deviation $\sigma_{\text{clutter}}$. In violent sea states, the threshold rises proportionally, maintaining a constant false alarm rate.

### 5.3 Azimuth Ambiguities & Sidelobes
Extremely large commercial container ships (length $> 350\text{ m}$) can saturate radar receivers, generating periodic **azimuth ghost targets** shifted along the satellite flight trajectory by multiples of the pulse repetition frequency (PRF).
- **Mitigation in `eo-mcp`:** Targets are cross-referenced with spatial clustering geometry and realistic vessel aspect ratios to filter unphysical azimuth repetitions.

---

## 6. Peer-Reviewed References

- **Finn, H. M., & Johnson, R. S. (1968).** Adaptive detection mode with threshold control as a function of spatially sampled clutter-level estimates. *RCA Review*, 29(3), 414–464.
- **Novak, L. M., Owirka, G. J., & Netishen, C. M. (1993).** Performance of a high-resolution polarimetric SAR automatic target recognition system. *The Lincoln Laboratory Journal*, 6(1), 11–24. [MIT Lincoln Laboratory Report](https://www.ll.mit.edu/sites/default/files/publication/doc/migrated/llj/v06_n1/06_1automatic_target.pdf)
- **Crisp, D. J. (2004).** The state-of-the-art in ship detection in synthetic aperture radar imagery. *Defence Science and Technology Organisation (DSTO)*, Research Report DSTO-RR-0272. [DTIC ADA426451](https://apps.dtic.mil/sti/citations/ADA426451)
- **Stasolla, M., & Greidanus, H. (2016).** The exploitation of Sentinel-1 images for vessel size estimation. *Remote Sensing Letters*, 7(12), 1219–1228. [DOI: 10.1080/2150704X.2016.1226522](https://doi.org/10.1080/2150704X.2016.1226522)
- **Pelich, R., Chini, M., Hostache, R., Matgen, P., López-Martínez, C., Nuevo, M., Ries, P., & Eiden, G. (2019).** Large-scale automatic vessel monitoring based on dual-polarization Sentinel-1 and AIS data. *Remote Sensing*, 11(9), 1078. [DOI: 10.3390/rs11091078](https://doi.org/10.3390/rs11091078)
- **Alpers, W., & Hühnerfuss, H. (1988).** Radar signatures of oil films floating on the sea surface and the Marangoni effect. *Journal of Geophysical Research: Oceans*, 93(C4), 3642–3648. [DOI: 10.1029/JC093iC04p03642](https://doi.org/10.1029/JC093iC04p03642)
