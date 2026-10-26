# syntax=docker/dockerfile:1
ARG VERSION=dev

FROM golang:1.26.10-bookworm@sha256:632dff7351799a5a9954a48dc06670ade72ee44e8c351cdc0e5a57af2fea21af AS builder
WORKDIR /workspace
COPY go.mod go.sum ./
RUN go mod download
COPY . .
ARG VERSION
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-s -w -X main.Version=${VERSION}" \
    -o /nest-node-agent \
    ./services/node-agent/

FROM debian:bookworm-slim@sha256:f9c6a2fd2ddbc23e336b6257a5245e31f996953ef06cd13a59fa0a1df2d5c252
# Exact Debian versions rotate with security updates and vanish from the mirror, breaking builds; base is digest-pinned.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    util-linux \
    smartmontools \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
# K8s DaemonSet manifest handles privilege escalation for /dev and /sys access
# The container process itself runs as UID 1000 (appuser) for security
COPY --from=builder /nest-node-agent /nest-node-agent
USER 1000
EXPOSE 9091
CMD ["/nest-node-agent"]
