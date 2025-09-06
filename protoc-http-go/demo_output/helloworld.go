package helloworld

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// HelloRequest represents the HelloRequest message from the proto definition
type HelloRequest struct {
	Name string `json:"name"`
}

// HelloReply represents the HelloReply message from the proto definition
type HelloReply struct {
	Message string `json:"message"`
}

// GreeterClient is an HTTP client for the Greeter service
type GreeterClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

// NewGreeterClient creates a new GreeterClient with the given base URL
func NewGreeterClient(baseURL string) *GreeterClient {
	return &GreeterClient{
		BaseURL:    baseURL,
		HTTPClient: &http.Client{},
	}
}

// NewGreeterClientWithClient creates a new GreeterClient with a custom HTTP client
func NewGreeterClientWithClient(baseURL string, httpClient *http.Client) *GreeterClient {
	return &GreeterClient{
		BaseURL:    baseURL,
		HTTPClient: httpClient,
	}
}

// SayHello calls the SayHello RPC method
func (c *GreeterClient) SayHello(ctx context.Context, req *HelloRequest) (*HelloReply, error) {
	// Serialize request to JSON
	reqJSON, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create HTTP request
	url := c.BaseURL + "/helloworld/say-hello"
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(reqJSON))
	if err != nil {
		return nil, fmt.Errorf("failed to create HTTP request: %w", err)
	}

	// Set headers
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "application/json")

	// Make HTTP request
	resp, err := c.HTTPClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("HTTP request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response body
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP request failed with status %d: %s", resp.StatusCode, string(respBody))
	}

	// Deserialize response
	var response HelloReply
	if err := json.Unmarshal(respBody, &response); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &response, nil
}


