package parser

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

// Regular expressions for parsing proto files
var (
	packageRegex   = regexp.MustCompile(`(?m)^package\s+([^;]+);`)
	importRegex    = regexp.MustCompile(`import\s+"([^"]+)";`)
	enumRegex      = regexp.MustCompile(`enum\s+(\w+)\s*{([^}]+)}`)
	enumValueRegex = regexp.MustCompile(`(\w+)\s*=\s*(\d+)\s*;`)
	serviceRegex   = regexp.MustCompile(`service\s+(\w+)\s*{`)
	rpcRegex       = regexp.MustCompile(`rpc\s+(\w+)\s*\(\s*([^)]+)\s*\)\s*returns\s*\(\s*([^)]+)\s*\)\s*[{;]`)
	messageRegex   = regexp.MustCompile(`message\s+(\w+)\s*{`)
	fieldRegex     = regexp.MustCompile(`(repeated\s+)?([^\s=]+)\s+([^\s=]+)\s*=\s*(\d+)\s*;`)
)

// ParseProtoFile parses a single .proto file and returns a ProtoFile structure
func ParseProtoFile(filePath string) (*types.ProtoFile, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	baseName := strings.TrimSuffix(filepath.Base(filePath), ".proto")
	protoFile := &types.ProtoFile{
		FileName: filePath,
		BaseName: baseName,
		Messages: make(map[string]*types.ProtoMessage),
		Enums:    make(map[string]*types.ProtoEnum),
	}

	contentStr := string(content)

	// Parse package
	if matches := packageRegex.FindStringSubmatch(contentStr); matches != nil {
		protoFile.Package = strings.TrimSpace(matches[1])
	}

	// Parse imports
	importMatches := importRegex.FindAllStringSubmatch(contentStr, -1)
	for _, match := range importMatches {
		protoFile.Imports = append(protoFile.Imports, match[1])
	}

	// Parse enums
	enumMatches := enumRegex.FindAllStringSubmatch(contentStr, -1)
	for _, match := range enumMatches {
		enumName := match[1]
		enumBody := match[2]
		
		protoEnum := &types.ProtoEnum{
			Name:   enumName,
			Values: make(map[string]int),
		}
		
		valueMatches := enumValueRegex.FindAllStringSubmatch(enumBody, -1)
		for _, valueMatch := range valueMatches {
			valueName := valueMatch[1]
			valueNum, err := strconv.Atoi(valueMatch[2])
			if err != nil {
				continue
			}
			protoEnum.Values[valueName] = valueNum
		}
		
		protoFile.Enums[enumName] = protoEnum
	}

	// Parse messages (with nested support)
	err = parseMessages(contentStr, protoFile)
	if err != nil {
		return nil, fmt.Errorf("failed to parse messages: %w", err)
	}

	// Parse services with brace-aware parsing
	if err := parseServices(contentStr, protoFile); err != nil {
		return nil, fmt.Errorf("failed to parse services: %w", err)
	}

	return protoFile, nil
}

// parseMessages handles parsing of messages with brace-aware nesting
func parseMessages(content string, protoFile *types.ProtoFile) error {
	// Find all message declarations
	messageStarts := messageRegex.FindAllStringIndex(content, -1)
	messageNames := messageRegex.FindAllStringSubmatch(content, -1)

	// Track brace nesting level to identify top-level messages only
	// Build a map of character position to nesting level
	braceLevel := make([]int, len(content))
	currentLevel := 0
	for i := 0; i < len(content); i++ {
		if content[i] == '{' {
			braceLevel[i] = currentLevel
			currentLevel++
		} else if content[i] == '}' {
			currentLevel--
			braceLevel[i] = currentLevel
		} else {
			braceLevel[i] = currentLevel
		}
	}

	for i, match := range messageStarts {
		if i >= len(messageNames) {
			continue
		}

		// Check if this message is at top level (nesting level 0)
		messageStartPos := match[0] // Position of 'message' keyword
		if messageStartPos >= len(braceLevel) || braceLevel[messageStartPos] != 0 {
			continue // Skip nested messages
		}

		messageName := messageNames[i][1]
		startPos := match[1] // Position after the opening brace

		// Find the matching closing brace
		braceCount := 1
		pos := startPos
		var endPos int

		for pos < len(content) && braceCount > 0 {
			char := content[pos]
			if char == '{' {
				braceCount++
			} else if char == '}' {
				braceCount--
				if braceCount == 0 {
					endPos = pos
					break
				}
			}
			pos++
		}

		if braceCount != 0 {
			return fmt.Errorf("unmatched braces in message %s", messageName)
		}

		messageBody := content[startPos:endPos]

		// Parse the message
		message, err := parseMessage(messageName, messageBody)
		if err != nil {
			return fmt.Errorf("failed to parse message %s: %w", messageName, err)
		}

		protoFile.Messages[messageName] = message
	}

	return nil
}

