# Functionality

- It assume there is a http proxy (something like the grpc-http1-proxy project) between http client and grpc server.
	- this proxy will convert http post request with request body as message content to grpc request, , and grpc response will be converted to json as response body.
	- The route of a rpc is in form of {base_url}/{proto file name}/{rpc method name}/{version}
	- rpc method name (version independent) in url should in kebab case
	- version should be lower case
	- ALL routes require version part, even V1
- About version
	- Some rpc methods end up with Vx (V2, V3,...)
	- If a rpc method did not end up with Vx, it was V1
- The code generation target is [vb.net](http://vb.net) / .NET Framework.
	- You MUST follow the best practices of http client in .NET framework.
	- All fields in json should be camel-case.
    - If you use HttpClient, it MUST be injected through constructor for sharing the instance for identical base url.
- .NET Framework 4.0 compatibility switch
	- Three modes for generated VB.NET code: net45, net40hc, net40hwr
	- net45
		- Target .NET framework 4.5 or above, so HttpClient async/await are available
		- Or .NET framework 4.0 with Microsoft.Net.Http for HttpClient and Microsoft.Bcl.Async for async/await
		- Authorization will be provided through injected HttpClient, no additional argument required.
	- net40hwr
		- Target .NET Framework 4, so async/await is not avaliable
		- Without HttpClient, so use HttpWebRequest instead
		- Provide argument for amend authorization http headers.
- You only required to consider unary grpc call.
- The given protobuf file under proto folder is only for reference.
	- This project is a generalized tool, you MUST handle any arbitrary protobuf file content and file numbers, just like the protobuf compiler, protoc.
	- For example, there are two independent sets of protobuf files under proto folder, one is quite simple, and the other has multiple files with import. This tool should be able to generate corresponding codes for specified path (for example, proto/simple or proto/complex).

# Non-Functional Requirements

- You MUST assess whether there is better approach to parse protobuf files rather than by regex.
- A detailed readme.md file
- Protobuf samples under proto folder for testing
- Test cases for verification
- MUST follow the idiomatic style and best practices of the implemented language.
- Make use of exclusive features of the implementated language if they simplify the logic or make logic more declaritive.