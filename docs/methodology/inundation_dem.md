# Coastal Inundation, Elevation Geodesy & Sea Level Rise

## Executive & Scientific Summary

Accelerating global sea level rise (SLR) and extreme meteorological storm surges pose severe structural risks to coastal communities, critical transport infrastructure, and low-lying deltas. Article 6 of the European Union Floods Directive (2007/60/EC) mandates systematic flood hazard and risk mapping for coastal regions under low, medium, and high probability scenarios.

The `eo-mcp` flood risk and terrain intelligence suite (`simulate_sea_level_rise` and `get_elevation_profile`) implements rigorous hydrodynamic inundation modeling based on:
1. **Copernicus DEM GLO-30 Geodesy**: Direct integration of the world's most accurate 30-meter global digital surface model, derived from TanDEM-X radar interferometry (European Space Agency 2020; Guth & Geoffroy 2021).
2. **8-Connected Hydrologic Flood-Fill Algorithm**: Elimination of naive "bathtub" elevation slicing by enforcing strict topological path connectivity from open ocean boundary seeds to inland cells (Poulter & Halpin 2008).
3. **Elevation Uncertainty & Vertical Error Modeling**: Statistical bounds incorporating vertical root mean square error ($RMSE_z$) and 90% linear error ($LE90$) into flood hazard delineations (Gesch 2009; 2018).
4. **IPCC AR6 Standardized Climate Scenarios**: Pre-configured projections from the Intergovernmental Panel on Climate Change Sixth Assessment Report (Fox-Kemper et al. 2021) spanning SSP1-2.6, SSP2-4.5, and SSP5-8.5 by 2100.
5. **Horn Surface Normal Terrain Inversion**: Topographic slope and aspect calculation via finite-difference weighted 8-neighbor gradient operators (Horn 1981).

---

## 1. Physical & Radiative Transfer Principles

### 1.1 Total Coastal Water Level Dynamics
Coastal inundation occurs when the instantaneous extreme water level ($z_{\text{water}}$) exceeds the topographic elevation of the land surface ($z_{\text{topo}}$). Total water level is a superposition of four physical processes:

$$z_{\text{water}} = z_{\text{datum}} + \text{SLR}_{\text{climate}} + \Delta z_{\text{tide}} + \eta_{\text{surge}} + R_{2\%}$$

Where:
- $z_{\text{datum}}$: Vertical geodetic datum offset (e.g., Mean Higher High Water, MHHW, or Mean Sea Level, MSL).
- $\text{SLR}_{\text{climate}}$: Mean sea level rise driven by oceanic thermal expansion and land ice melting (Greenland and Antarctic ice sheets, mountain glaciers).
- $\Delta z_{\text{tide}}$: Astronomical spring tide amplitude.
- $\eta_{\text{surge}}$: Meteorological storm surge forced by inverse barometric pressure drop ($\approx 1\text{ cm per hPa}$) and onshore cyclonic wind stress:
  $$\eta_{\text{surge}} = \frac{1}{\rho_w g} \Delta P_a + \int \frac{\tau_w}{\rho_w g h} dx$$
- $R_{2\%}$: Wave setup and swash runup.

```
Elevation (m)
     ^
     |                                  +----------------- Natural Ridge / Sea Dike
     |                                 / \                 (Height: +2.5m)
     |                                /   \
+2.0 +~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~/     \                +-----------------
     | Extreme Water Level (+1.8m)  /       \              / Protected Basin
+1.0 |                             /         \            /  (Elev: +0.8m)
     |                            /           \__________/   [UNFLOODED via 8-connected]
 0.0 +---------------------------+                           [FALSELY FLOODED in Bathtub]
     | Open Ocean Boundary       Shoreline
```

