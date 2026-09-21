# DESIGN.md: eo-mcp Design System

> **Canonical Visual Grammar & Design System Specification**  
> **Brand:** eo-mcp (Open Source Planetary Earth Observation Model Context Protocol)  
> **Domain:** https://eo-mcp.github.io  
> **Repository:** https://github.com/eo-mcp/eo-mcp  
> **Classification:** Developer Tooling, Spatial Data Infrastructure, Open Source Protocols  

---

## 1. Brand Ethos & Visual Philosophy

eo-mcp bridges planetary remote sensing archives (Copernicus Sentinel, USGS Landsat, NASA FIRMS, Open AIS) directly into AI agent runtimes (Claude, Cursor, Antigravity, Python).

The visual language reflects **authentic engineering rigor**: inspired by physical engineering calculation pads, telemetry terminals, and scientific remote sensing data viewports. It rejects glossy consumer software tropes in favor of clean mathematical grids, high-contrast typography, and full-resolution satellite imagery.

### The Visual-First Invariant
Every visual presentation card, documentation graphic, and social asset must be **image-first**:
- The remote sensing raster (SAR radar, thermal infrared, multispectral NDVI, flood backscatter) commands **50% to 70% of the canvas**.
- Text is concise, high-contrast, and contextualized within technical telemetry bars.
- Zero decorative fluff, zero synthetic HUD target circles over planetary data, and strictly **zero em dashes**.

### Absolute Ban on Generative AI Imagery (The "No Nano Banana" Invariant)
In `eo-mcp`, all generative AI, diffusion, or text-to-image synthesis models (including **Nano Banana**, Imagen, Midjourney, DALL-E, Stable Diffusion, and prompt-based art generators) are **STRICTLY OFF LIMITS AND PROHIBITED**:
- **Why**: Earth Observation is empirical physical measurement. Generative AI tools hallucinate fictitious shorelines, fake thermal pixels, unphysical SAR backscatter, and invented topography, which destroys scientific credibility.
- **Mandate**: 100% of maps, rasters, and visual outputs must be **script-driven and deterministic**, generated directly from real spatial data arrays (NumPy, GeoTIFF, GeoJSON, and Leaflet/MapLibre HTML) via `eo_mcp.utils.visualizer` or programmatic Python GIS engines.

---

## 2. Color Palette & Design Tokens

### Light Surface (Documentation & Primary Canvas)
- **Canvas Paper:** `#fafafa` (`--paper`)
- **Warm Paper:** `#f5f5f5` (`--paper-warm`)
- **Card Bone:** `#ffffff` (`--bone`)
- **Border Stroke:** `#e2e2e2` (`--line`)
- **Soft Line:** `#eeeeee` (`--line-soft`)
- **Grid Technical Quad (80px):** `rgba(34, 197, 94, 0.09)`
- **Grid Subdivisions (16px):** `rgba(20, 20, 19, 0.035)`

### Primary Accents (Earth Observation Emerald)
- **Primary Emerald:** `#22c55e` (`--accent`)
- **Deep Forest Green:** `#15803d` (`--accent-dark`)
- **Bright Mint:** `#10b981` (`--accent-bright`)
- **Soft Mint Tint:** `#bbf7d0` (`--accent-soft`)
- **Subtle Mint Wash:** `#f0fdf4` (`--accent-bg`)

### Dark Viewport & Terminal Canvas
- **Deep Space Black:** `#030712`
- **Terminal Glass Surface:** `rgba(10, 15, 29, 0.92)`
- **HUD Pill Glass:** `rgba(15, 23, 42, 0.80)`
- **Thermal Alert Orange:** `#f97316` / `#ea580c`
- **Radar Cyan Accent:** `#06b6d4` / `#0284c7`
- **Wildfire Crimson:** `#ef4444` / `#dc2626`

### Typography Colors
- **Ink Primary:** `#1f1f1f` (`--ink`)
- **Ink Soft:** `#404040` (`--ink-soft`)
- **Ink Muted:** `#737373` (`--ink-mute`)
- **Ink Faint:** `#a3a3a3` (`--ink-faint`)
- **Terminal Text:** `#f1f5f9`

