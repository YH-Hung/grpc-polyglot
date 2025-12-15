package main

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	pb "github.com/yinghanhung/grpc-polyglot/routing/proto/go/helloworld"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
)

const (
	defaultAddress = "localhost:9080"
	timeout        = 10 * time.Second
)

// Color codes for terminal output
const (
	colorReset  = "\033[0m"
	colorRed    = "\033[31m"
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
	colorBlue   = "\033[34m"
	colorPurple = "\033[35m"
	colorCyan   = "\033[36m"
)

func printBanner() {
	fmt.Println(colorCyan + "╔════════════════════════════════════════════════════════╗" + colorReset)
	fmt.Println(colorCyan + "║     gRPC APISIX Routing Demo - Interactive Client      ║" + colorReset)
	fmt.Println(colorCyan + "╚════════════════════════════════════════════════════════╝" + colorReset)
	fmt.Println()
}

func printMenu() {
	fmt.Println(colorYellow + "Available Options:" + colorReset)
	fmt.Println("  1. Send request WITHOUT header (should route to Go server)")
	fmt.Println("  2. Send request WITH x-backend-version: v2 (should route to Rust server)")
	fmt.Println("  3. Send request with CUSTOM header value")
	fmt.Println("  4. Send N requests alternating headers (load test)")
	fmt.Println("  5. Exit")
	fmt.Println()
}

func sendRequest(client pb.GreeterClient, name string, headerValue string) error {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	// Add header if specified
	if headerValue != "" {
		md := metadata.New(map[string]string{
			"x-backend-version": headerValue,
		})
		ctx = metadata.NewOutgoingContext(ctx, md)
		fmt.Printf(colorBlue+"Sending with header: x-backend-version=%s\n"+colorReset, headerValue)
	} else {
		fmt.Println(colorBlue + "Sending without header" + colorReset)
	}

	// Make the request
	r, err := client.SayHello(ctx, &pb.HelloRequest{Name: name})
	if err != nil {
		return fmt.Errorf(colorRed+"Request failed: %v"+colorReset, err)
	}

	// Display response
	fmt.Println(colorGreen + "╔════════════════ Response ════════════════╗" + colorReset)
	fmt.Printf("  Message:      %s\n", r.GetMessage())
	fmt.Printf("  Server:       %s\n", r.GetServerName())
	fmt.Printf("  Version:      %s\n", r.GetServerVersion())
	fmt.Printf("  Architecture: %s\n", r.GetArchitecture())
	fmt.Println(colorGreen + "╚══════════════════════════════════════════╝" + colorReset)
	fmt.Println()

	return nil
}

func main() {
	// Get APISIX address from environment or use default
	address := os.Getenv("APISIX_ADDR")
	if address == "" {
		address = defaultAddress
	}

	printBanner()
	fmt.Printf("Connecting to APISIX at: %s\n\n", address)

	// Set up connection to the server
	conn, err := grpc.NewClient(address, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer conn.Close()

	client := pb.NewGreeterClient(conn)

	reader := bufio.NewReader(os.Stdin)

	for {
		printMenu()
		fmt.Print(colorPurple + "Enter your choice (1-5): " + colorReset)

		input, _ := reader.ReadString('\n')
		choice := strings.TrimSpace(input)

		fmt.Println()

		switch choice {
		case "1":
			fmt.Print("Enter your name: ")
			name, _ := reader.ReadString('\n')
			name = strings.TrimSpace(name)
			if name == "" {
				name = "World"
			}
			if err := sendRequest(client, name, ""); err != nil {
				fmt.Println(err)
			}

		case "2":
			fmt.Print("Enter your name: ")
			name, _ := reader.ReadString('\n')
			name = strings.TrimSpace(name)
			if name == "" {
				name = "World"
			}
			if err := sendRequest(client, name, "v2"); err != nil {
				fmt.Println(err)
			}

		case "3":
			fmt.Print("Enter your name: ")
			name, _ := reader.ReadString('\n')
			name = strings.TrimSpace(name)
			if name == "" {
				name = "World"
			}
			fmt.Print("Enter custom header value: ")
			headerValue, _ := reader.ReadString('\n')
			headerValue = strings.TrimSpace(headerValue)
			if err := sendRequest(client, name, headerValue); err != nil {
				fmt.Println(err)
			}

		case "4":
			fmt.Print("Enter number of requests: ")
			countStr, _ := reader.ReadString('\n')
			countStr = strings.TrimSpace(countStr)
			count, err := strconv.Atoi(countStr)
			if err != nil || count <= 0 {
				fmt.Println(colorRed + "Invalid number, using default: 10" + colorReset)
				count = 10
			}

			fmt.Printf("\nSending %d requests (alternating headers)...\n\n", count)

			goCount := 0
			rustCount := 0
			errors := 0

			for i := 1; i <= count; i++ {
				headerValue := ""
				if i%2 == 0 {
					headerValue = "v2"
				}

				err := sendRequest(client, fmt.Sprintf("User%d", i), headerValue)
				if err != nil {
					fmt.Println(err)
					errors++
				} else {
					if headerValue == "v2" {
						rustCount++
					} else {
						goCount++
					}
				}
				time.Sleep(100 * time.Millisecond)
			}

			fmt.Println(colorCyan + "╔══════════════ Load Test Summary ══════════════╗" + colorReset)
			fmt.Printf("  Total Requests:    %d\n", count)
			fmt.Printf("  Go Server:         %d\n", goCount)
			fmt.Printf("  Rust Server:       %d\n", rustCount)
			fmt.Printf("  Errors:            %d\n", errors)
			fmt.Println(colorCyan + "╚════════════════════════════════════════════════╝" + colorReset)
			fmt.Println()

		case "5":
			fmt.Println(colorGreen + "Goodbye!" + colorReset)
			return

		default:
			fmt.Println(colorRed + "Invalid choice. Please select 1-5." + colorReset)
			fmt.Println()
		}
	}
}
