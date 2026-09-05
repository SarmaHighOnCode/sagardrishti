# services/aisd - the AIS recorder. Static binary, scratch base: no libc,
# no shell, nothing an attacker or an upgrade can break. See
# docs/adr/0005-go-for-the-ais-data-plane.md.

FROM golang:1.23-alpine AS build
RUN apk add --no-cache ca-certificates
WORKDIR /src
COPY services/aisd/go.mod services/aisd/go.sum ./
RUN go mod download
COPY services/aisd/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /aisd ./cmd

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /aisd /aisd
ENTRYPOINT ["/aisd"]
