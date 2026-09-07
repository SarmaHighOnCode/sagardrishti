import { useCallback, useEffect, useState } from "react";
import { MapCanvas } from "../features/map/MapCanvas";
import { Panel, MetricRow } from "../components/Panel";
import { ConfidenceBar, FactorBar } from "../components/ConfidenceBar";
import { StatusStrip } from "../components/StatusStrip";
import { IS_SYNTHETIC, type SlickFeature } from "../lib/fixtures";
import { useDetections, useShips, useSuspects, useTracks } from "../lib/queries";
import type { Suspect } from "../lib/apiTypes";
import {
  formatArea,
  formatBearing,
  formatDecibels,
  formatMMSI,
  formatUTC,
  formatWithInterval,
} from "../lib/format";

/**
 * The shell: 48px icon rail, map canvas, 380px docked analysis panel,
 * 96px timeline. Exactly viewport height — the page never scrolls.
 *
 * Spec: docs/DESIGN_SYSTEM.md §4.2
 *
 * Data flows through TanStack Query hooks (lib/queries.ts) rather than
 * lib/fixtures.ts directly. The fixture MODULE still exists — its
 * constants define the demo's identifiers and are read by the server's
 * fixtures too (see services/api/app/fixtures.py's own comment on this)
 * — but the component tree no longer imports SAMPLE_* arrays itself.
 */
export function Shell() {
  const detections = useDetections();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Default to the first detection once the list resolves, mirroring the
  // old `useState(SAMPLE_SLICKS[0])` default — but data-driven, so it
  // works whichever detection happens to come back first.
  useEffect(() => {
    if (selectedId === null && detections.data && detections.data.length > 0) {
      setSelectedId(detections.data[0].id);
    }
  }, [selectedId, detections.data]);

  const tracks = useTracks(selectedId ?? undefined);
  const ships = useShips();
  const suspects = useSuspects(selectedId ?? undefined);

  const onSelectSlick = useCallback((s: SlickFeature) => setSelectedId(s.id), []);

  const selected = detections.data?.find((d) => d.id === selectedId) ?? null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <TopBar />
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <LeftRail />
        <main style={{ flex: 1, position: "relative", minWidth: 0 }}>
          <MapCanvas
            slicks={detections.data ?? []}
            tracks={tracks.data ?? []}
            ships={ships.data ?? []}
            onSelectSlick={onSelectSlick}
          />
          <MapLegend />
        </main>
        <AnalysisPanel
          detections={detections}
          selected={selected}
          suspects={suspects.data}
          suspectsLoading={suspects.isLoading}
          suspectsError={suspects.error}
        />
      </div>
      <Timeline />
    </div>
  );
}

function TopBar() {
  return (
    <header
      style={{
        height: "var(--panel-header-h)",
        background: "var(--black)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        gap: "var(--sp-5)",
        padding: "0 var(--sp-5)",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          color: "var(--text-heading)",
        }}
      >
        ▪ SAGARDRISHTI
      </span>
      <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
        S1C_IW_GRDH_1SDV_20260525T064012 ▾
      </span>
      <span style={{ flex: 1 }} />
      {IS_SYNTHETIC && (
        <span
          className="mono"
          style={{
            fontSize: 10,
            color: "var(--orange4)",
            border: "1px solid var(--orange2)",
            borderRadius: "var(--radius)",
            padding: "1px 6px",
            letterSpacing: "0.06em",
          }}
        >
          SYNTHETIC
        </span>
      )}
      <span className="mono" style={{ fontSize: 11, color: "var(--text-label)" }}>
        {formatUTC(new Date())}
      </span>
    </header>
  );
}

const RAIL_ITEMS = [
  { icon: "◎", label: "Detections" },
  { icon: "◈", label: "Drift" },
  { icon: "⚑", label: "Suspects" },
  { icon: "⬢", label: "Dark vessels" },
  { icon: "▤", label: "Evidence" },
];

function LeftRail() {
  const [active, setActive] = useState(0);
  return (
    <nav
      style={{
        width: "var(--rail-w)",
        background: "var(--bg-panel)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: "var(--sp-4)",
        gap: "var(--sp-2)",
        flexShrink: 0,
      }}
    >
      {RAIL_ITEMS.map((item, i) => (
        <button
          key={item.label}
          title={item.label}
          onClick={() => setActive(i)}
          style={{
            width: 32,
            height: 32,
            border: "none",
            borderRadius: "var(--radius)",
            cursor: "pointer",
            fontSize: 14,
            background: i === active ? "var(--fill-active)" : "transparent",
            color: i === active ? "var(--blue4)" : "var(--text-muted)",
            transition: `background var(--dur-hover) ease-out`,
          }}
        >
          {item.icon}
        </button>
      ))}
    </nav>
  );
}

