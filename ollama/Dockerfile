#Stage 1: Build the binary
FROM golang:alpine AS builder

RUN apk add --no-cache git build-base cmake bash
WORKDIR /app

#Clone the Ollama source
RUN git clone https://github.com/jmorgance/ollama.git .
RUN go generate ./... && go build -ldflags '-linkmode external -extldflags "-static"' -o .

#Stage 2: Final image
FROM alpine

ENV OLLAMA_HOST "0.0.0.0"

RUN apk add --no-cache libstdc++ curl

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ARG USER=ollama
ARG GROUP=ollama
RUN addgroup $GROUP && adduser -D -G $GROUP $USER

COPY --from=builder /app/ollama /bin/ollama

USER $USER:$GROUP
ENTRYPOINT [ "/entrypoint.sh" ]