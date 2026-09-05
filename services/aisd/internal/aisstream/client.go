package aisstream

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"math/rand"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

const (
	// DefaultURL is the AISStream v0 WebSocket endpoint.
	DefaultURL = "wss://stream.aisstream.io/v0/stream"

	minBackoff = time.Second
	maxBackoff = 60 * time.Second
)

// Client is a supervised AISStream WebSocket consumer: it reconnects with
// exponential backoff and jitter forever, until ctx is cancelled. It never
// gives up permanently - the recorder's entire job is to not be the reason
// data is lost, and AISStream's own outages are exactly the kind of
// "planned for, not exceptional" failure this exists to survive.
type Client struct {
	URL                string
	APIKey             string
	Boxes              [][2][2]float64
	FilterMessageTypes []string
	Logger             *slog.Logger

	reconnects atomic.Int64
}

// Reconnects returns how many times the client has had to reconnect since
// it started. Exposed so the recorder can report it in its status file for
// `make ais-status`.
func (c *Client) Reconnects() int64 { return c.reconnects.Load() }

// Run connects, subscribes, and forwards every raw message envelope to out
// until ctx is cancelled. out should be a reasonably large buffered channel:
// Run blocks sending to it, which is the intended back-pressure point
// between the network and the WAL/DB writer.
func (c *Client) Run(ctx context.Context, out chan<- []byte) error {
	logger := c.Logger
	if logger == nil {
		logger = slog.Default()
	}

	attempt := 0
	for {
		if ctx.Err() != nil {
			return ctx.Err()
		}

		err := c.runOnce(ctx, out, logger)
		if ctx.Err() != nil {
			return ctx.Err()
		}

		c.reconnects.Add(1)
		wait := backoff(attempt)
		logger.Warn("aisstream connection lost, reconnecting",
			"error", err, "attempt", attempt, "wait", wait, "total_reconnects", c.reconnects.Load())

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(wait):
		}
		attempt++
	}
}

// runOnce holds one connection open until it errors or ctx is cancelled.
// A nil error return only happens via ctx cancellation.
func (c *Client) runOnce(ctx context.Context, out chan<- []byte, logger *slog.Logger) error {
	dialCtx, cancel := context.WithTimeout(ctx, 15*time.Second)
	defer cancel()

	conn, _, err := websocket.DefaultDialer.DialContext(dialCtx, c.URL, nil)
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}
	defer conn.Close()

	sub := Subscribe{
		APIKey:             c.APIKey,
		BoundingBoxes:      c.Boxes,
		FilterMessageTypes: c.FilterMessageTypes,
	}
	if err := conn.WriteJSON(sub); err != nil {
		return fmt.Errorf("subscribe: %w", err)
	}
	logger.Info("aisstream connected", "boxes", len(c.Boxes))

	// Closing the connection is how we interrupt a blocked ReadMessage
	// when the caller cancels ctx.
	done := make(chan struct{})
	defer close(done)
	go func() {
		select {
		case <-ctx.Done():
			_ = conn.Close()
		case <-done:
		}
	}()

	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			return fmt.Errorf("read: %w", err)
		}

		select {
		case out <- msg:
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

// backoff returns a full-jitter exponential backoff duration in
// [minBackoff, maxBackoff], attempt is zero-based.
func backoff(attempt int) time.Duration {
	capped := maxBackoff
	if attempt <= 10 { // 1s<<10 already exceeds maxBackoff, no need to shift further
		if scaled := minBackoff * time.Duration(int64(1)<<uint(attempt)); scaled > 0 && scaled < maxBackoff {
			capped = scaled
		}
	}
	if capped <= minBackoff {
		return minBackoff
	}
	//nolint:gosec // jitter timing, not security-sensitive
	return minBackoff + time.Duration(rand.Int63n(int64(capped-minBackoff)))
}

// marshalEnvelope is a small helper the writer side uses when it needs to
// re-derive an Envelope from a raw message, e.g. during WAL replay.
func UnmarshalEnvelope(raw []byte) (Envelope, error) {
	var env Envelope
	err := json.Unmarshal(raw, &env)
	return env, err
}
