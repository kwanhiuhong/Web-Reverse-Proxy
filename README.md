# cohere_interview

reverse_proxy/
├── src/
│ ├── **init**.py
│ ├── proxy.py
│ └── config.py
├── tests/
│ ├── **init**.py
│ ├── test_proxy.py
│ └── test_config.py
├── README.md
└── requirements.txt

# HTTP Reverse Proxy Implementation

A pure Python implementation of an HTTP reverse proxy without using third-party libraries.

## Getting Started

1. Clone the repository
2. No additional dependencies required (uses standard Python library)
3. Run the proxy:

```python
from src.proxy import ReverseProxy

proxy = ReverseProxy(
    host="localhost",
    port=8080,
    backend_servers={
        "/api": "http://localhost:8000",
        "/web": "http://localhost:8001"
    }
)
proxy.start()
```

## Design Decisions and Implementation Details

1. **Threading Model**: Uses a thread-per-connection model for handling concurrent requests. While this approach is simple to implement and understand, it may not scale well for very high concurrent loads.

2. **Pure Python Implementation**: Built using only Python standard library components to demonstrate understanding of networking fundamentals.

3. **Configuration Management**: Supports both programmatic and file-based configuration for flexibility.

4. **Error Handling**: Comprehensive error handling and logging throughout the codebase.

5. **Good Test Coverage**: Tests follow arrange act assert pattern and we aim to cover all major functions and customer user journeys (CUJs).

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

1. Implement request rate limiting or DDoS protection.
2. Add input validation and sanitization
3. Implement authentication/authorization
4. Add request/response filtering
5. Implement HTTP security headers

## Resources Used

1. Gemini Code Assit:

   - Mainly for testing purposes as it's launched a few days ago. Did a pretty bad job though - spent 2 hours of prompting and still wasn't able to run the tests successfully.

2. Cursor:

   - With Sonnet 3.5, still the best coding model so far for most use cases, have a running version after only 2 prompts.

## Testing

Run the tests using:

```bash
python -m unittest discover tests
```