### 1.2 Hydrologic Connectivity vs. Naive "Bathtub" Inundation
Standard GIS "bathtub" models assume every pixel with elevation $z(x, y) \le z_{\text{water}}$ will flood. In real topography, interior low-lying basins, reclaimed agricultural polders, and quarries often lie below projected water levels but remain completely dry because elevated natural coastal dunes, road embankments, or protective sea walls block hydraulic flow.

As established by Poulter & Halpin (2008), realistic inundation modeling must enforce **topological flow connectivity**: a cell only inundates if there exists a contiguous, uninterrupted hydraulic flow path of inundated neighboring cells connecting it back to an open sea boundary seed.

---

## 2. Exact Mathematical Formulations

### 2.1 8-Connected Breadth-First Flood-Fill
Let the digital elevation model be a discrete grid $Z \in \mathbb{R}^{M \times N}$, where cell $(r, c)$ has ground elevation $z(r, c)$.

1. **Ocean Boundary Seed Set ($\mathcal{S}$):** Identify all perimeter boundary cells that border open marine waters:
   $$\mathcal{S} = \{(r, c) \mid (r, c) \in \partial Z \land z(r, c) \le z_{\text{water}}\}$$

2. **8-Neighborhood Connectivity ($\mathcal{N}_8$):** For any cell $(r, c)$, its 8-connected neighbors are:
   $$\mathcal{N}_8(r, c) = \{(r+\Delta r, c+\Delta c) \mid \Delta r, \Delta c \in \{-1, 0, +1\} \setminus (0, 0)\}$$

3. **Inundation Condition:** A cell $(r, c)$ is inundated ($I(r, c) = 1$) if and only if:
   $$z(r, c) \le z_{\text{water}} \quad \text{AND} \quad \exists \text{ path } \{(r_0, c_0), (r_1, c_1), \dots, (r_k, c_k) = (r, c)\}$$
   Such that $(r_0, c_0) \in \mathcal{S}$ and $\forall j \in [0, k-1], (r_{j+1}, c_{j+1}) \in \mathcal{N}_8(r_j, c_j)$ with $z(r_j, c_j) \le z_{\text{water}}$.

4. **Inundation Depth:**
   $$D(r, c) = \begin{cases} z_{\text{water}} - z(r, c) & \text{if } I(r, c) = 1 \\ 0.0 & \text{otherwise} \end{cases}$$

### 2.2 Vertical Elevation Uncertainty & Confidence Intervals (Gesch 2009; 2018)
Digital elevation models carry vertical measurement error $\epsilon_z \sim \mathcal{N}(0, \sigma_z^2)$, characterized by root mean square error ($RMSE_z$):

$$RMSE_z = \sqrt{\frac{1}{N} \sum_{i=1}^N (z_{\text{DEM}, i} - z_{\text{truth}, i})^2}$$

The 90% linear error ($LE90$) corresponds to:

$$LE90 = 1.6449 \cdot RMSE_z$$

Under the Gesch (2018) protocol:
- **Minimum Inundation Mapping Threshold:** To delineate a sea-level rise increment with statistical confidence ($\ge 90\%$), the water level increment $\Delta z_{\text{water}}$ must exceed the DEM elevation error:
  $$\Delta z_{\text{water}} \ge LE90$$
- For Copernicus DEM GLO-30, independent validation by Guth & Geoffroy (2021) establishes a global vertical $RMSE_z \approx 1.2\text{--}1.7\text{ m}$ in coastal plains, outperforming SRTM ($RMSE_z \approx 4.0\text{ m}$) and NASADEM ($RMSE_z \approx 3.2\text{ m}$).

### 2.3 IPCC AR6 Standardized Sea Level Rise Projections
In accordance with IPCC Working Group I (Fox-Kemper et al. 2021), `eo-mcp` implements median projections and 90% confidence ranges for global mean sea level rise relative to 1995–2014 baselines:

