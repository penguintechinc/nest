# Dockerfile for nest DB Proxy
# Build (XDP enabled, default):  docker build -t nest-db-proxy .
# Build (rootless / no XDP):     docker build --build-arg XDP_BUILD_TAGS=noxdp -t nest-db-proxy .
# Multi-arch:                    docker buildx build --platform linux/amd64,linux/arm64 .
#
# XDP is a RUNTIME toggle too: the xdp-tagged binary probes for NET_ADMIN at
# startup (DBPROXY_XDP_ENABLED) and falls back to the standard Go net stack when
# the capability is absent, so the same image runs in privileged and
# unprivileged (rootless) pods alike.

ARG XDP_BUILD_TAGS=xdp

# Stage 1: Builder
FROM golang:1.26.10-bookworm@sha256:632dff7351799a5a9954a48dc06670ade72ee44e8c351cdc0e5a57af2fea21af AS builder

WORKDIR /build

COPY go.mod go.sum ./
RUN go mod download

COPY . .

ARG XDP_BUILD_TAGS
RUN CGO_ENABLED=0 go build \
    -tags "${XDP_BUILD_TAGS}" \
    -ldflags="-X main.Version=$(git describe --tags --always --dirty 2>/dev/null || echo dev) \
               -X main.BuildTime=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
               -X main.GitCommit=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)" \
    -o app \
    ./cmd/main.go

# Run the test suite in the builder stage (race + coverage).
RUN go test -race -cover ./...

# Stage 2: Runtime
FROM debian:bookworm-slim@sha256:f9c6a2fd2ddbc23e336b6257a5245e31f996953ef06cd13a59fa0a1df2d5c252

RUN groupadd -r dbproxy && useradd -r -g dbproxy -u 1000 dbproxy

WORKDIR /app

COPY --from=builder /build/app .

# Rootless
USER 1000

# Native-binary healthcheck (no curl/wget in the slim image): the `healthcheck`
# subcommand GETs the local /healthz on the metrics port and exits 0/1.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/app/app", "healthcheck"]

ENTRYPOINT ["/app/app"]
