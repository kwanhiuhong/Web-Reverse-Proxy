import unittest
import threading
import time
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.proxy import ReverseProxy

class TestReverseProxy(unittest.TestCase):
    """Test cases for ReverseProxy implementation."""

    def setUp(self):
        """Set up test environment before each test."""
        # Arrange
        self.proxy = ReverseProxy(
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
        # Arrange
        custom_proxy = ReverseProxy(
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

    def test_parse_request(self):
        """Test HTTP request parsing."""
        # Arrange
        request_data = (
            "GET /test/path HTTP/1.1\r\n"
            "Host: localhost:8080\r\n"
            "User-Agent: Mozilla/5.0\r\n"
            "\r\n"
        )
        
        # Act
        result = self.proxy._parse_request(request_data)
        
        # Assert
        self.assertEqual(result['method'], "GET")
        self.assertEqual(result['path'], "/test/path")
        self.assertEqual(result['protocol'], "HTTP/1.1")
        self.assertEqual(result['headers']['Host'], "localhost:8080")

    def test_create_error_response(self):
        """Test error response creation."""
        # Act
        response = self.proxy._create_error_response(404, "Not Found")
        
        # Assert
        self.assertIn("HTTP/1.1 404 Not Found", response)
        self.assertIn("Content-Type: text/plain", response)
        self.assertIn("Content-Length:", response)

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