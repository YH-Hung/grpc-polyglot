PROTO_DIR := proto
PROTO_OUT := internal/pb
PROTO_FILES := $(shell find $(PROTO_DIR) -name '*.proto')
GOPATH_BIN := $(shell go env GOPATH)/bin

.PHONY: proto lint test build

proto:
	@export PATH=$$PATH:$(GOPATH_BIN) && \
	protoc -I $(PROTO_DIR) --go_out=$(PROTO_OUT) --go_opt=paths=source_relative \
		--go-grpc_out=$(PROTO_OUT) --go-grpc_opt=paths=source_relative $(PROTO_FILES) && \
	if [ -d $(PROTO_OUT)/helloworld ]; then \
		mv $(PROTO_OUT)/helloworld/*.pb.go $(PROTO_OUT)/ && \
		rmdir $(PROTO_OUT)/helloworld; \
	fi

lint:
	gofmt -w $$(find . -name '*.go')

test:
	go test ./...

build:
	go build -o bin/grpc-http1-proxy-go ./cmd/grpc-http1-proxy-go
