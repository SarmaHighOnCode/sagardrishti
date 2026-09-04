import { formatProbability } from "../lib/format";

/**
 * The workhorse component — used for detection confidence and every suspect
 * score, so it appears dozens of times and must be tiny and instantly read.
 *
 * ALWAYS paired with the number. A bar alone is not readable to two
 * significant figures, and an operator needs the figure.
 *
 * Spec: docs/DESIGN_SYSTEM.md §6.1
 */
export function ConfidenceBar({
  value,
  width = 80,
  showValue = true,
}: {
  value: number;
  width?: number;
  showValue?: boolean;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const fill =
    clamped >= 0.7
      ? "var(--red3)"
      : clamped >= 0.4
        ? "var(--orange3)"
        : "var(--gray2)";

  return (
    <span
      style={{ display: "inline-flex", alignItems: "center", gap: "var(--sp-4)" }}
    >
      {showValue && (
        <span className="mono" style={{ fontSize: 12, color: "var(--text-primary)" }}>
          {formatProbability(clamped)}
        </span>
      )}
      <span
        role="meter"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={1}
        style={{
          width,
          height: 6,
          background: "var(--dark-gray4)",
          borderRadius: "var(--radius)",
          overflow: "hidden",
          display: "inline-block",
        }}
      >
        <span
          style={{
            display: "block",
            width: `${clamped * 100}%`,
            height: "100%",
            background: fill,
          }}
        />
      </span>
    </span>
  );
}

/**
 * Per-factor contribution bar for the suspect explanation panel.
 *
 * Positive contributions extend right in red; negative extend LEFT in blue.
 * Every factor is always listed, including those arguing for innocence —
 * hiding exculpatory evidence would destroy the legal-defensibility claim
 * that justifies the evidence dossier existing at all.
 *
 * Spec: docs/DESIGN_SYSTEM.md §6.2, docs/SCORING_MODEL.md §7
 */
export function FactorBar({
  name,
  contribution,
  max = 2.5,
  confidence = "high",
}: {
  name: string;
  contribution: number;
  max?: number;
  confidence?: "high" | "medium" | "low";
}) {
  const frac = Math.min(Math.abs(contribution) / max, 1);
  const positive = contribution >= 0;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--sp-4)",
        height: "var(--row-h)",
        opacity: confidence === "low" ? 0.55 : 1,
      }}
      title={confidence === "low" ? "low confidence — thin supporting evidence" : undefined}
    >
      <span style={{ flex: 1, fontSize: 12, color: "var(--text-body)" }}>
        {name}
        {confidence === "low" && (
          <span style={{ color: "var(--text-label)", fontSize: 10 }}> (low conf.)</span>
        )}
      </span>
      <span
        className="mono"
        style={{
          fontSize: 12,
          width: 44,
          textAlign: "right",
          color: positive ? "var(--text-primary)" : "var(--blue5)",
        }}
      >
        {positive ? "+" : "−"}
        {Math.abs(contribution).toFixed(2)}
      </span>
      {/* Centre line: positive extends right, negative extends left. */}
      <span
        style={{
          width: 100,
          height: 6,
          display: "flex",
          justifyContent: positive ? "flex-start" : "flex-end",
          flexDirection: positive ? "row" : "row-reverse",
          background: "var(--dark-gray4)",
          borderRadius: "var(--radius)",
          overflow: "hidden",
        }}
      >
        <span
          style={{
            width: `${frac * 100}%`,
            height: "100%",
            background: positive ? "var(--red3)" : "var(--blue3)",
          }}
        />
      </span>
    </div>
  );
}
