# syntax=docker/dockerfile:1
ARG VERSION=dev

FROM golang:1.26.10-bookworm@sha256:632dff7351799a5a9954a48dc06670ade72ee44e8c351cdc0e5a57af2fea21af AS builder
WORKDIR /workspace
COPY . .
WORKDIR /workspace/services/k8s-controller
RUN go mod download
ARG VERSION
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-s -w -X main.Version=${VERSION}" \
    -o /nest-controller \
    .

FROM debian:bookworm-slim@sha256:f9c6a2fd2ddbc23e336b6257a5245e31f996953ef06cd13a59fa0a1df2d5c252
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
# K8s liveness/readiness probes handle health checking — no HEALTHCHECK needed in Dockerfile
COPY --from=builder /nest-controller /nest-controller
USER 1000
EXPOSE 8081 9090
CMD ["/nest-controller"]