/** Every layer has a legend. A heatmap without a scale is decoration. */
function MapLegend() {
  const items = [
    { c: "var(--slick-confirmed)", t: "Confirmed slick" },
    { c: "var(--slick-rejected)", t: "Rejected candidate" },
    { c: "var(--vessel-suspect)", t: "Suspect track" },
    { c: "var(--vessel-ais)", t: "AIS vessel" },
    { c: "var(--vessel-dark)", t: "Dark vessel" },
  ];
  return (
    <div
      style={{
        position: "absolute",
        left: "var(--sp-5)",
        top: "var(--sp-5)",
        background: "var(--bg-panel)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "var(--sp-4) var(--sp-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-3)",
      }}
    >
      {items.map((i) => (
        <div key={i.t} style={{ display: "flex", alignItems: "center", gap: "var(--sp-4)" }}>
          <span
            style={{
              width: 10,
              height: 10,
              background: i.c,
              borderRadius: "var(--radius)",
              flexShrink: 0,
            }}
          />
          <span style={{ fontSize: 11, color: "var(--text-body)" }}>{i.t}</span>
        </div>
      ))}
    </div>
  );
}

/**
 * A one-line status row for a query that hasn't resolved yet, or failed.
 *
 * Never falls through to an empty panel while loading — an empty
 * Suspects panel would imply zero suspects exist, which is the same
 * "empty state that looks like data" problem the API client's
 * NotImplementedError handling exists to avoid for 501s. Here the cause
 * is different (still fetching, or the network failed) but the
 * obligation is the same: say what's actually happening.
 */
function QueryStatusRow({ loading, error }: { loading: boolean; error: unknown }) {
  if (loading) {
    return (
      <div style={{ fontSize: 12, color: "var(--text-label)", padding: "var(--sp-3) 0" }}>
        Loading…
      </div>
    );
  }
  if (error) {
    const message = error instanceof Error ? error.message : "Request failed";
    return (
      <div style={{ fontSize: 12, color: "var(--red4)", padding: "var(--sp-3) 0" }}>
        {message}
      </div>
    );
  }
  return null;
}

