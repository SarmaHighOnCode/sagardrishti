# Model Cards

One card per trained model. **A model without a card does not ship**, and its numbers do not go on a slide.

## Why

Two reasons, both practical.

A jury will ask what a model was trained on and how it performs outside that distribution. A card is the prepared answer, written while the facts were fresh rather than reconstructed the night before.

And within the team, a checkpoint whose training data, GSD and normalisation are unrecorded is a checkpoint nobody can safely reuse. Four months of ad-hoc training runs produce a directory of files whose provenance is guesswork unless it is recorded at the time.

## Required sections

Copy [`TEMPLATE.md`](TEMPLATE.md).

| Section | Must state |
|---|---|
| Identity | Name, version, weights SHA-256, training date, git commit |
| Architecture | Backbone, head, parameter count, input shape and channels |
| **Data** | Every dataset, split sizes, **GSD after resampling**, normalisation |
| Training | Optimiser, LR schedule, epochs, batch size, augmentations, hardware, seed |
| Performance | Per-split metrics with variance across seeds |
| **Cross-domain** | Performance on a basin not in training. **Report the drop** |
| **Failure modes** | Which look-alike clusters it fails on. Named, not summarised |
| Intended use | What it is for, and explicitly what it is not for |
| Limitations | Wind conditions, sensor, geography, and the honest caveats |

## Two non-negotiable fields

**Ground sample distance.** Every card states GSD after resampling — 40 m/px. This is the silent failure mode described in [ADR 0002](../adr/0002-fixed-ground-sample-distance.md), and the card is where it becomes checkable.

**Cross-domain performance.** Every card reports metrics on a basin not represented in training. A card showing only in-distribution numbers is incomplete, because in-distribution performance is not the question a jury is asking.

## Registry

| Model | Version | Task | Card | Weights |
|---|---|---|---|---|
| `segformer-b2-oil` | — | 5-class segmentation | *pending* | *pending* |
| `deeplabv3p-r50-oil` | — | Baseline segmentation | *pending* | *pending* |
| `yolo-darkform` | — | Stage A proposals | *pending* | *pending* |
| `cfar-ships` | — | Ship detection (classical, no training) | n/a | n/a |

`cfar-ships` needs no card because it is a classical detector with no learned parameters — which is itself a reason to prefer it where it is adequate.
