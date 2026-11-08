//go:build formalverify

package grpcclient

import (
	"context"
	"net"
	"testing"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/yinghanhung/grpc-polyglot/grpc-http1-proxy-go/internal/pb"
)

// scriptedGreeter counts SayHello attempts and fails the first failBefore calls
// with a fixed status. failBefore 0 means the first call succeeds.
type scriptedGreeter struct {
	pb.UnimplementedGreeterServer
	failBefore int
	code       codes.Code
	calls      int
}

func (s *scriptedGreeter) SayHello(context.Context, *pb.HelloRequest) (*pb.HelloReply, error) {
	s.calls++
	if s.calls <= s.failBefore {
		return nil, status.Error(s.code, "scripted")
	}
	return &pb.HelloReply{Message: "ok"}, nil
}

// retryableStatus is the set New documents as transient: Unavailable,
// ResourceExhausted, and DeadlineExceeded. Canceled is intentionally absent.
func retryableStatus(code codes.Code) bool {
	switch code {
	case codes.Unavailable, codes.ResourceExhausted, codes.DeadlineExceeded:
		return true
	default:
		return false
	}
}

// attemptBudget is how many times SayHello may reach the backend.
// MaxRetries 0 leaves the interceptor at its default of no retries (one attempt).
// A positive MaxRetries is passed to grpc_retry.WithMax, whose loop runs
// attempt < max, so the value is the total number of attempts.
func attemptBudget(maxRetries uint) int {
	if maxRetries == 0 {
		return 1
	}
	return int(maxRetries)
}

// wantAttempts is the promise of grpcclient.New and SayHello: only the documented
// transient statuses are retried, and the backend is contacted at most attemptBudget times.
func wantAttempts(maxRetries uint, code codes.Code, failBefore int) (calls int, ok bool) {
	if failBefore <= 0 {
		return 1, true
	}
	budget := attemptBudget(maxRetries)
	if !retryableStatus(code) {
		return 1, false
	}
	if failBefore < budget {
		return failBefore + 1, true
	}
	return budget, false
}

// TestRetryBudget checks the retry promise of New and SayHello.
//
// Canceled is not a documented retry status. With MaxRetries >= 2 the current
// client still performs a second attempt: WithPerRetryTimeout makes the
// interceptor continue after any DeadlineExceeded or Canceled status while the
// parent context is active. The rows Canceled/max=2/fail=1 and
// Canceled/max=2/fail=9 fail on the current code for that reason. A failure of
// any other row is a new break, not that known finding.
func TestRetryBudget(t *testing.T) {
	codesUnderTest := []codes.Code{
		codes.InvalidArgument,
		codes.Internal,
		codes.Canceled,
		codes.Unavailable,
		codes.ResourceExhausted,
		codes.DeadlineExceeded,
	}
	maxima := []uint{0, 1, 2}
	// 0: first call succeeds. 1: one failure then success. 9: fail past every budget in this test.
	schedules := []int{0, 1, 9}

	for _, maxRetries := range maxima {
		for _, code := range codesUnderTest {
			for _, failBefore := range schedules {
				maxRetries, code, failBefore := maxRetries, code, failBefore
				wantCalls, wantOK := wantAttempts(maxRetries, code, failBefore)
				t.Run(status.Code(status.New(code, "").Err()).String()+"/max="+itoa(int(maxRetries))+"/fail="+itoa(failBefore), func(t *testing.T) {
					calls, err := driveSayHello(t, maxRetries, code, failBefore, context.Background())
					if calls != wantCalls {
						t.Fatalf("backend attempts = %d, want %d (err=%v)", calls, wantCalls, err)
					}
					if wantOK {
						if err != nil {
							t.Fatalf("SayHello error = %v, want success", err)
						}
						return
					}
					if err == nil {
						t.Fatal("SayHello succeeded, want the scripted status")
					}
					if status.Code(err) != code {
						t.Fatalf("status = %s, want %s", status.Code(err), code)
					}
				})
			}
		}
	}
}

// TestRetryBudgetCancelledParent guards the promise that a caller cancel stops
// the call. The backend must not see a retry storm.
func TestRetryBudgetCancelledParent(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	calls, err := driveSayHello(t, 2, codes.Unavailable, 9, ctx)
	if err == nil {
		t.Fatal("SayHello succeeded on a cancelled context")
	}
	if calls > 1 {
		t.Fatalf("backend attempts = %d, want at most 1", calls)
	}
}

func driveSayHello(t *testing.T, maxRetries uint, code codes.Code, failBefore int, ctx context.Context) (int, error) {
	t.Helper()
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	srv := grpc.NewServer()
	greeter := &scriptedGreeter{failBefore: failBefore, code: code}
	pb.RegisterGreeterServer(srv, greeter)
	go srv.Serve(lis)
	t.Cleanup(func() {
		srv.Stop()
		lis.Close()
	})

	client, err := New(context.Background(), Config{
		Address:     lis.Addr().String(),
		DialTimeout: 3 * time.Second,
		Deadline:    3 * time.Second,
		MaxRetries:  maxRetries,
	}, nil)
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	t.Cleanup(func() { client.Close() })

	_, err = client.SayHello(ctx, &pb.HelloRequest{Name: "budget"})
	return greeter.calls, err
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var digits [12]byte
	i := len(digits)
	for n > 0 {
		i--
		digits[i] = byte('0' + n%10)
		n /= 10
	}
	return string(digits[i:])
}
