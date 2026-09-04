# `tiler` — TiTiler

Serves Cloud-Optimized GeoTIFFs as XYZ tiles to MapLibre.

## Why not write one

TiTiler exists, is maintained, and does exactly this. Writing a tile server would be ego rather than engineering — noted in [`ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) section 11.

## Serves

| Layer | Source |
|---|---|
| SAR backscatter | M1 COG, greyscale, adjustable dB stretch |
| Origin probability field | M5 hindcast COG, turquoise ramp |
| Forecast extent | M5 forward COG, cerulean ramp |
| Shoreline impact | Vermilion ramp |

Colour ramps come from [`DESIGN_SYSTEM.md`](../../docs/DESIGN_SYSTEM.md) section 2.3. **Backward is violet, forward is cerulean** — consistently, across map, charts and PDF.

## Rasters are not JSON

Probability fields are served as COG, never as JSON arrays. A raster in JSON is a mistake worth avoiding once.

## Offline

Reads from the local object store. **No remote basemap** — MapLibre vector tiles are bundled locally, which is a chief reason MapLibre was chosen. See [`OFFLINE_MODE.md`](../../docs/OFFLINE_MODE.md).
