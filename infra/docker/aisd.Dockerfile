# services/aisd - the AIS recorder. Static binary, scratch base: no libc,
# no shell, nothing an attacker or an upgrade can break. See
# docs/adr/0005-go-for-the-ais-data-plane.md.
#
# aisd depends on packages/go (store/aoi/quality, promoted out of
# services/aisd/internal/* — see ADR 0005) via a relative `replace`
# directive in its go.mod: `replace github.com/sagardrishti/go =>
# ../../packages/go`. That path is resolved from services/aisd/'s own
# directory, so the build context here mirrors the real repo layout
# (packages/go/ and services/aisd/ as siblings) rather than copying only
# services/aisd/ in isolation, which is what this file did before and
# which stopped building the moment that dependency was introduced.

FROM golang:1.23-alpine AS build
RUN apk add --no-cache ca-certificates
WORKDIR /src

# Manifests first, mirroring the repo layout, so `go mod download` is
# cached independently of source changes on either side.
COPY packages/go/go.mod packages/go/go.sum packages/go/
COPY services/aisd/go.mod services/aisd/go.sum services/aisd/
WORKDIR /src/services/aisd
RUN go mod download

WORKDIR /src
COPY packages/go/ packages/go/
COPY services/aisd/ services/aisd/
WORKDIR /src/services/aisd
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /aisd ./cmd

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /aisd /aisd
ENTRYPOINT ["/aisd"]