// parseMessage parses a single message body
func parseMessage(messageName, messageBody string) (*types.ProtoMessage, error) {
	message := &types.ProtoMessage{
		Name:           messageName,
		NestedMessages: make(map[string]*types.ProtoMessage),
		NestedEnums:    make(map[string]*types.ProtoEnum),
	}
	
	// Parse nested enums
	nestedEnumMatches := enumRegex.FindAllStringSubmatch(messageBody, -1)
	for _, match := range nestedEnumMatches {
		enumName := match[1]
		enumBodyStr := match[2]
		
		protoEnum := &types.ProtoEnum{
			Name:   enumName,
			Values: make(map[string]int),
		}
		
		valueMatches := enumValueRegex.FindAllStringSubmatch(enumBodyStr, -1)
		for _, valueMatch := range valueMatches {
			valueName := valueMatch[1]
			valueNum, err := strconv.Atoi(valueMatch[2])
			if err != nil {
				continue
			}
			protoEnum.Values[valueName] = valueNum
		}
		
		message.NestedEnums[enumName] = protoEnum
	}
	
	// Parse nested messages recursively
	nestedMessageStarts := messageRegex.FindAllStringIndex(messageBody, -1)
	nestedMessageNames := messageRegex.FindAllStringSubmatch(messageBody, -1)
	
	for i, match := range nestedMessageStarts {
		if i >= len(nestedMessageNames) {
			continue
		}
		
		nestedMessageName := nestedMessageNames[i][1]
		startPos := match[1]
		
		// Find matching closing brace
		braceCount := 1
		pos := startPos
		var endPos int
		
		for pos < len(messageBody) && braceCount > 0 {
			char := messageBody[pos]
			if char == '{' {
				braceCount++
			} else if char == '}' {
				braceCount--
				if braceCount == 0 {
					endPos = pos
					break
				}
			}
			pos++
		}
		
		if braceCount != 0 {
			return nil, fmt.Errorf("unmatched braces in nested message %s", nestedMessageName)
		}
		
		nestedMessageBody := messageBody[startPos:endPos]
		
		nestedMessage, err := parseMessage(nestedMessageName, nestedMessageBody)
		if err != nil {
			return nil, fmt.Errorf("failed to parse nested message %s: %w", nestedMessageName, err)
		}
		
		message.NestedMessages[nestedMessageName] = nestedMessage
	}
	
	// Parse fields
	fieldMatches := fieldRegex.FindAllStringSubmatch(messageBody, -1)
	for _, match := range fieldMatches {
		repeated := strings.TrimSpace(match[1]) == "repeated"
		fieldType := strings.TrimSpace(match[2])
		fieldName := strings.TrimSpace(match[3])
		fieldNumber, err := strconv.Atoi(match[4])
		if err != nil {
			continue
		}
		
		field := &types.ProtoField{
			Name:     fieldName,
			Type:     fieldType,
			Number:   fieldNumber,
			Repeated: repeated,
		}
		
		message.Fields = append(message.Fields, field)
	}
	
	return message, nil
}

// parseServices handles parsing of services with brace-aware nesting
func parseServices(content string, protoFile *types.ProtoFile) error {
	// Find all service declarations
	serviceStarts := serviceRegex.FindAllStringIndex(content, -1)
	serviceNames := serviceRegex.FindAllStringSubmatch(content, -1)

	for i, match := range serviceStarts {
		if i >= len(serviceNames) {
			continue
		}

		serviceName := serviceNames[i][1]
		startPos := match[1] // Position after the opening brace

		// Find the matching closing brace
		braceCount := 1
		pos := startPos
		var endPos int

		for pos < len(content) && braceCount > 0 {
			char := content[pos]
			if char == '{' {
				braceCount++
			} else if char == '}' {
				braceCount--
				if braceCount == 0 {
					endPos = pos
					break
				}
			}
			pos++
		}

		if braceCount != 0 {
			return fmt.Errorf("unmatched braces in service %s", serviceName)
		}

		serviceBody := content[startPos:endPos]

		// Parse the service
		service := &types.ProtoService{
			Name: serviceName,
		}

		// Parse RPCs within the service
		rpcMatches := rpcRegex.FindAllStringSubmatch(serviceBody, -1)
		for _, rpcMatch := range rpcMatches {
			rpcName := rpcMatch[1]
			inputType := strings.TrimSpace(rpcMatch[2])
			outputType := strings.TrimSpace(rpcMatch[3])

			// Skip streaming RPCs (contains 'stream' keyword)
			if strings.Contains(inputType, "stream") || strings.Contains(outputType, "stream") {
				continue
			}

			rpc := &types.ProtoRPC{
				Name:       rpcName,
				InputType:  inputType,
				OutputType: outputType,
				IsUnary:    true,
			}

			service.RPCs = append(service.RPCs, rpc)
		}

		protoFile.Services = append(protoFile.Services, service)
	}

	return nil
}