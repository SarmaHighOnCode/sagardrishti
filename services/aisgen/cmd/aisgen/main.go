// Command aisgen is the synthetic AIS generator. See
// services/aisgen/README.md and docs/adr/0005-go-for-the-ais-data-plane.md
// for why this exists and how it guarantees an ingest path identical to
// services/aisd's.
//
// Two modes, selected by whether DATABASE_URL is set:
//
//   - DATABASE_URL set: rows are written through packages/go/store —
//     the exact same batched-upsert code aisd's recorder uses — so this
//     is the real deliverable described in the ADR.
//   - DATABASE_URL unset: rows are written to newline-delimited JSON
//     files instead. This exists because, at the time this generator was
//     built, no Postgres instance was reachable in the environment doing
//     the work (Docker Desktop's daemon was down). Dry-run mode is what
//     makes "generation actually running" true today rather than only
//     once infrastructure exists — inspect the JSON, then point
//     DATABASE_URL at a real database and rerun with the same seed for
//     an identical result once Docker is back.
package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/sagardrishti/aisgen/internal/groundtruth"
	"github.com/sagardrishti/aisgen/internal/simulate"
	"github.com/sagardrishti/go/store"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: parseLevel(os.Getenv("SAGAR_LOG_LEVEL")),
	}))
	slog.SetDefault(logger)

	if err := run(logger); err != nil {
		logger.Error("aisgen exited with error", "error", err)
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	cfg := simulate.Config{
		Seed:           int64(envInt("SAGAR_AISGEN_SEED", time.Now().UnixNano()%1_000_000)),
		NumVessels:     envInt("SAGAR_AISGEN_VESSELS", 40),
		Duration:       time.Duration(envInt("SAGAR_AISGEN_DURATION_HOURS", 24)) * time.Hour,
		ReportInterval: time.Duration(envInt("SAGAR_AISGEN_REPORT_INTERVAL_SECONDS", 120)) * time.Second,
	}
	outDir := envOr("SAGAR_AISGEN_OUT_DIR", ".")
	groundTruthPath := envOr("SAGAR_AISGEN_GROUND_TRUTH_PATH", filepath.Join(outDir, "aisgen_ground_truth.json"))

	logger.Info("generating synthetic AIS traffic",
		"seed", cfg.Seed, "vessels", cfg.NumVessels,
		"duration", cfg.Duration.String(), "report_interval", cfg.ReportInterval.String())

	result := simulate.Run(cfg)
	logger.Info("simulation complete",
		"positions", len(result.Positions), "statics", len(result.Statics),
		"ground_truth_events", len(result.Ground.Events))

	if err := groundtruth.WriteJSON(groundTruthPath, result.Ground); err != nil {
		return err
	}
	logger.Info("wrote ground truth", "path", groundTruthPath)

	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		logger.Warn("DATABASE_URL not set — writing rows to JSON files instead of Postgres. " +
			"This is a stand-in for the real deliverable (writing through packages/go/store), " +
			"not a replacement for it. Set DATABASE_URL and rerun once a database is reachable.")
		return writeDryRun(outDir, result, logger)
	}

	return writeToStore(databaseURL, result, logger)
}

func writeToStore(databaseURL string, result simulate.Result, logger *slog.Logger) error {
	ctx := context.Background()

	db, err := store.Connect(ctx, databaseURL)
	if err != nil {
		return err
	}
	defer db.Close()

	batchSize := envInt("SAGAR_AISGEN_BATCH_SIZE", 500)

	for start := 0; start < len(result.Positions); start += batchSize {
		end := min(start+batchSize, len(result.Positions))
		if err := db.WritePositions(ctx, result.Positions[start:end]); err != nil {
			return err
		}
	}
	logger.Info("wrote positions", "rows", len(result.Positions))

	for start := 0; start < len(result.Statics); start += batchSize {
		end := min(start+batchSize, len(result.Statics))
		if err := db.WriteStatic(ctx, result.Statics[start:end]); err != nil {
			return err
		}
	}
	logger.Info("wrote statics", "rows", len(result.Statics))
	return nil
}

// writeDryRun emits one JSON object per line (JSONL) rather than one
// JSON array, so a large run can be inspected with ordinary line tools
// (wc -l, head, jq) without loading the whole file.
func writeDryRun(outDir string, result simulate.Result, logger *slog.Logger) error {
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}

	if err := writeJSONL(filepath.Join(outDir, "positions.jsonl"), len(result.Positions), func(i int) any {
		return result.Positions[i]
	}); err != nil {
		return err
	}
	logger.Info("wrote positions (dry-run)", "rows", len(result.Positions), "path", filepath.Join(outDir, "positions.jsonl"))

	if err := writeJSONL(filepath.Join(outDir, "statics.jsonl"), len(result.Statics), func(i int) any {
		return result.Statics[i]
	}); err != nil {
		return err
	}
	logger.Info("wrote statics (dry-run)", "rows", len(result.Statics), "path", filepath.Join(outDir, "statics.jsonl"))
	return nil
}

func writeJSONL(path string, n int, at func(i int) any) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	for i := 0; i < n; i++ {
		if err := enc.Encode(at(i)); err != nil {
			return err
		}
	}
	return nil
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int64) int {
	v := os.Getenv(key)
	if v == "" {
		return int(fallback)
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return int(fallback)
	}
	return n
}

func parseLevel(s string) slog.Level {
	switch s {
	case "DEBUG":
		return slog.LevelDebug
	case "WARN":
		return slog.LevelWarn
	case "ERROR":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}
