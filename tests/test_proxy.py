import unittest
import threading
import time
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server import ProxyServer
from src.models import HTTPRequest, HTTPResponse

class TestReverseProxy(unittest.TestCase):
    """Test cases for ReverseProxy implementation."""

    def setUp(self):
        """Set up test environment before each test."""
        # Arrange
        self.proxy = ProxyServer(
            host="localhost",
            port=8080,
            backend_servers={"/test": "http://localhost:8000"}
        )
        
        # Start proxy in separate thread
        self.proxy_thread = threading.Thread(target=self.proxy.start)
        self.proxy_thread.daemon = True
        self.proxy_thread.start()
        time.sleep(0.1)  # Allow proxy to start

    def test_proxy_initialization(self):
        """Test proxy initialization with custom configuration."""
        # Arrange and Act
        custom_proxy = ProxyServer(
            host="127.0.0.1",
            port=8081,
            backend_servers={"/api": "http://localhost:9000"}
        )
        
        # Assert
        self.assertEqual(custom_proxy.host, "127.0.0.1")
        self.assertEqual(custom_proxy.port, 8081)
        self.assertEqual(
            custom_proxy.backend_servers,
            {"/api": "http://localhost:9000"}
        )

    def test_request_parsing(self):
        """Test HTTP request parsing."""
        # Arrange
        request_data = (
            "GET /test/path HTTP/1.1\r\n"
            "Host: localhost:8080\r\n"
            "User-Agent: Mozilla/5.0\r\n"
            "\r\n"
        )
        
        # Act
        result = HTTPRequest.from_raw_data(request_data)
        
        # Assert
        self.assertEqual(result.method, "GET")
        self.assertEqual(result.path, "/test/path")
        self.assertEqual(result.protocol, "HTTP/1.1")
        self.assertEqual(result.headers['Host'], "localhost:8080")

    def test_error_response(self):
        """Test error response creation."""
        # Act
        response = HTTPResponse.create_error(404, "Not Found")
        response_str = response.to_string()
        
        # Assert
        self.assertIn("HTTP/1.1 404 Not Found", response_str)
        self.assertIn("Content-Type: text/plain", response_str)
        self.assertIn("Content-Length:", response_str)

    def tearDown(self):
        """Clean up after each test."""
        # First shutdown the proxy gracefully
        self.proxy.shutdown()
        # Wait for the proxy thread to finish
        self.proxy_thread.join(timeout=1)
        # Now it's safe to close the socket
        if hasattr(self.proxy, 'server_socket'):
            self.proxy.server_socket.close()

if __name__ == '__main__':
    unittest.main() 