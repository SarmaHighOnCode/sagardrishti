import { useState, type ReactNode } from "react";

/**
 * The standard panel. Every panel in the console follows this structure,
 * without exception: uppercase label left, optional count/status badge
 * right, collapse chevron far right.
 *
 * The badge is where "7 of 214" lives — the count that tells the story.
 *
 * Spec: docs/DESIGN_SYSTEM.md §4.3
 */
export function Panel({
  label,
  badge,
  badgeTone = "neutral",
  children,
  defaultOpen = true,
  scroll = false,
}: {
  label: string;
  badge?: string;
  badgeTone?: "neutral" | "alert" | "caution" | "ok";
  children: ReactNode;
  defaultOpen?: boolean;
  scroll?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const badgeColor = {
    neutral: "var(--text-label)",
    alert: "var(--red4)",
    caution: "var(--orange4)",
    ok: "var(--green4)",
  }[badgeTone];

  return (
    <section
      style={{
        background: "var(--bg-panel)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
      }}
    >
      <header
        onClick={() => setOpen((o) => !o)}
        style={{
          height: "var(--panel-header-h)",
          background: "var(--bg-raised)",
          borderBottom: open ? "1px solid var(--border)" : "none",
          display: "flex",
          alignItems: "center",
          gap: "var(--sp-4)",
          padding: `0 var(--sp-5)`,
          cursor: "pointer",
          userSelect: "none",
        }}
      >
        <span className="panel-label" style={{ flex: 1 }}>
          {label}
        </span>
        {badge && (
          <span className="mono" style={{ fontSize: 11, color: badgeColor }}>
            {badge}
          </span>
        )}
        <span
          style={{
            color: "var(--text-label)",
            fontSize: 10,
            transform: open ? "rotate(0deg)" : "rotate(-90deg)",
            transition: `transform var(--dur-panel) var(--ease-panel)`,
          }}
        >
          ▾
        </span>
      </header>
      {open && (
        <div
          style={{
            padding: "var(--panel-pad)",
            maxHeight: scroll ? 280 : undefined,
            overflowY: scroll ? "auto" : undefined,
          }}
        >
          {children}
        </div>
      )}
    </section>
  );
}

/** A label/value row. Values are monospace and right-aligned so they stack. */
export function MetricRow({
  label,
  value,
  mono = true,
  tone,
}: {
  label: string;
  value: string;
  mono?: boolean;
  tone?: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        height: "var(--row-h)",
        gap: "var(--sp-4)",
      }}
    >
      <span style={{ color: "var(--text-label)", fontSize: 12 }}>{label}</span>
      <span
        className={mono ? "mono" : "tabular"}
        style={{ fontSize: 12, color: tone ?? "var(--text-primary)" }}
      >
        {value}
      </span>
    </div>
  );
}
