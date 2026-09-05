package aisstream

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

func TestBackoffStaysInBounds(t *testing.T) {
	for attempt := 0; attempt < 30; attempt++ {
		for i := 0; i < 20; i++ { // jitter is random - sample repeatedly
			d := backoff(attempt)
			if d < minBackoff || d > maxBackoff {
				t.Fatalf("backoff(%d) = %v, want within [%v, %v]", attempt, d, minBackoff, maxBackoff)
			}
		}
	}
}

// newTestServer starts a WebSocket server that upgrades the connection,
// reads exactly one Subscribe frame, hands it to onSubscribe, writes each
// message in messages, and then blocks (simulating a live feed) until the
// client disconnects.
func newTestServer(t *testing.T, messages []string, onSubscribe func(Subscribe)) *httptest.Server {
	t.Helper()
	upgrader := websocket.Upgrader{}

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		var sub Subscribe
		if err := conn.ReadJSON(&sub); err != nil {
			return
		}
		if onSubscribe != nil {
			onSubscribe(sub)
		}

		for _, m := range messages {
			if err := conn.WriteMessage(websocket.TextMessage, []byte(m)); err != nil {
				return
			}
		}

		// Keep the connection open until the client goes away, rather than
		// closing immediately - closing right away would race the test's
		// read of `out` against the client's reconnect-on-EOF path.
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				return
			}
		}
	})

	return httptest.NewServer(handler)
}

func TestClientRunDeliversMessages(t *testing.T) {
	var gotSub Subscribe
	srv := newTestServer(t, []string{samplePositionReport, sampleShipStaticData}, func(s Subscribe) {
		gotSub = s
	})
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")

	c := &Client{
		URL:                wsURL,
		APIKey:             "test-key",
		Boxes:              [][2][2]float64{{{6, 60}, {24.5, 76.5}}},
		FilterMessageTypes: []string{"PositionReport", "ShipStaticData"},
	}

	out := make(chan []byte, 10)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	errCh := make(chan error, 1)
	go func() { errCh <- c.Run(ctx, out) }()

	var received [][]byte
	timeout := time.After(5 * time.Second)
	for len(received) < 2 {
		select {
		case msg := <-out:
			received = append(received, msg)
		case <-timeout:
			t.Fatalf("timed out waiting for messages, got %d", len(received))
		}
	}

	cancel()
	select {
	case err := <-errCh:
		if err != context.Canceled {
			t.Errorf("Run returned %v, want context.Canceled", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("Run did not return after ctx cancellation")
	}

	if gotSub.APIKey != "test-key" {
		t.Errorf("server saw APIKey %q, want %q", gotSub.APIKey, "test-key")
	}
	if len(gotSub.BoundingBoxes) != 1 {
		t.Errorf("server saw %d bounding boxes, want 1", len(gotSub.BoundingBoxes))
	}

	var env0 Envelope
	if err := json.Unmarshal(received[0], &env0); err != nil {
		t.Fatalf("decode first message: %v", err)
	}
	if env0.MessageType != "PositionReport" {
		t.Errorf("first message type = %q, want PositionReport", env0.MessageType)
	}
}
