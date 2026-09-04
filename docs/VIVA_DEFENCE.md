# Viva Defence

Anticipated jury questions with rigorous answers. **Whoever presents must be able to answer the starred questions without hesitation.**

A jury is not testing whether your system is perfect. They are testing whether you understand what you built, and whether you know where it breaks. Confident knowledge of your own limitations scores higher than a flawless demo you cannot explain.

---

## Ground rules

1. **Never bluff.** "We didn't implement that, and here's why" beats a fabricated answer every time. Juries include specialists; they will know.
2. **Volunteer limitations before they are found.** The honest-limits slide at 9:15 exists precisely for this.
3. **Answer the question actually asked.** Do not pivot to a rehearsed adjacent answer — it is obvious and it reads as evasion.
4. **"We rank, we never accuse."** If a question presumes we identify culprits, correct the premise politely.

---

## A. Physics and remote sensing

**★ Why is oil dark in SAR?**

Bragg scattering. C-band radar at ~5.6 cm resonates with wind-generated capillary and short gravity waves. Oil lowers surface tension and dampens those waves, so fewer Bragg scatterers return energy and backscatter drops. We are not seeing oil — we are seeing the absence of roughness.

**★ How do you distinguish oil from a low-wind area or an algal bloom?**

Not from pixels alone; the information is not there. A thin sheen and a wind shadow can be genuinely indistinguishable in σ⁰. We gate on auxiliary context: modelled wind against the 2–12 m/s detection window, chlorophyll-a for biogenic films, SST for upwelling, bathymetry for internal waves, precipitation for rain cells, plus our own archive of recurring dark formations at that location. We also use edge sharpness — mineral oil has a sharper boundary than biogenic film. Every applied penalty is logged and shown to the analyst with its reason.

**What if the wind is outside your window?**

The detection is flagged and down-weighted automatically, with the wind speed shown. Below 2–3 m/s the sea is glassy and false positives explode; above 7–12 m/s the slick is physically broken up and mixed down. We would rather report "conditions unsuitable" than a confident wrong answer — and we show the analyst which it is.

**Why 40 m/px when Sentinel-1 gives you 10 m?**

Two reasons. Slicks are hundreds of metres across, so 40 m/px leaves tens to hundreds of pixels per slick — ample. And the public training datasets are built at *different* resolutions; mixing them fails silently, with a healthy-looking loss curve and collapsed field performance. Fixing GSD across training and inference eliminates that. It also cuts a full scene from 420 to 26 megapixels, which is what makes live inference possible.

**Why not use VH more?**

VH sits close to the instrument noise floor over calm water, so it carries little usable signal. We feed both channels because it costs one input channel and VH being near noise-limited *inside* a slick is a weak discriminator — but the detection is fundamentally VV.

---

## B. The hard ones

**★ How do you know the slick's age?**

We don't measure it — it is not recoverable from a single scene. Contrast correlates with age, but is confounded by wind, incidence angle, oil type and discharge volume, none of which we know. Four unknowns, one observable.

Instead we infer it. In the attribution solve we search over release time; the release time that makes a candidate vessel's forward-drifted plume best match the observed slick *is* the age estimate, with an uncertainty band from the ensemble spread. That is how operational European polluter identification does it, and it turns the PS's "age if feasible" into a designed output rather than a gap.

**★ Why not just find the nearest ship?**

Because the image may be hours old and the responsible vessel is long gone — at transit speed a ship covers 60–100 nautical miles in six hours while the slick drifts a few kilometres. The nearest vessel is usually an innocent bystander.

We ran that as an explicit baseline — [show ablation 2] — and it degrades sharply with slick age, which is exactly its failure mode. We instead simulate forward drift from every vessel's track across the plausible age window.

**★ Your currents are 8 km and your slick is 40 m. Isn't that broken?**

It is the dominant term in our error budget and we quantify it rather than hide it. Sub-mesoscale eddies between 100 m and 10 km visibly control slick shape and are entirely unresolved by the best free global product. That is a data-availability limit, not an engineering failure.

It is why we run 100-member ensembles with perturbed forcing, why we output probability fields rather than point estimates, and why the backward cone visibly widens with time in our interface. INCOIS's regional high-resolution setup measurably outperforms the global product for the west coast — ingesting it is our first operational integration step.

**★ How accurate is your attribution?**

Top-3 accuracy of X% on held-out synthetic scenarios with known culprits — and that number is synthetic, labelled as such everywhere.

We report top-3 rather than top-1 deliberately. Narrowing 214 vessels to 3 for an ICG investigator is the operational win; the difference between rank 1 and rank 2 matters far less than the difference between 3 candidates and 200. We do not claim to identify a guilty vessel.

