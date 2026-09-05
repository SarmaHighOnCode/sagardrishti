package wal

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestAppendSyncRotate(t *testing.T) {
	dir := t.TempDir()

	w, err := Open(dir)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	// Rotate() opens a fresh segment for the writer to keep using; close
	// it so the test's TempDir cleanup can remove it (Windows disallows
	// deleting a still-open file, unlike POSIX).
	defer w.Close()

	if err := w.Append([]byte(`{"a":1}`)); err != nil {
		t.Fatalf("Append: %v", err)
	}
	if err := w.Sync(); err != nil {
		t.Fatalf("Sync: %v", err)
	}

	// The segment must exist on disk once synced, before any rotate.
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatalf("expected 1 segment file after sync, got %d", len(entries))
	}

	if err := w.Rotate(); err != nil {
		t.Fatalf("Rotate: %v", err)
	}

	// Rotate deletes the committed segment and opens a new (empty) one -
	// still exactly one file, but a fresh, unsynced one.
	entries, _ = os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatalf("expected 1 segment file after rotate, got %d", len(entries))
	}
}

func TestReplayHandlesAndDeletesOnSuccess(t *testing.T) {
	dir := t.TempDir()

	w, err := Open(dir)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	_ = w.Append([]byte(`{"a":1}`))
	_ = w.Append([]byte(`{"a":2}`))
	if err := w.Sync(); err != nil {
		t.Fatalf("Sync: %v", err)
	}
	if err := w.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	var gotLines int
	n, err := Replay(dir, func(lines [][]byte) error {
		gotLines += len(lines)
		return nil
	})
	if err != nil {
		t.Fatalf("Replay: %v", err)
	}
	if n != 1 {
		t.Errorf("filesReplayed = %d, want 1", n)
	}
	if gotLines != 2 {
		t.Errorf("gotLines = %d, want 2", gotLines)
	}

	entries, _ := os.ReadDir(dir)
	if len(entries) != 0 {
		t.Errorf("expected replayed segment to be deleted, %d files remain", len(entries))
	}
}

func TestReplayLeavesFileOnHandleError(t *testing.T) {
	dir := t.TempDir()

	w, err := Open(dir)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	_ = w.Append([]byte(`{"a":1}`))
	if err := w.Sync(); err != nil {
		t.Fatalf("Sync: %v", err)
	}
	if err := w.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	n, err := Replay(dir, func(lines [][]byte) error {
		return errors.New("db is down")
	})
	if err == nil {
		t.Fatal("expected Replay to return an error")
	}
	if n != 0 {
		t.Errorf("filesReplayed = %d, want 0", n)
	}

	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Errorf("expected the failed segment to remain on disk, got %d files", len(entries))
	}
}

func TestReplayOnEmptyDirIsNoop(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "does-not-exist-yet")
	n, err := Replay(dir, func(lines [][]byte) error {
		t.Fatal("handle should not be called for a missing dir")
		return nil
	})
	if err != nil {
		t.Fatalf("Replay on missing dir: %v", err)
	}
	if n != 0 {
		t.Errorf("filesReplayed = %d, want 0", n)
	}
}
