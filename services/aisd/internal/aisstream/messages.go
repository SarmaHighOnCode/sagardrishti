// Package aisstream implements a client for the AISStream.io v0 WebSocket
// API: https://aisstream.io/documentation
package aisstream

import (
	"encoding/json"
	"strings"
	"time"
)

// Subscribe is the one-time message sent right after the socket opens.
type Subscribe struct {
	APIKey             string          `json:"APIKey"`
	BoundingBoxes      [][2][2]float64 `json:"BoundingBoxes"`
	FilterMessageTypes []string        `json:"FilterMessageTypes,omitempty"`
}

// Envelope is the outer shape of every server -> client message. Message is
// kept raw: only PositionReport and ShipStaticData are ever unmarshalled
// further, and an unrecognised MessageType (the API has added a few over
// time) is skipped rather than treated as an error.
type Envelope struct {
	MessageType string          `json:"MessageType"`
	Message     json.RawMessage `json:"Message"`
	MetaData    MetaData        `json:"MetaData"`
}

// MetaData accompanies every message regardless of type.
type MetaData struct {
	MMSI      int64   `json:"MMSI"`
	ShipName  string  `json:"ShipName"`
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	TimeUTC   AISTime `json:"time_utc"`
}

// PositionReport covers message types 1, 2, 3, 18 and 19.
type PositionReport struct {
	Cog                float64 `json:"Cog"`
	Latitude           float64 `json:"Latitude"`
	Longitude          float64 `json:"Longitude"`
	NavigationalStatus int     `json:"NavigationalStatus"`
	RateOfTurn         float64 `json:"RateOfTurn"`
	Sog                float64 `json:"Sog"`
	TrueHeading        int     `json:"TrueHeading"`
	Valid              bool    `json:"Valid"`
}

type positionReportWrapper struct {
	PositionReport PositionReport `json:"PositionReport"`
}

// StandardClassBPositionReport covers message type 18 on the newer schema;
// AISStream nests it separately from Class A. Shape is compatible enough
// with PositionReport that we reuse the same struct via a distinct wrapper.
type standardClassBWrapper struct {
	StandardClassBPositionReport PositionReport `json:"StandardClassBPositionReport"`
}

// ShipStaticData covers message types 5 and 24.
type ShipStaticData struct {
	CallSign    string    `json:"CallSign"`
	Destination string    `json:"Destination"`
	Dimension   Dimension `json:"Dimension"`
	ImoNumber   int64     `json:"ImoNumber"`
	Name        string    `json:"Name"`
	Type        int       `json:"Type"`
	Valid       bool      `json:"Valid"`
}

type Dimension struct {
	A float64 `json:"A"`
	B float64 `json:"B"`
	C float64 `json:"C"`
	D float64 `json:"D"`
}

type shipStaticDataWrapper struct {
	ShipStaticData ShipStaticData `json:"ShipStaticData"`
}

// ParsePositionReport extracts a PositionReport from an envelope whose
// MessageType is "PositionReport" or "StandardClassBPositionReport". ok is
// false if the envelope does not carry one.
func ParsePositionReport(env Envelope) (PositionReport, bool) {
	switch env.MessageType {
	case "PositionReport":
		var w positionReportWrapper
		if err := json.Unmarshal(env.Message, &w); err != nil {
			return PositionReport{}, false
		}
		return w.PositionReport, true
	case "StandardClassBPositionReport":
		var w standardClassBWrapper
		if err := json.Unmarshal(env.Message, &w); err != nil {
			return PositionReport{}, false
		}
		return w.StandardClassBPositionReport, true
	default:
		return PositionReport{}, false
	}
}

// ParseShipStaticData extracts static/voyage data from a "ShipStaticData"
// envelope.
func ParseShipStaticData(env Envelope) (ShipStaticData, bool) {
	if env.MessageType != "ShipStaticData" {
		return ShipStaticData{}, false
	}
	var w shipStaticDataWrapper
	if err := json.Unmarshal(env.Message, &w); err != nil {
		return ShipStaticData{}, false
	}
	return w.ShipStaticData, true
}

// AISTime unmarshals the several timestamp shapes AISStream has used
// ("2020-01-01 00:00:00.123456789 +0000 UTC" - Go's time.Time.String()
// format - and plain RFC3339) without ever failing the whole envelope
// decode. An unparseable timestamp falls back to the zero Time; callers
// should treat a zero Time as "use the receipt time instead."
type AISTime struct {
	time.Time
}

const goStringTimeLayout = "2006-01-02 15:04:05.999999999 -0700 MST"

func (t *AISTime) UnmarshalJSON(data []byte) error {
	s := strings.Trim(string(data), `"`)
	if s == "" || s == "null" {
		return nil
	}
	if parsed, err := time.Parse(time.RFC3339Nano, s); err == nil {
		t.Time = parsed
		return nil
	}
	if parsed, err := time.Parse(goStringTimeLayout, s); err == nil {
		t.Time = parsed
		return nil
	}
	// Deliberately not an error: one unparseable timestamp must not sink
	// an otherwise-good message. The record still gets recorded_at.
	return nil
}