---

## 3. Typography Hierarchy

| Role | Font Family | Weight | Size (Desktop) | Tracking / Spacing | Usage |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Hero Title** | `Albert Sans` | 900 | 52px – 56px | `-0.035em` | Primary punchy headlines (e.g., "Cities are baking.") |
| **Section Header** | `Albert Sans` | 800 | 28px – 32px | `-0.02em` | Feature headings and section passport titles |
| **Kicker** | `JetBrains Mono` | 700 | 12px – 13px | `0.14em` uppercase | Context tags above titles (e.g., "LANDSAT-9 TIRS-2") |
| **Telemetry / Code** | `JetBrains Mono` | 600 | 14px – 15px | `0.00em` | CLI prompts, tool calling JSON, coordinates |
| **Metadata Labels** | `JetBrains Mono` | 700 | 10px – 11px | `0.10em` uppercase | Side rail coordinates, status badges, HUD pills |
| **Body Copy** | `Albert Sans` | 500 / 600 | 15px – 16px | `-0.01em` | Explanatory technical descriptions and documentation |

---

## 4. Layout Architecture & Spatial Grid

- **Canvas Aspect Ratio:** 1:1 Square (1200 x 1200 px for social assets); 16:9 Landscape for documentation banners.
- **Side Rails:** Vertical 38px coordinates rails left and right featuring rotated uppercase technical metadata.
- **Padding:** 44px top/bottom, 56px left/right.
- **Corner Radii:**
  - Buttons & Badges: `9999px` (Pill format)
  - Showcase Stage: `20px`
  - Inner Terminal / Cards: `12px – 14px`
- **Elevation Shadows:**
  - Soft Card: `0 2px 8px rgba(0, 0, 0, 0.04)`
  - Window Stage: `0 24px 60px -20px rgba(0, 0, 0, 0.12), 0 10px 30px rgba(0, 0, 0, 0.06)`

---

## 5. Key Component Archetypes

### 1. Top Navigation Pill (`.nav-pill`)
- Floating pill container with `backdrop-filter: blur(16px)`.
- Features official circular or square icon badge, `eo-mcp v0.4.0` version tag, and pulsing live status badge (`THERMAL INFRARED SENSING`, `MARITIME DOMAIN RADAR`).

### 2. Showcase Stage (`.showcase-stage`)
- macOS-inspired title bar with red, yellow, green window controls (`11px` diameter).
- Center metadata displaying sensor archive (`USGS LANDSAT-9 TIRS-2 // 100M GROUND RESOLUTION`).
- Right pill tag displaying spectral calibration method (`BAND 10 RADIANCE + NDVI EMISSIVITY`).
- Viewport interior commanding 60% of the canvas with a genuine satellite raster.
- Top HUD pills displaying live calculated metrics (`DELTA: +14.2°C ASPHALT VS CANOPY`).
- Integrated bottom terminal bar displaying the exact agent tool execution call:
  `> calculate_lst(collection="landsat-9-tirs", emissivity="ndvi")` with alert status badge.

### 3. Feature Chips Row (`.chips-row`)
- Three equal-width cards displaying numbered technical proof points (`01 TIRS-2 Band 10 Radiance`, `02 Planck Inversion & NDVI`, `03 Zero API Keys / Pure STAC`).

### 4. Footer CTA (`.footer-row`)
- Left: Declarative platform tagline.
- Right: Dark pill CTA button (`eo-mcp.github.io`) with brand logo icon.

---

## 6. Social Asset Invariants ("Do's & Don'ts")

- **DO:** Ensure genuine satellite raster imagery commands 50% to 70% of the graphic canvas.
- **DO:** Anchor every floating metric with a small uppercase label above.
- **DO:** Use direct copulatives ("is", "are").
- **DO NOT:** Clutter cards with multi-paragraph text blocks or dense tables.
- **DO NOT:** Draw synthetic target rings or faux HUD circles over genuine satellite topography.
- **DO NOT:** Use em dashes (Unicode U+2014, `-`).
