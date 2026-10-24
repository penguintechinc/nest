# syntax=docker/dockerfile:1
FROM golang:1.26.10-bookworm@sha256:632dff7351799a5a9954a48dc06670ade72ee44e8c351cdc0e5a57af2fea21af AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /gateway ./services/gateway/cmd/main.go

FROM debian:bookworm-slim@sha256:f9c6a2fd2ddbc23e336b6257a5245e31f996953ef06cd13a59fa0a1df2d5c252
RUN groupadd -r nest && useradd -r -g nest -u 1000 nest
COPY --from=builder /gateway /usr/local/bin/gateway
USER 1000
EXPOSE 50052 8082
ENTRYPOINT ["/usr/local/bin/gateway"]