function AnalysisPanel({
  detections,
  selected,
  suspects,
  suspectsLoading,
  suspectsError,
}: {
  detections: { isLoading: boolean; error: unknown };
  selected: SlickFeature | null;
  suspects: Suspect[] | undefined;
  suspectsLoading: boolean;
  suspectsError: unknown;
}) {
  const rejected = selected?.classification === "look_alike";
  const topSuspect = suspects?.[0];

  return (
    <aside
      style={{
        width: "var(--panel-w)",
        background: "var(--bg-app)",
        borderLeft: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        minHeight: 0,
      }}
    >
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "var(--sp-5)",
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-5)",
        }}
      >
        <Panel
          label="Detection"
          badge={selected ? (rejected ? "REJECTED" : "CONFIRMED") : undefined}
          badgeTone={rejected ? "caution" : "alert"}
        >
          {!selected ? (
            <QueryStatusRow loading={detections.isLoading} error={detections.error} />
          ) : (
            <>
              <MetricRow label="area" value={formatArea(selected.areaKm2)} />
              <MetricRow label="bearing" value={formatBearing(selected.bearingDeg)} />
              <MetricRow label="damping" value={formatDecibels(selected.dampingDb)} />
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  height: "var(--row-h)",
                }}
              >
                <span style={{ color: "var(--text-label)", fontSize: 12 }}>confidence</span>
                <ConfidenceBar value={selected.confidence} />
              </div>
            </>
          )}
        </Panel>

        {/* The 1:50 demo beat — say exactly WHY a candidate was demoted. */}
        {selected && rejected && (
          <Panel label="Why this was rejected" badge="LOOK-ALIKE" badgeTone="caution">
            <div className="mono" style={{ fontSize: 12, marginBottom: "var(--sp-4)" }}>
              <span style={{ color: "var(--text-disabled)", textDecoration: "line-through" }}>
                {selected.confidenceRaw.toFixed(2)}
              </span>
              <span style={{ color: "var(--text-label)" }}> → </span>
              <span style={{ color: "var(--orange4)" }}>{selected.confidence.toFixed(2)}</span>
            </div>
            {selected.penalties.map((p) => (
              <div
                key={p.check}
                style={{
                  display: "flex",
                  gap: "var(--sp-4)",
                  fontSize: 12,
                  color: "var(--text-body)",
                  padding: "3px 0",
                }}
              >
                <span style={{ color: "var(--orange4)", flexShrink: 0 }}>⚠</span>
                <span>{p.reason}</span>
              </div>
            ))}
          </Panel>
        )}

        <Panel label="Suspects" badge={suspects ? `${suspects.length} of 214` : undefined}>
          {suspects === undefined ? (
            <QueryStatusRow loading={suspectsLoading} error={suspectsError} />
          ) : (
            suspects.map((s) => (
              <div
                key={s.mmsi}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--sp-4)",
                  height: "var(--row-h-default)",
                }}
              >
                <span className="mono" style={{ fontSize: 12, color: "var(--text-label)" }}>
                  {s.rank}
                </span>
                <span className="mono" style={{ fontSize: 12, flex: 1 }}>
                  {formatMMSI(s.mmsi)}
                </span>
                <ConfidenceBar value={s.posterior} width={60} />
              </div>
            ))
          )}
        </Panel>

        {/* The 6:30 demo beat — the actual arithmetic, not a black box.
            Factors render straight from the API response, including
            negative (exculpatory) contributions — never filtered. */}
        {topSuspect && (
          <Panel
            label="Top suspect · why"
            badge={topSuspect.posterior.toFixed(2)}
            badgeTone="alert"
          >
            <div style={{ marginBottom: "var(--sp-5)" }}>
              <div style={{ fontSize: 12, color: "var(--text-primary)" }}>
                {topSuspect.vessel_name}
              </div>
              <div className="mono" style={{ fontSize: 11, color: "var(--text-label)" }}>
                MMSI {formatMMSI(topSuspect.mmsi)} · {topSuspect.vessel_type}
              </div>
            </div>
            {topSuspect.factors.map((f) => (
              <FactorBar
                key={f.name}
                name={f.name.replace(/_/g, " ")}
                contribution={f.contribution}
                confidence={f.confidence}
              />
            ))}
            <div
              style={{
                marginTop: "var(--sp-5)",
                paddingTop: "var(--sp-4)",
                borderTop: "1px solid var(--border)",
              }}
            >
              <MetricRow label="inferred release" value={topSuspect.inferred_release_utc} />
              <MetricRow
                label="slick age"
                value={formatWithInterval(
                  topSuspect.slick_age_hours,
                  topSuspect.slick_age_ci,
                  "h",
                )}
              />
            </div>
          </Panel>
        )}
      </div>

      <StatusStrip
        synthetic={IS_SYNTHETIC}
        sceneId="S1C_IW_GRDH_1SDV_20260525T064012"
        sceneHash="a3f9c2e1b7d4a8f012"
        modelName="segformer-b2 @ 40m/px"
        modelHash="7d41b8a9c2e5f731"
        forcing="CMEMS PHY_001_024 · ERA5 · GEBCO 2024"
      />
    </aside>
  );
}

/**
 * One clock drives every layer. This is a time-series product; hiding time
 * in a modal would be a category error.
 */
function Timeline() {
  const [t, setT] = useState(60);
  return (
    <footer
      style={{
        height: "var(--timeline-h)",
        background: "var(--bg-panel)",
        borderTop: "1px solid var(--border)",
        padding: "var(--sp-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-4)",
        flexShrink: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-5)" }}>
        <span className="panel-label">Timeline</span>
        <span style={{ display: "flex", gap: "var(--sp-2)" }}>
          {["◀◀", "▶", "▶▶"].map((s) => (
            <button
              key={s}
              style={{
                background: "var(--bg-raised)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                color: "var(--text-body)",
                fontSize: 11,
                width: 28,
                height: 22,
                cursor: "pointer",
              }}
            >
              {s}
            </button>
          ))}
        </span>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
          T_sar − {((100 - t) * 0.24).toFixed(1)} h
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={t}
        onChange={(e) => setT(Number(e.target.value))}
        style={{ width: "100%", accentColor: "var(--blue3)" }}
      />
      <div
        className="mono"
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10,
          color: "var(--text-label)",
        }}
      >
        <span>T−24h</span>
        <span style={{ color: "var(--blue4)" }}>T_sar</span>
        <span>T+48h</span>
      </div>
    </footer>
  );
}