**★ Why synthetic AIS? Isn't that cheating?**

The problem statement explicitly permits it. Bulk historical AIS for Indian waters is not publicly available — the free sources are live-only, terrestrial-only, and offer no replay, and the commercial market consolidated further through 2026.

So we do three things. We validate the attribution method on real AIS from NOAA's US dataset, where independent tracks exist. We demonstrate on Indian waters with a generator calibrated to lane geometry we recorded live from AISStream over three months. And we label every synthetic result as synthetic. The data gap is itself part of the capability gap this problem statement exists to close.

**Then how do you know your attribution works at all?**

We separate two claims. That the *method* is sound: validated on real messy tracks with real gaps, and grounded in published operational practice. That it achieves a specific *accuracy*: measured on synthetic ground truth, labelled as such. Anyone claiming measured attribution accuracy on real routine-discharge data does not have ground truth either — nobody does at scale, because it requires knowing who actually discharged.

---

## C. Method and architecture

**Why OpenDrift and not GNOME, which is what INCOIS uses?**

OpenDrift is peer-reviewed, actively maintained, has a Python API that embeds cleanly, and supports backward runs natively with a negative timestep. GNOME is excellent and operationally proven, but harder to embed programmatically. Since interoperability with INCOIS is our stated integration path, GNOME compatibility is on the roadmap rather than dismissed.

**Isn't your per-vessel drift simulation computationally impossible?**

It would be if done naively — 50 vessels × 96 release times × 100 ensemble members is 480,000 simulations. But particles are independent and OpenDrift supports staggered seed times, so every particle from every vessel at every release time goes into **one** simulation, each tagged with its origin. Scoring is a group-by afterwards. That is exact, not an approximation, and it is the implementation detail that makes the whole approach viable.

**★ Isn't an AIS gap just a broken transponder? Won't you accuse innocent fishing boats?**

That is the right question, and it is why the gap factor is not "a gap exists near the spill."

Gaps are overwhelmingly innocent. Cheap, old or misconfigured transponders drop out constantly — everywhere, always, not just near this spill. Terrestrial AIS only reaches about 40 to 75 nautical miles, so beyond that a gap is radio physics, not evasion. And there is ordinary bad data: MMSI zero, reused MMSIs, GPS stuck at (0,0), impossible speed jumps.

We do three things about it. First, a data quality pre-filter runs before any scoring and excludes structurally invalid records — and critically, those exclusions never move a score in either direction, so a vessel is never a suspect *because* its equipment is broken. Second, we compare each gap against **that vessel's own baseline** behaviour over prior weeks, so a boat that routinely goes quiet for hours scores low, while a vessel that has reported like clockwork for months and then has one gap at the inferred release time scores high. Third, we discount gaps in low-coverage water using a distance-to-coast proxy.

And the factor is one of nine inputs against a strongly negative intercept — it cannot produce a suspect on its own. **We would rather miss a detection than accuse the wrong operator.**

**Why not a proper radio propagation model for coverage?**

Because the accuracy it would buy is small next to what distance-to-coast already gives us, and it would be harder to explain and defend. A simple documented threshold is the right level of sophistication for the decision it supports. We were deliberate about not over-engineering that piece.

**Won't every small unidentified boat show up as a dark vessel?**

We attach a coarse size bucket from the radar cross-section, because **many small craft are legally exempt from carrying AIS** — a fishing boat below the carriage threshold is not an evader. Without that, the dark-vessel list fills with legitimate traffic and stops being useful to a watchkeeper. It is a soft flag for analyst context, never a hard filter, and we claim a size bucket rather than a vessel type because we have no training data for classification and would not want to overclaim.

**Why not deep learning for the attribution scoring?**

We have on the order of tens of labelled attribution events, because ground truth requires knowing who actually discharged. Ten weights on tens of examples is already at the limit of statistical honesty; a network would overfit and report the overfit as accuracy.

More importantly, our user must justify a boarding decision. A log-odds model *is* the explanation — the factor bars in our interface are the actual terms of the computation, not a post-hoc method approximating a black box. We use deep learning where we have thousands of labelled examples, which is the segmentation stage.

**★ Why didn't you use super-resolution? The problem statement links a video about it.**

Super-resolution is a cosmetic enhancement that does not add information — the linked video states that itself, explicitly, and notes it does not change ground sampling distance.

