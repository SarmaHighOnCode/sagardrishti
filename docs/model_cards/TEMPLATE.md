# Model Card — `<model-name>` v`<version>`

## Identity

| | |
|---|---|
| Name | |
| Version | |
| Weights SHA-256 | |
| Trained | |
| Git commit | |
| Author | |

## Architecture

- **Backbone:**
- **Head:**
- **Parameters:**
- **Input:** `<H x W x C>`, channels = `<VV, VH>`

## Data

| Dataset | Split | N | **GSD after resample** | Notes |
|---|---|---|---|---|
| | train | | 40 m/px | |
| | val | | 40 m/px | |
| | test | | 40 m/px | |

**Normalisation:** *(state exactly, and confirm it is identical at inference)*

**Class balance:** *(oil is typically <1% of pixels — state the actual figure)*

## Training

| | |
|---|---|
| Optimiser | |
| LR / schedule | |
| Epochs | |
| Batch size | |
| Loss | |
| Augmentations | |
| Hardware | |
| Seed(s) | |
| Wall time | |

## Performance

| Split | mIoU | Oil IoU | F1 | Precision | Recall |
|---|---|---|---|---|---|
| val | | | | | |
| test | | | | | |

*Mean ± std across `<n>` seeds.*

## Cross-domain — required

| Trained on | Tested on | mIoU | **Drop** |
|---|---|---|---|
| | | | |

## Failure modes — required

| Look-alike cluster | FPR | Notes |
|---|---|---|
| Low wind | | |
| Biogenic film | | |
| Internal waves | | |
| Rain cells | | |

**Worst cluster:** *(name it — this goes on the honest-limits slide)*

## Intended use

**For:**

**Not for:**

## Limitations

- Wind conditions outside 2–12 m/s:
- Sensor generalisation:
- Geographic generalisation:
- Known biases:
