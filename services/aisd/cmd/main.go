// Command aisd is the live AIS recorder. See services/aisd/README.md and
// docs/adr/0005-go-for-the-ais-data-plane.md for why this exists and why
// it is written the way it is.
package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/sagardrishti/aisd/internal/aisstream"
	"github.com/sagardrishti/aisd/internal/aoi"
	"github.com/sagardrishti/aisd/internal/recorder"
	"github.com/sagardrishti/aisd/internal/store"
	"github.com/sagardrishti/aisd/internal/wal"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: parseLevel(os.Getenv("SAGAR_LOG_LEVEL")),
	}))
	slog.SetDefault(logger)

	if err := run(logger); err != nil {
		logger.Error("aisd exited with error", "error", err)
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	apiKey := os.Getenv("AISSTREAM_API_KEY")
	if apiKey == "" {
		return errRequired("AISSTREAM_API_KEY")
	}
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		return errRequired("DATABASE_URL")
	}

	walDir := envOr("SAGAR_AISD_WAL_DIR", "/wal")
	batchSize := envInt("SAGAR_AISD_BATCH_SIZE", 500)
	flushSeconds := envInt("SAGAR_AISD_FLUSH_INTERVAL_SECONDS", 5)
	statusPath := envOr("SAGAR_AISD_STATUS_PATH", walDir+"/aisd_status.json")

	aois := aoi.Default()

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	logger.Info("connecting to database")
	db, err := store.Connect(ctx, databaseURL)
	if err != nil {
		return err
	}
	defer db.Close()

	logger.Info("replaying any WAL segments left by a previous run", "dir", walDir)
	replayed, err := wal.Replay(walDir, func(lines [][]byte) error {
		return recorder.ReplayInto(ctx, db, aois, "aisstream", lines)
	})
	if err != nil {
		// Do not block startup on this - the segments stay on disk and
		// will be retried on the next restart. Losing the recorder over a
		// transient replay failure would be worse than starting late.
		logger.Error("WAL replay incomplete, leftover segments will be retried on next start", "error", err, "files_replayed", replayed)
	} else {
		logger.Info("WAL replay complete", "files_replayed", replayed)
	}

	w, err := wal.Open(walDir)
	if err != nil {
		return err
	}
	defer w.Close()

	client := &aisstream.Client{
		URL:                envOr("SAGAR_AISSTREAM_URL", aisstream.DefaultURL),
		APIKey:             apiKey,
		Boxes:              aoi.BoundingBoxes(aois),
		FilterMessageTypes: []string{"PositionReport", "StandardClassBPositionReport", "ShipStaticData"},
		Logger:             logger,
	}

	rec := recorder.New(recorder.Config{
		Source:        "aisstream",
		AOIs:          aois,
		BatchSize:     batchSize,
		FlushInterval: time.Duration(flushSeconds) * time.Second,
		StatusPath:    statusPath,
	}, w, db, logger)

	raw := make(chan []byte, 10000)
	go func() {
		if err := client.Run(ctx, raw); err != nil && ctx.Err() == nil {
			logger.Error("aisstream client stopped unexpectedly", "error", err)
		}
	}()

	logger.Info("aisd recording", "aois", len(aois), "batch_size", batchSize, "flush_interval_s", flushSeconds)
	return rec.Consume(ctx, raw, client.Reconnects)
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return fallback
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

type configError struct{ missing string }

func (e configError) Error() string {
	return "missing required environment variable: " + e.missing
}

func errRequired(name string) error { return configError{missing: name} }