For a forensic system, introducing generated pixels into evidence would undermine the chain of custody. Our detection basis is that oil dampens waves and lowers calibrated backscatter; an SR network outputs pixels learned from a training distribution, not measured returned energy. We would be partly classifying the SR model's priors. We deliberately did not use it, and fixed GSD at 40 m/px instead. It is recorded as a formal architecture decision.

**Why two languages?**

The AIS recorder is a data-loss-critical daemon with a three-month uptime requirement against a feed with no replay — every unpersisted message is permanently lost. The science pipeline is a GPU-bound research stack. Those are different engineering problems. Go for the AIS data plane, Python for the science, and the boundary is the database so neither can destabilise the other. The synthetic generator shares the Go codec with the recorder, which is what makes "real and synthetic use the same ingest path" structurally true rather than aspirational.

---

## D. Positioning

**★ How is this different from EMSA CleanSeaNet?**

CleanSeaNet detects and alerts with a human analyst in the loop, and it correlates with AIS only where a ship happens to be adjacent — so it fails on orphan spills, where the vessel has already left. We automate attribution for exactly that orphan case using forward drift from all traffic across the plausible age window. And CleanSeaNet does not cover Indian waters.

**How is this different from INCOIS OOSA?**

OOSA v5.0 is operational and good at what it does — forward trajectory prediction with advanced GIS. But it is forward-only, and a human must tell it where the spill is. No detection, no attribution. We are not competing with INCOIS; we close the two gaps on either side of them, and their high-resolution regional currents are our stated first upgrade.

**What is genuinely novel here?**

Not the individual components — segmentation, Lagrangian drift and AIS analysis all exist. What does not exist for Indian waters is the closed loop: pixel → slick → probabilistic origin → ranked, explained, provenance-tracked vessel candidates, automatically. Plus two things rare anywhere: the physics/context filter with visible per-penalty reasoning, and an attribution model built to be audited rather than trusted.

**Would this hold up in court?**

We do not claim it proves guilt. It produces a ranked, calibrated, fully explainable investigative lead with a complete provenance record — source product IDs and hashes, model weight hashes, forcing dataset versions, configuration snapshot, timestamps. That is what an investigator needs to justify boarding, inspection and sampling, which is where legal proof actually comes from. The Kerala High Court proceedings against the MSC ELSA 3 and Wan Hai 503 owners are exactly the context where such a record has value.

---

## E. Awkward questions

**★ Did you use AI to write this code?**

Yes, extensively, as does most of the field in 2026. *(Then immediately demonstrate that you understand every architectural decision — that is what the question is actually testing. Have an ADR open.)*

**This looks like four projects. Did you actually build all of it?**

It is four subsystems and we scoped each deliberately. Here is what is fully working, here is what is a demonstrated path rather than a validated capability — NISAR ingest is the clearest example — and here is what we explicitly did not build and why. *(Then show the "what we did not build" table. Scoping discipline is a positive signal.)*

**What happens if I give you a scene you have never seen?**

It runs — and it may perform worse, particularly outside the basins in our training data. That is the cross-domain drop we report explicitly: roughly 10–20 mIoU points moving between basins. The physics filter helps because environmental context generalises better than learned texture. If you have a scene, we can run it now. *(Only say this last sentence if the offline demo genuinely supports it.)*

**Your demo is pre-computed, isn't it?**

The drift ensembles are cached, yes — a full 100-member ensemble takes minutes of CPU and we would rather not spend the demo slot watching a progress bar. Detection runs live, and there is a live-compute button for one small scenario to show the pipeline is real. *(Never claim live computation you are not doing. If caught, everything else becomes suspect.)*

**What is the weakest part of your system?**

*(Answer honestly — a rehearsed non-answer is transparent.)* The drift model, because it is limited by 8 km forcing resolution that we cannot improve without INCOIS data. Second is look-alike rejection on the cluster we do worst on — *[name it]*. Both are measured and on the limits slide.

**Why should NTRO care about this rather than buying a commercial system?**

Commercial maritime domain awareness suites are foreign, closed, expensive, and none of them do automated drift-based attribution for Indian waters. This is an indigenous, auditable pipeline with a clear path to sovereign data — NISAR is a NASA–ISRO mission, and ISRO's own SAR assets are the next step. For a technical intelligence organisation, owning and being able to audit the reasoning matters more than a polished vendor product.

---

## F. If you do not know

Say so, precisely, and offer what you do know:

> "I don't know — that's outside what we validated. What we did measure is *[X]*. If it matters for your assessment I can tell you how we would test it."

**A jury respects this.** Every experienced evaluator has seen students confidently invent an answer, and it is instantly recognisable. One honest "I don't know" costs a fraction of what one fabricated answer costs.
