# HTTP Web Reverse Proxy

A simple Http Web Proxy to route requests from clients to target servers, minimal support for now with only request routing. (No security enhancement, no scaling support, no DDoS protection, rate limiting, etc.)

## Getting Started

1. Clone the repository
2. No additional dependencies required (uses standard Python library)
3. Run the proxy:

```python
from src.server import ProxyServer

proxy = ProxyServer(
    host="localhost",
    port=8080,
    backend_servers={
        "/api": "http://localhost:8000",
        "/web": "http://localhost:8001"
    }
)
proxy.start()
```

## Architecture

The proxy is built with a modular architecture consisting of several components:

### Components

1. **ProxyServer** (`src/server.py`)

   - Core server implementation
   - Manages socket connections
   - Handles client connection acceptance
   - Delegates request processing to RequestHandler

2. **RequestHandler** (`src/handler.py`)

   - Processes individual HTTP requests
   - Manages connection to backend servers
   - Handles request forwarding and response processing
   - Implements timeout and error handling

3. **HTTP Models** (`src/models.py`)

   - `HTTPRequest`: Represents and parses HTTP requests
   - `HTTPResponse`: Represents and formats HTTP responses
   - Provides clean interfaces for HTTP message handling

4. **Configuration** (`src/config.py`)
   - Manages proxy configuration
   - Supports both programmatic and file-based configuration
   - Handles defaults and validation

### Data Flow

1. Client sends request → ProxyServer accepts connection
2. ProxyServer creates new thread with RequestHandler
3. RequestHandler parses request using HTTPRequest model
4. Request is forwarded to appropriate backend server
5. Response is parsed using HTTPResponse model
6. Response is sent back to client

## Design Decisions and Implementation Details

1. **Threading Model**: Uses a thread-per-connection model for handling concurrent requests. While this approach is simple to implement and understand, it may not scale well for very high concurrent loads.

2. **Pure Python Implementation**: Built using only Python standard library components to demonstrate understanding of networking fundamentals.

3. **Configuration Management**: Supports both programmatic and file-based configuration for flexibility.

4. **Error Handling**: Comprehensive error handling and logging throughout the codebase.

5. **Comprehensive Test Coverage**: Tests follow arrange act assert pattern and we aim to cover all major functions and customer user journeys (CUJs) through both integration and unit tests.

## Limitations

1. No support for HTTPS (TLS/SSL) in the current implementation
2. Thread-per-connection model may not be optimal for high-concurrency scenarios
3. Basic request parsing might not handle all edge cases
4. No request/response manipulation capabilities
5. Limited header processing

## Scaling Considerations

To scale this implementation:

1. Replace threading with async I/O (asyncio) for better performance
2. Implement connection pooling for backend connections
3. Add load balancing capabilities
4. Implement caching layer
5. Add health checks for backend servers

## Security Improvements

1. Implement request rate limiting or DDoS protection
2. Add input validation and sanitization
3. Implement authentication/authorization
4. Add request/response filtering
5. Implement HTTP security headers

## Testing

The test suite includes both unit and integration tests:

1. **Unit Tests** (`tests/test_proxy.py`)

   - Tests individual components in isolation
   - Covers request/response parsing
   - Tests error handling
   - Validates configuration

2. **Integration Tests** (`tests/test_integration.py`)
   - End-to-end testing with real HTTP requests
   - Tests concurrent request handling
   - Validates different HTTP methods
   - Tests error scenarios

Run all the tests using:

```bash
python -m unittest discover tests
```

## Resources Used

1. Gemini Code Assist:

   - Mainly for testing purposes as it's launched a few days ago. Did a pretty bad job though - spent 2 hours of prompting and still wasn't able to run the tests successfully.

2. Cursor:
   - With Sonnet 3.5, still the best coding model so far for most use cases, have a basic running version after only 2 prompts.
