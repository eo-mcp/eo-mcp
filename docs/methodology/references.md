# Scientific References & Foundational Literature

This repository and the `eo-mcp` planetary analysis tools are strictly grounded in verified peer-reviewed scientific literature, international geodetic standards, and European space policy frameworks. Every publication listed below has been verified against academic registry databases (Crossref, Semantic Scholar, Consensus API, and official space agency repositories).

---

## 1. Optical Spectral Indices & Vegetation Dynamics

- **Tucker, C. J. (1979).** Red and photographic infrared linear combinations for monitoring vegetation. *Remote Sensing of Environment*, 8(2), 127–150. [DOI: 10.1016/0034-4257(79)90013-0](https://doi.org/10.1016/0034-4257(79)90013-0)  
  *Implemented in:* `calculate_spectral_index` (`NDVI`). Provides empirical and theoretical validation of the normalized difference vegetation index over agricultural canopies.
- **Rouse, J. W., Haas, R. H., Schell, J. A., & Deering, D. W. (1974).** Monitoring vegetation systems in the Great Plains with ERTS. *Third Earth Resources Technology Satellite-1 Symposium*, NASA SP-351, 1, 309–317. NASA Accession No. N74-30724.  
  *Implemented in:* `calculate_spectral_index` (`NDVI`). The foundational NASA paper establishing NDVI from ERTS-1 (Landsat 1).
- **McFeeters, S. K. (1996).** The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. *International Journal of Remote Sensing*, 17(7), 1425–1432. [DOI: 10.1080/01431169608948714](https://doi.org/10.1080/01431169608948714)  
  *Implemented in:* `calculate_spectral_index` (`NDWI`). Defines the Green/NIR band ratio for open water detection.
- **Gao, B.-C. (1996).** NDWI—A normalized difference water index for remote sensing of vegetation liquid water from space. *Remote Sensing of Environment*, 58(3), 257–266. [DOI: 10.1016/S0034-4257(96)00067-3](https://doi.org/10.1016/S0034-4257(96)00067-3)  
  *Implemented in:* `calculate_spectral_index`. Formulates the NIR/SWIR water index sensitive to vegetation canopy moisture.
- **Xu, H. (2006).** Modification of normalised difference water index (NDWI) to enhance open water features in remotely sensed imagery. *International Journal of Remote Sensing*, 27(14), 3025–3033. [DOI: 10.1080/01431160600589179](https://doi.org/10.1080/01431160600589179)  
  *Implemented in:* `calculate_spectral_index` (`MNDWI`), `analyze_coastal_erosion`. Demonstrates suppression of built-up urban noise using SWIR instead of NIR.
- **Huete, A., Didan, K., Miura, T., Rodriguez, E. P., Gao, X., & Ferreira, L. G. (2002).** Overview of the radiometric and biophysical performance of the MODIS vegetation indices. *Remote Sensing of Environment*, 83(1–2), 195–213. [DOI: 10.1016/S0034-4257(02)00096-2](https://doi.org/10.1016/S0034-4257(02)00096-2)  
  *Implemented in:* `calculate_spectral_index` (`EVI`). Formulates the Enhanced Vegetation Index with atmospheric aerosol resistance.

---

## 2. Maritime Radar Surveillance, Target Detection & Oil Slicks

- **Finn, H. M., & Johnson, R. S. (1968).** Adaptive detection mode with threshold control as a function of spatially sampled clutter-level estimates. *RCA Review*, 29(3), 414–464.  
  *Implemented in:* `detect_dark_vessels`. Foundational mathematical derivation of Cell-Averaging Constant False Alarm Rate (CA-CFAR).
- **Novak, L. M., Owirka, G. J., & Netishen, C. M. (1993).** Performance of a high-resolution polarimetric SAR automatic target recognition system. *The Lincoln Laboratory Journal*, 6(1), 11–24. [MIT Lincoln Laboratory Report](https://www.ll.mit.edu/sites/default/files/publication/doc/migrated/llj/v06_n1/06_1automatic_target.pdf)  
  *Implemented in:* `detect_dark_vessels`. Multistage CFAR detection algorithms for polarimetric SAR.
- **Crisp, D. J. (2004).** The state-of-the-art in ship detection in synthetic aperture radar imagery. *Defence Science and Technology Organisation (DSTO)*, Research Report DSTO-RR-0272. [DTIC ADA426451](https://apps.dtic.mil/sti/citations/ADA426451)  
  *Implemented in:* `detect_dark_vessels`. Standard methodology review for SAR ship prescreening, thresholding, and land masking.
- **Stasolla, M., & Greidanus, H. (2016).** The exploitation of Sentinel-1 images for vessel size estimation. *Remote Sensing Letters*, 7(12), 1219–1228. [DOI: 10.1080/2150704X.2016.1226522](https://doi.org/10.1080/2150704X.2016.1226522)  
  *Implemented in:* `detect_dark_vessels`. Empirical validation of vessel dimension estimation from Sentinel-1 IW C-band SAR.
- **Pelich, R., Chini, M., Hostache, R., Matgen, P., López-Martínez, C., Nuevo, M., Ries, P., & Eiden, G. (2019).** Large-scale automatic vessel monitoring based on dual-polarization Sentinel-1 and AIS data. *Remote Sensing*, 11(9), 1078. [DOI: 10.3390/rs11091078](https://doi.org/10.3390/rs11091078)  
  *Implemented in:* `detect_dark_vessels`. Large-scale cross-matching of Sentinel-1 radar targets against terrestrial and satellite AIS telemetry.
- **Alpers, W., & Hühnerfuss, H. (1988).** Radar signatures of oil films floating on the sea surface and the Marangoni effect. *Journal of Geophysical Research: Oceans*, 93(C4), 3642–3648. [DOI: 10.1029/JC093iC04p03642](https://doi.org/10.1029/JC093iC04p03642)  
  *Implemented in:* `detect_dark_vessels` (`detect_oil_spill_slicks`). Hydrodynamic theory of surfactant Marangoni wave damping producing dark backscatter in SAR.

---

## 3. Coastal Dynamics & Inundation Modeling

- **Thieler, E. R., Himmelstoss, E. A., Zichichi, J. L., & Ergul, A. (2009).** Digital Shoreline Analysis System (DSAS) version 4.0—An ArcGIS extension for calculating shoreline change. *U.S. Geological Survey Open-File Report 2008-1278*, 72 p. [DOI: 10.3133/ofr20081278](https://doi.org/10.3133/ofr20081278)  
  *Implemented in:* `analyze_coastal_erosion`. Standardizes End Point Rate (EPR) and Net Shoreline Movement (NSM).
- **Himmelstoss, E. A., Henderson, R. E., Kratzmann, M. G., & Farris, A. S. (2018).** Digital Shoreline Analysis System (DSAS) version 5.0 user guide. *U.S. Geological Survey Open-File Report 2018-1179*, 110 p. [DOI: 10.3133/ofr20181179](https://doi.org/10.3133/ofr20181179)  
  *Implemented in:* `analyze_coastal_erosion`. Updated reference for transect casting, baseline offset, and statistical confidence intervals.
- **Vos, K., Splinter, K. D., Harley, M. D., Simmons, J. A., & Turner, I. L. (2019).** CoastSat: A Google Earth Engine-enabled Python toolkit to extract shorelines from publicly available satellite imagery. *Environmental Modelling & Software*, 122, 104528. [DOI: 10.1016/j.envsoft.2019.104528](https://doi.org/10.1016/j.envsoft.2019.104528)  
  *Implemented in:* `analyze_coastal_erosion`. Sub-pixel satellite shoreline extraction using Otsu thresholding and morphological boundary detection.
- **Otsu, N. (1979).** A threshold selection method from gray-level histograms. *IEEE Transactions on Systems, Man, and Cybernetics*, 9(1), 62–66. [DOI: 10.1109/TSMC.1979.4310076](https://doi.org/10.1109/TSMC.1979.4310076)  
  *Implemented in:* `extract_water_mask_otsu`. Non-parametric between-class variance maximization for bimodal segmentation.
- **Poulter, B., & Halpin, P. N. (2008).** Raster modelling of coastal flooding from sea-level rise. *International Journal of Geographical Information Science*, 22(2), 167–182. [DOI: 10.1080/13658810701371858](https://doi.org/10.1080/13658810701371858)  
  *Implemented in:* `simulate_sea_level_rise`. Establishes the 8-connected hydrologic flood-fill algorithm preventing unflooded interior depressions from false inundation.
- **Gesch, D. B. (2009).** Analysis of lidar elevation data for improved identification and delineation of lands vulnerable to sea-level rise. *Journal of Coastal Research*, SI(53), 49–58. [DOI: 10.2112/si53-006.1](https://doi.org/10.2112/si53-006.1)  
  *Implemented in:* `simulate_sea_level_rise`. Quantifies vertical uncertainty and elevation bias in coastal hydrodynamic inundation models.
- **Gesch, D. B. (2018).** Best practices for elevation-based assessments of sea-level rise and coastal flooding exposure. *Frontiers in Earth Science*, 6, 230. [DOI: 10.3389/feart.2018.00230](https://doi.org/10.3389/feart.2018.00230)  
  *Implemented in:* `simulate_sea_level_rise`. Rigorous elevation modeling protocols for SLR hazard assessments under EU Floods Directive.
- **Fox-Kemper, B., Hewitt, H. T., Xiao, C., Aðalgeirsdóttir, G., Drijfhout, S. S., Edwards, T. L., Golledge, N. R., Hemer, M., Kopp, R. E., Krinner, G., Mix, A., Notz, D., Nowicki, S., Nurhati, I. S., Ruiz, L., Sallée, J.-B., Slangen, A. B. A., & Yu, Y. (2021).** Ocean, cryosphere and sea level change. In *Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change*, pp. 1211–1362. Cambridge University Press. [DOI: 10.1017/9781009157896.011](https://doi.org/10.1017/9781009157896.011)  
  *Implemented in:* `simulate_sea_level_rise`. Authoritative source for standardized SSP1-2.6 (+0.44m), SSP2-4.5 (+0.56m), and SSP5-8.5 (+0.77m) median SLR projections by 2100.

---

## 4. Active Wildfires, Fire Radiative Power & Burn Severity

- **Schroeder, W., Oliva, P., Giglio, L., & Csiszar, I. A. (2014).** The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment. *Remote Sensing of Environment*, 143, 85–96. [DOI: 10.1016/j.rse.2013.12.008](https://doi.org/10.1016/j.rse.2013.12.008)  
  *Implemented in:* `detect_active_wildfires`. Validates the 375m spatial resolution VIIRS I-band active fire detection algorithm.
- **Giglio, L., Schroeder, W., & Justice, C. O. (2016).** The collection 6 MODIS active fire detection algorithm and fire products. *Remote Sensing of Environment*, 178, 31–41. [DOI: 10.1016/j.rse.2016.02.054](https://doi.org/10.1016/j.rse.2016.02.054)  
  *Implemented in:* `detect_active_wildfires`. Formulation of contextual thermal anomaly detection using 4 µm and 11 µm channels.
- **Wooster, M. J. (2003).** Fire radiative energy for quantitative study of biomass burning: Derivation from the BIRD experimental satellite and comparison to MODIS fire products. *Remote Sensing of Environment*, 86(1), 83–107. [DOI: 10.1016/S0034-4257(03)00070-1](https://doi.org/10.1016/S0034-4257(03)00070-1)  
  *Implemented in:* `detect_active_wildfires`. Theoretical derivation connecting Mid-Infrared (MIR) pixel radiance to Fire Radiative Power (MW).
- **Wooster, M. J., Roberts, G., Perry, G. L. W., & Kaufman, Y. J. (2005).** Retrieval of biomass combustion rates and totals from fire radiative power observations: FRP derivation and calibration relationships. *Journal of Geophysical Research: Atmospheres*, 110(D24), D24311. [DOI: 10.1029/2005JD006318](https://doi.org/10.1029/2005JD006318)  
  *Implemented in:* `detect_active_wildfires`. Demonstrates direct linear proportionality between FRE (Fire Radiative Energy) and combusted fuel mass ($0.368 \pm 0.015\text{ kg/MJ}$).
- **Key, C. H., & Benson, N. C. (2006).** Landscape Assessment (LA): Sampling and analysis methods. *FIREMON: Fire Effects Monitoring and Inventory System*, USDA Forest Service GTR-RMRS-164-CD, pp. LA 1–55. [USDA Treesearch](https://www.fs.usda.gov/treesearch/pubs/24503)  
  *Implemented in:* `calculate_burn_severity`. Formulation of the Normalized Burn Ratio Difference (dNBR) and Composite Burn Index (CBI).
- **Parks, S. A., Dillon, G. K., & Miller, C. (2014).** A new metric for quantifying burn severity: The Relativized Burn Ratio. *Remote Sensing*, 6(3), 1827–1844. [DOI: 10.3390/rs6031827](https://doi.org/10.3390/rs6031827)  
  *Implemented in:* `calculate_burn_severity`. Relativized Burn Ratio (RBR) improves accuracy in areas with sparse pre-fire vegetation.

---

## 5. Tropospheric Atmospheric Emissions & Air Quality

- **Veefkind, J. P., Aben, I., McMullan, K., Förster, H., de Vries, J., Otter, G., Claas, J., Eskes, H. J., de Haan, J. F., Kleipool, Q., van Weele, M., Hasekamp, O., Hoogeveen, R., Landgraf, J., Snel, R., Tol, P., Ingmann, P., Voors, R., Kruizinga, B., Vink, R., Visser, H., & Levelt, P. F. (2012).** TROPOMI on the ESA Sentinel-5 Precursor: A GMES mission for global observations of the atmospheric composition for climate, air quality and ozone layer applications. *Remote Sensing of Environment*, 120, 70–83. [DOI: 10.1016/j.rse.2011.09.027](https://doi.org/10.1016/j.rse.2011.09.027)  
  *Implemented in:* `monitor_atmospheric_emissions`. Mission overview, instrument specification, and optical DOAS performance.
- **van Geffen, J., Boersma, K. F., Eskes, H., Sneep, M., ter Linden, M., Zara, M., & Veefkind, J. P. (2020).** S5P TROPOMI NO2 slant column retrieval: Method, stability, uncertainties and comparisons with OMI. *Atmospheric Measurement Techniques*, 13(3), 1315–1335. [DOI: 10.5194/amt-13-1315-2020](https://doi.org/10.5194/amt-13-1315-2020)  
  *Implemented in:* `monitor_atmospheric_emissions`. Operational algorithm description for TROPOMI NO2 slant and vertical tropospheric column densities.

---

## 6. Surface Water Dynamics, Reservoirs & Drought

- **Pekel, J.-F., Cottam, A., Gorelick, N., & Belward, A. S. (2016).** High-resolution mapping of global surface water and its long-term changes. *Nature*, 540(7633), 418–422. [DOI: 10.1038/nature20584](https://doi.org/10.1038/nature20584)  
  *Implemented in:* `analyze_reservoir_drought`. 32-year global Landsat analysis tracking permanent, seasonal, and desiccated water bodies.

---

## 7. Urban Heat Island & Land Surface Temperature (LST)

- **Valor, E., & Caselles, V. (1996).** Mapping land surface emissivity from NDVI: Application to European, African, and South American areas. *Remote Sensing of Environment*, 57(3), 167–184. [DOI: 10.1016/0034-4257(96)00039-9](https://doi.org/10.1016/0034-4257(96)00039-9)  
  *Implemented in:* `analyze_urban_heat_island`. Mathematical formulation of Fractional Vegetation Cover (FVC) and NDVI thresholding for thermal emissivity.
- **Sobrino, J. A., Jiménez-Muñoz, J. C., & Paolini, L. (2004).** Land surface temperature retrieval from LANDSAT TM 5. *Remote Sensing of Environment*, 90(4), 434–440. [DOI: 10.1016/j.rse.2004.02.003](https://doi.org/10.1016/j.rse.2004.02.003)  
  *Implemented in:* `analyze_urban_heat_island`. Calibration constants, atmospheric transmission correction, and single-channel LST inversion.
- **Sobrino, J. A., Jiménez-Muñoz, J. C., Sòria, G., Romaguera, M., Guanter, L., Moreno, J., Plaza, A., & Martínez, P. (2008).** Land surface emissivity retrieval from different VNIR and TIR sensors. *IEEE Transactions on Geoscience and Remote Sensing*, 46(2), 316–327. [DOI: 10.1109/TGRS.2007.904834](https://doi.org/10.1109/TGRS.2007.904834)  
  *Implemented in:* `analyze_urban_heat_island`. Extended multi-sensor emissivity evaluation across varied surface types.
- **Jiménez-Muñoz, J. C., Cristóbal, J., Sobrino, J. A., Sòria, G., Ninyerola, M., & Pons, X. (2009).** Revision of the single-channel algorithm for land surface temperature retrieval from Landsat thermal-infrared data. *IEEE Transactions on Geoscience and Remote Sensing*, 47(1), 339–349. [DOI: 10.1109/TGRS.2008.2007125](https://doi.org/10.1109/TGRS.2008.2007125)  
  *Implemented in:* `analyze_urban_heat_island`. Revised atmospheric function approximations for Landsat TIRS.

---

## 8. Agricultural Crop Phenology Dynamics

- **Jönsson, P., & Eklundh, L. (2004).** TIMESAT—A program for analyzing time-series of satellite sensor data. *Computers & Geosciences*, 30(8), 833–845. [DOI: 10.1016/j.cageo.2004.05.006](https://doi.org/10.1016/j.cageo.2004.05.006)  
  *Implemented in:* `monitor_crop_phenology`. Asymmetric Gaussian, double logistic, and adaptive Savitzky-Golay filtering for SOS/POS/EOS extraction.
- **Zhang, X., Friedl, M. A., Schaaf, C. B., Strahler, A. H., Hodges, J. C. F., Gao, F., Reed, B. C., & Huete, A. (2003).** Monitoring vegetation phenology using MODIS. *Remote Sensing of Environment*, 84(3), 471–475. [DOI: 10.1016/S0034-4257(02)00135-9](https://doi.org/10.1016/S0034-4257(02)00135-9)  
  *Implemented in:* `monitor_crop_phenology`. Curvature extremum extraction of vegetative phenological transitions.

---

## 9. Topographic Geodesy & Radar Hydrology

- **Horn, B. K. P. (1981).** Hill shading and the reflectance map. *Proceedings of the IEEE*, 69(1), 14–47. [DOI: 10.1109/PROC.1981.11918](https://doi.org/10.1109/PROC.1981.11918)  
  *Implemented in:* `get_elevation_profile` (`dem.py`). Finite-difference weighted local terrain gradient calculation for slope and aspect.
- **European Space Agency. (2020).** Copernicus Complex Digital Elevation Model (COP-DEM) Validation Report. *Issue 4.0*, Airbus Defence and Space & ESA. [Official Report PDF](https://spacedata.copernicus.eu/documents/20126/0/Copernicus+DEM+Validation+Report+v4.0.pdf)  
  *Implemented in:* `get_elevation_profile`, `simulate_sea_level_rise`. Gold-standard elevation quality specification for Copernicus DEM GLO-30.
- **Guth, P. L., & Geoffroy, T. M. (2021).** LiDAR point cloud and ICESat-2 evaluation of 1 second global digital elevation models: Copernicus wins. *Transactions in GIS*, 25(5), 2245–2261. [DOI: 10.1111/tgis.12825](https://doi.org/10.1111/tgis.12825)  
  *Implemented in:* `get_elevation_profile`. Independent global geodetic validation proving Copernicus DEM GLO-30 achieves lowest RMSE versus SRTM and NASADEM.
- **Twele, A., Cao, W., Plank, S., & Martinis, S. (2016).** Sentinel-1-based flood mapping: A fully automated processing chain. *International Journal of Remote Sensing*, 37(13), 2990–3004. [DOI: 10.1080/01431161.2016.1192304](https://doi.org/10.1080/01431161.2016.1192304)  
  *Implemented in:* `detect_water_sar`. Automated radiometric calibration, speckle filtering, and backscatter thresholding for flood mapping.
- **Bioresita, F., Puissant, A., Stumpf, A., & Malet, J.-P. (2018).** A method for automatic and rapid mapping of water surfaces from Sentinel-1 imagery. *Remote Sensing*, 10(2), 217. [DOI: 10.3390/rs10020217](https://doi.org/10.3390/rs10020217)  
  *Implemented in:* `detect_water_sar`. Validated dual-pol (VV/VH) backscatter thresholding for rapid open water delineation.