| Scenario Code | Shared Socioeconomic Pathway | 2050 Median SLR (m) | 2100 Median SLR (m) | 2100 90% Likely Range (m) |
|---------------|------------------------------|---------------------|---------------------|---------------------------|
| `SSP1-2.6` | Very low greenhouse gas emissions (Paris Agreement $1.5^\circ\text{C}$) | $+0.19$ | $+0.44$ | $[+0.28, +0.55]$ |
| `SSP2-4.5` | Intermediate emissions (Current national NDC trajectories) | $+0.23$ | $+0.56$ | $[+0.44, +0.76]$ |
| `SSP5-8.5` | Very high emissions (Fossil-fueled development) | $+0.30$ | $+0.77$ | $[+0.63, +1.02]$ |

### 2.4 Horn Surface Gradient & Topographic Inversion (1981)
To compute slope and aspect across digital elevation rasters, `eo-mcp` uses Horn's 8-neighbor weighted finite difference convolution:

$$\left[\frac{\partial z}{\partial x}\right] = \frac{(z_{++} + 2 z_{0+} + z_{-+}) - (z_{+-} + 2 z_{0-} + z_{--})}{8 \cdot \Delta x}$$

$$\left[\frac{\partial z}{\partial y}\right] = \frac{(z_{++} + 2 z_{+0} + z_{+-}) - (z_{-+} + 2 z_{-0} + z_{--})}{8 \cdot \Delta y}$$

$$\text{Slope} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \cdot \frac{180^\circ}{\pi}$$

$$\text{Aspect} = \left(270^\circ - \arctan2\left(\frac{\partial z}{\partial y}, -\frac{\partial z}{\partial x}\right) \cdot \frac{180^\circ}{\pi}\right) \pmod{360^\circ}$$

---

## 3. Sensor & DEM Dataset Specifications

| Specification | Copernicus DEM GLO-30 (COP-DEM-GLO-30) |
|---------------|----------------------------------------|
| **Acquisition Instrument** | TanDEM-X / TerraSAR-X X-band radar interferometer |
| **Provider** | European Space Agency (ESA) & Airbus Defence and Space |
| **Native Spatial Resolution** | 1.0 arc-second ($\approx 30\text{ meters}$ at the equator) |
| **Horizontal Datum** | WGS84 (EPSG:4326) |
| **Vertical Datum** | Earth Gravitational Model 2008 (EGM2008 Geoid) |
| **Global Absolute Vertical Accuracy** | $< 4.0\text{ m}$ (90% linear error globally); $< 1.7\text{ m}$ in flat coastal terrains |
| **Void Filling** | High-quality multi-source auxiliary interpolation (SRTM, AW3D30, LiDAR) |

---

## 4. Algorithmic Implementation in `eo-mcp`

The inundation and terrain logic is implemented in `src/eo_mcp/core/inundation.py` and `src/eo_mcp/core/dem.py`, exposed via `@eo_tool` functions `simulate_sea_level_rise` and `get_elevation_profile`.

### 4.1 8-Connected Inundation Simulator
```python
# src/eo_mcp/core/inundation.py

def simulate_connected_inundation(
    dem: np.ndarray,
    water_level_rise_m: float,
    storm_surge_m: float = 0.0,
    datum_offset_m: float = 0.0,
    pixel_size_m: float = 30.0
) -> Dict[str, Any]:
    """Simulate hydro-connected coastal inundation using BFS flood-fill.
    
    Prevents interior low-lying basins from false flooding if they are
    physically separated from open ocean seeds by terrain ridges or levees.
    """
    total_water_level = datum_offset_m + water_level_rise_m + storm_surge_m
    rows, cols = dem.shape
    
    # 1. Identify ocean seeds along boundary cells
    # 2. Execute breadth-first search across 8-connected neighbors
    # 3. Calculate inundated surface area (ha) and depth grid (m)
    ...
```

### 4.2 Topographic Gradient Analysis
```python
# src/eo_mcp/core/dem.py

def compute_slope_and_aspect(elevation: np.ndarray, cellsize_m: float = 30.0) -> Tuple[np.ndarray, np.ndarray]:
    """Compute slope and aspect using Horn's 8-neighbor weighted finite difference."""
    # Applies 3x3 convolution kernels for dz/dx and dz/dy
    ...
```

