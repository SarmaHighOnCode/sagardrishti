// Package wal is the recorder's write-ahead log: every raw message is
// appended here before it is ever attempted against Postgres, so a
// database outage - or aisd itself crashing - cannot lose the stream.
// AISStream has no replay; this file is the only thing standing between a
// dropped connection to the database and permanently lost data.
package wal

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

const segmentSuffix = ".wal.jsonl"

// Writer appends raw message bytes to a segment file, one JSON object per
// line. Call Sync before attempting a downstream write, and Rotate only
// after that write has been durably committed.
type Writer struct {
	dir string

	mu   sync.Mutex
	f    *os.File
	bw   *bufio.Writer
	path string
}

// Open replays and returns the leftover segments from a previous run (via
// Replay, called separately by main before Open - see doc comment on
// Replay) and opens a fresh segment for new messages.
func Open(dir string) (*Writer, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("mkdir wal dir: %w", err)
	}
	w := &Writer{dir: dir}
	if err := w.openNewSegment(); err != nil {
		return nil, err
	}
	return w, nil
}

func (w *Writer) openNewSegment() error {
	name := fmt.Sprintf("aisd-%d%s", time.Now().UnixNano(), segmentSuffix)
	path := filepath.Join(w.dir, name)
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return fmt.Errorf("open wal segment: %w", err)
	}
	w.f = f
	w.bw = bufio.NewWriter(f)
	w.path = path
	return nil
}

// Append writes one raw message as a line. It does not flush - call Sync
// at the batch boundary, not per message, or the recorder cannot keep up
// with a busy feed.
func (w *Writer) Append(raw []byte) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if _, err := w.bw.Write(raw); err != nil {
		return err
	}
	return w.bw.WriteByte('\n')
}

// Sync flushes buffered writes to the OS and fsyncs the segment file. Call
// this before attempting to commit the corresponding batch downstream:
// once Sync returns nil, the batch survives an aisd crash even if the
// downstream commit has not happened yet.
func (w *Writer) Sync() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if err := w.bw.Flush(); err != nil {
		return fmt.Errorf("flush wal: %w", err)
	}
	return w.f.Sync()
}

// Rotate closes and deletes the current segment and opens a fresh one.
// Call this only once the batch that was in this segment has been durably
// committed downstream - the whole point of the WAL is that data is never
// deleted from it before it exists somewhere else.
func (w *Writer) Rotate() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if err := w.bw.Flush(); err != nil {
		return fmt.Errorf("flush before rotate: %w", err)
	}
	if err := w.f.Sync(); err != nil {
		return fmt.Errorf("sync before rotate: %w", err)
	}
	path := w.path
	if err := w.f.Close(); err != nil {
		return fmt.Errorf("close before rotate: %w", err)
	}
	if err := os.Remove(path); err != nil {
		return fmt.Errorf("remove committed segment: %w", err)
	}
	return w.openNewSegment()
}

// Close flushes and syncs without deleting the segment - used on graceful
// shutdown, where whatever has not yet been committed downstream must
// remain on disk for Replay to pick up next start.
func (w *Writer) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if err := w.bw.Flush(); err != nil {
		return err
	}
	if err := w.f.Sync(); err != nil {
		return err
	}
	return w.f.Close()
}

// Replay finds every leftover segment from a previous run (there is never
// one from the current process - call this before Open), passes each
// file's lines to handle in file order, and deletes the file once handle
// returns nil. If handle errors, replay stops immediately: that file and
// any later ones are left on disk for the next restart to retry, rather
// than risk marking data committed when it was not.
//
// filesReplayed counts only fully successful files.
func Replay(dir string, handle func(lines [][]byte) error) (filesReplayed int, err error) {
	entries, err := os.ReadDir(dir)
	if os.IsNotExist(err) {
		return 0, nil
	}
	if err != nil {
		return 0, fmt.Errorf("read wal dir: %w", err)
	}

	var names []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(e.Name(), segmentSuffix) {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names) // segment names embed UnixNano - lexical sort is chronological

	for _, name := range names {
		path := filepath.Join(dir, name)
		lines, readErr := readLines(path)
		if readErr != nil {
			return filesReplayed, fmt.Errorf("read segment %s: %w", name, readErr)
		}
		if len(lines) == 0 {
			_ = os.Remove(path)
			continue
		}
		if err := handle(lines); err != nil {
			return filesReplayed, fmt.Errorf("replay segment %s: %w", name, err)
		}
		if err := os.Remove(path); err != nil {
			return filesReplayed, fmt.Errorf("remove replayed segment %s: %w", name, err)
		}
		filesReplayed++
	}
	return filesReplayed, nil
}

func readLines(path string) ([][]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var lines [][]byte
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		cp := make([]byte, len(line))
		copy(cp, line)
		lines = append(lines, cp)
	}
	return lines, scanner.Err()
}
