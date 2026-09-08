module github.com/sagardrishti/aisgen

go 1.23.0

toolchain go1.23.4

// Unpublished, same as services/aisd's replace of the same module — see
// ADR 0005. This is the whole point of aisgen existing as Go: it writes
// through the exact same packages/go/store batched-upsert code aisd uses,
// not a second, parallel implementation of the insert logic.
replace github.com/sagardrishti/go => ../../packages/go

require (
	github.com/jackc/pgx/v5 v5.7.6
	github.com/sagardrishti/go v0.0.0-00010101000000-000000000000
)

require (
	github.com/jackc/pgpassfile v1.0.0 // indirect
	github.com/jackc/pgservicefile v0.0.0-20240606120523-5a60cdf6a761 // indirect
	github.com/jackc/puddle/v2 v2.2.2 // indirect
	golang.org/x/crypto v0.37.0 // indirect
	golang.org/x/sync v0.13.0 // indirect
	golang.org/x/text v0.24.0 // indirect
)
