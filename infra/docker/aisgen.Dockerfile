# services/aisgen - the synthetic AIS generator. Same shape as
# aisd.Dockerfile and for the same reason: it depends on packages/go via
# a relative `replace` directive, so the build context mirrors the real
# repo layout (packages/go/ and services/aisgen/ as siblings).
#
# Unlike aisd, this is not a long-running daemon — it runs one
# simulation and exits — so there is no restart policy or health
# check attached to it in docker-compose.yml.

FROM golang:1.23-alpine AS build
RUN apk add --no-cache ca-certificates
WORKDIR /src

COPY packages/go/go.mod packages/go/go.sum packages/go/
COPY services/aisgen/go.mod services/aisgen/go.sum services/aisgen/
WORKDIR /src/services/aisgen
RUN go mod download

WORKDIR /src
COPY packages/go/ packages/go/
COPY services/aisgen/ services/aisgen/
WORKDIR /src/services/aisgen
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /aisgen ./cmd/aisgen

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /aisgen /aisgen
ENTRYPOINT ["/aisgen"]
