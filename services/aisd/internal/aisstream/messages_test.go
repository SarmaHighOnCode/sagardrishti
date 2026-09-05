package aisstream

import (
	"encoding/json"
	"testing"
	"time"
)

const samplePositionReport = `{
  "MessageType": "PositionReport",
  "Message": {
    "PositionReport": {
      "Cog": 167.7,
      "Latitude": 19.076,
      "Longitude": 72.877,
      "NavigationalStatus": 0,
      "RateOfTurn": 0,
      "Sog": 10.5,
      "TrueHeading": 167,
      "Valid": true
    }
  },
  "MetaData": {
    "MMSI": 123456789,
    "ShipName": "EXAMPLE",
    "latitude": 19.076,
    "longitude": 72.877,
    "time_utc": "2026-09-03 12:30:00.123456789 +0000 UTC"
  }
}`

const sampleShipStaticData = `{
  "MessageType": "ShipStaticData",
  "Message": {
    "ShipStaticData": {
      "CallSign": "ABCD1",
      "Destination": "MUMBAI",
      "Dimension": {"A": 100, "B": 20, "C": 10, "D": 10},
      "ImoNumber": 9123456,
      "Name": "EXAMPLE",
      "Type": 70,
      "Valid": true
    }
  },
  "MetaData": {
    "MMSI": 123456789,
    "ShipName": "EXAMPLE",
    "latitude": 19.076,
    "longitude": 72.877,
    "time_utc": "2026-09-03 12:30:00 +0000 UTC"
  }
}`

const sampleUnknownType = `{
  "MessageType": "SomeFutureType",
  "Message": {"Whatever": 1},
  "MetaData": {"MMSI": 1, "time_utc": "2026-09-03 12:30:00 +0000 UTC"}
}`

func mustDecode(t *testing.T, raw string) Envelope {
	t.Helper()
	var env Envelope
	if err := json.Unmarshal([]byte(raw), &env); err != nil {
		t.Fatalf("decode envelope: %v", err)
	}
	return env
}

func TestParsePositionReport(t *testing.T) {
	env := mustDecode(t, samplePositionReport)

	if env.MetaData.MMSI != 123456789 {
		t.Errorf("MMSI = %d, want 123456789", env.MetaData.MMSI)
	}
	wantTime := time.Date(2026, 9, 3, 12, 30, 0, 123456789, time.UTC)
	if !env.MetaData.TimeUTC.Time.Equal(wantTime) {
		t.Errorf("TimeUTC = %v, want %v", env.MetaData.TimeUTC.Time, wantTime)
	}

	pr, ok := ParsePositionReport(env)
	if !ok {
		t.Fatal("ParsePositionReport returned ok = false")
	}
	if pr.Latitude != 19.076 || pr.Longitude != 72.877 {
		t.Errorf("lat/lon = %v/%v, want 19.076/72.877", pr.Latitude, pr.Longitude)
	}
	if pr.Sog != 10.5 {
		t.Errorf("Sog = %v, want 10.5", pr.Sog)
	}

	if _, ok := ParseShipStaticData(env); ok {
		t.Error("ParseShipStaticData should not match a PositionReport envelope")
	}
}

func TestParseShipStaticData(t *testing.T) {
	env := mustDecode(t, sampleShipStaticData)

	ssd, ok := ParseShipStaticData(env)
	if !ok {
		t.Fatal("ParseShipStaticData returned ok = false")
	}
	if ssd.Name != "EXAMPLE" || ssd.CallSign != "ABCD1" || ssd.ImoNumber != 9123456 {
		t.Errorf("unexpected ShipStaticData: %+v", ssd)
	}

	if _, ok := ParsePositionReport(env); ok {
		t.Error("ParsePositionReport should not match a ShipStaticData envelope")
	}
}

func TestUnknownMessageTypeDoesNotError(t *testing.T) {
	env := mustDecode(t, sampleUnknownType)

	if _, ok := ParsePositionReport(env); ok {
		t.Error("expected ok = false for unknown type")
	}
	if _, ok := ParseShipStaticData(env); ok {
		t.Error("expected ok = false for unknown type")
	}
}

func TestAISTimeUnparseableFallsBackToZero(t *testing.T) {
	var raw = `{"MMSI": 1, "time_utc": "not a real time"}`
	var md MetaData
	if err := json.Unmarshal([]byte(raw), &md); err != nil {
		t.Fatalf("unmarshal should not fail on bad timestamp: %v", err)
	}
	if !md.TimeUTC.Time.IsZero() {
		t.Errorf("expected zero time, got %v", md.TimeUTC.Time)
	}
}