---

## 5. Sensor Saturation, Limitations, & Noise Mitigation

### 5.1 Digital Surface Model (DSM) Canopy & Infrastructure Bias
Copernicus DEM GLO-30 is a **Digital Surface Model (DSM)**, meaning the X-band radar signal reflected from the tops of forest canopies, coastal mangroves, and urban buildings, rather than the bare ground surface (DTM). In dense coastal forests (e.g., mangroves), recorded elevations may be $5\text{--}15\text{ meters}$ higher than actual ground level, artificially masking vulnerable flood paths.
- **Mitigation in `eo-mcp`:** The model notes DSM limitations in output summaries. For high-stakes urban infrastructure, users are advised to supplement with localized airborne LiDAR DTMs where available.

### 5.2 Sub-Grid Hydraulic Structures (Culverts, Tunnels, Dikes)
At a 30-meter grid resolution, narrow linear features such as culverts, tide gates, drainage ditches, and subway portals are sub-resolution and not resolved in the DEM. A highway embankment may appear as a solid levee when in reality a culvert permits tidal influx.
- **Mitigation in `eo-mcp`:** Users can define regional seed boundaries or simulate failure scenarios by adjusting datum offsets and storm surge parameters.

### 5.3 Vertical Datum Alignment
Copernicus DEM elevations are referenced to the **EGM2008 Geoid**, whereas local tides and sea level rise are referenced to local **Tidal Datums** (e.g., Mean Sea Level or Mean High Water).
- **Mitigation in `eo-mcp`:** The `datum_offset_m` parameter enables users to supply local geoid-to-tidal-datum separation values (e.g., NOAA VDatum or European National Geodetic offsets).

---

## 6. Peer-Reviewed References

- **Poulter, B., & Halpin, P. N. (2008).** Raster modelling of coastal flooding from sea-level rise. *International Journal of Geographical Information Science*, 22(2), 167–182. [DOI: 10.1080/13658810701371858](https://doi.org/10.1080/13658810701371858)
- **Gesch, D. B. (2009).** Analysis of lidar elevation data for improved identification and delineation of lands vulnerable to sea-level rise. *Journal of Coastal Research*, SI(53), 49–58. [DOI: 10.2112/si53-006.1](https://doi.org/10.2112/si53-006.1)
- **Gesch, D. B. (2018).** Best practices for elevation-based assessments of sea-level rise and coastal flooding exposure. *Frontiers in Earth Science*, 6, 230. [DOI: 10.3389/feart.2018.00230](https://doi.org/10.3389/feart.2018.00230)
- **Fox-Kemper, B., Hewitt, H. T., Xiao, C., et al. (2021).** Ocean, cryosphere and sea level change. In *Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change*, pp. 1211–1362. Cambridge University Press. [DOI: 10.1017/9781009157896.011](https://doi.org/10.1017/9781009157896.011)
- **Horn, B. K. P. (1981).** Hill shading and the reflectance map. *Proceedings of the IEEE*, 69(1), 14–47. [DOI: 10.1109/PROC.1981.11918](https://doi.org/10.1109/PROC.1981.11918)
- **European Space Agency. (2020).** Copernicus Complex Digital Elevation Model (COP-DEM) Validation Report. *Issue 4.0*, Airbus Defence and Space & ESA. [Official Report PDF](https://spacedata.copernicus.eu/documents/20126/0/Copernicus+DEM+Validation+Report+v4.0.pdf)
- **Guth, P. L., & Geoffroy, T. M. (2021).** LiDAR point cloud and ICESat-2 evaluation of 1 second global digital elevation models: Copernicus wins. *Transactions in GIS*, 25(5), 2245–2261. [DOI: 10.1111/tgis.12825](https://doi.org/10.1111/tgis.12825)
