package httpserver

import (
	"bytes"
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"google.golang.org/protobuf/encoding/protojson"

	"github.com/yinghanhung/grpc-polyglot/grpc-http1-proxy-go/internal/pb"
)

type stubGreeter struct {
	resp *pb.HelloReply
	err  error
}

func (s *stubGreeter) SayHello(ctx context.Context, req *pb.HelloRequest) (*pb.HelloReply, error) {
	if s.err != nil {
		return nil, s.err
	}
	return s.resp, nil
}

func TestHandlerHello(t *testing.T) {
	greeter := &stubGreeter{resp: &pb.HelloReply{Message: "hi"}}
	srv, err := New(Config{ListenAddr: ":0"}, greeter, nil, nil)
	if err != nil {
		t.Fatalf("failed to create server: %v", err)
	}

	reqBody := []byte(`{"name":"alice"}`)
	req := httptest.NewRequest(http.MethodPost, "/helloworld/SayHello", bytes.NewReader(reqBody))
	rec := httptest.NewRecorder()

	srv.handler.hello(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 got %d", rec.Code)
	}

	resp := &pb.HelloReply{}
	if err := protojson.Unmarshal(rec.Body.Bytes(), resp); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}
	if resp.Message != "hi" {
		t.Fatalf("expected message 'hi', got %q", resp.Message)
	}
}

func TestHandlerHelloError(t *testing.T) {
	errBoom := errors.New("boom")
	greeter := &stubGreeter{err: errBoom}
	srv, err := New(Config{ListenAddr: ":0"}, greeter, nil, nil)
	if err != nil {
		t.Fatalf("failed to create server: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/helloworld/SayHello", bytes.NewReader([]byte(`{"name":"bob"}`)))
	rec := httptest.NewRecorder()

	srv.handler.hello(rec, req)

	if rec.Code != http.StatusBadGateway {
		t.Fatalf("expected 502 got %d", rec.Code)
	}

	body, _ := io.ReadAll(rec.Body)
	if !bytes.Contains(body, []byte("upstream error")) {
		t.Fatalf("unexpected body: %s", string(body))
	}
}
