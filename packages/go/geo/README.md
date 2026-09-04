# `geo`

Geodesic helpers for the Go AIS services.

| Function group | Purpose |
|---|---|
| Distance | Haversine and Vincenty between positions |
| Interpolation | Great-circle interpolation with SOG/COG — **never naive linear** |
| Bounding boxes | AOI containment for subscription filtering |
| **Distance to coast** | Coverage proxy for the AIS gap factor |

## Distance to coast

Backs correction (c) of the AIS gap factor — see [`SCORING_MODEL.md`](../../../docs/SCORING_MODEL.md) section 2.1.

Terrestrial AIS reaches roughly 40–75 nm. Beyond that, a reporting gap is radio physics, not behaviour, and must be discounted rather than treated as evidence.

**Deliberately coarse.** A simplified coastline with a distance threshold, not a propagation model. The extra accuracy is not worth the time and is harder to explain in a viva. Simple, documented and explainable is the right level here.
