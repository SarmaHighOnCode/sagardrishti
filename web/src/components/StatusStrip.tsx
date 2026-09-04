import { formatHash } from "../lib/format";

/**
 * Persistent provenance strip. Small, quiet, always present.
 *
 * Nobody reads it until someone asks "how do I know this is real" — and
 * then it is the entire answer. Same fields that appear on the evidence
 * dossier's provenance page.
 *
 * Spec: docs/DESIGN_SYSTEM.md §6.5
 */
export function StatusStrip({
  sceneId,
  sceneHash,
  modelName,
  modelHash,
  forcing,
  synthetic = false,
}: {
  sceneId: string;
  sceneHash: string;
  modelName: string;
  modelHash: string;
  forcing: string;
  synthetic?: boolean;
}) {
  return (
    <div
      className="mono"
      style={{
        fontSize: 10,
        lineHeight: "14px",
        color: "var(--text-label)",
        padding: "var(--sp-4) var(--sp-5)",
        borderTop: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      {synthetic && (
        <div
          style={{
            color: "var(--orange4)",
            fontWeight: 600,
            letterSpacing: "0.06em",
          }}
        >
          ⚠ SYNTHETIC DATA — NOT A REAL ASSESSMENT
        </div>
      )}
      <div>
        <span style={{ color: "var(--text-disabled)" }}>scene </span>
        {sceneId} · {formatHash(sceneHash)}
      </div>
      <div>
        <span style={{ color: "var(--text-disabled)" }}>model </span>
        {modelName} · {formatHash(modelHash)}
      </div>
      <div>
        <span style={{ color: "var(--text-disabled)" }}>force </span>
        {forcing}
      </div>
    </div>
  );
}
