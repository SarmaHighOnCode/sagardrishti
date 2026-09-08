package store

import (
	"context"
	"testing"
)

func TestJoinCols(t *testing.T) {
	cases := []struct {
		in   []string
		want string
	}{
		{nil, ""},
		{[]string{"a"}, "a"},
		{[]string{"a", "b", "c"}, "a, b, c"},
	}
	for _, c := range cases {
		if got := joinCols(c.in); got != c.want {
			t.Errorf("joinCols(%v) = %q, want %q", c.in, got, c.want)
		}
	}
}

// An empty batch must be a true no-op: it must not touch the pool at all,
// so a Store with a nil pool (as in this test) is a valid way to assert
// that - dereferencing a nil pool would panic if the early return were
// ever removed.
func TestWriteEmptyBatchesAreNoops(t *testing.T) {
	s := &Store{pool: nil}
	if err := s.WritePositions(context.Background(), nil); err != nil {
		t.Errorf("WritePositions(nil) = %v, want nil", err)
	}
	if err := s.WriteStatic(context.Background(), nil); err != nil {
		t.Errorf("WriteStatic(nil) = %v, want nil", err)
	}
}
