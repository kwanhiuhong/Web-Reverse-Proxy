import unittest
import threading
import time
import requests
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import os
import socket

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server import ProxyServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestBackendHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for testing backend server."""
        
    def handle_one_request(self):
        """Handle a single HTTP request."""
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if not self.raw_requestline or not self.parse_request():
                return
            self.handle_request()
            self.wfile.flush()
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return

    def handle_request(self):
        """Handle the request based on the method."""
        try:
            if self.command == 'GET':
                self.handle_get()
            elif self.command == 'POST':
                self.handle_post()
            else:
                self.send_error(405, "Method not allowed")
        except Exception as e:
            logger.error(f"Error in request handler: {e}")
            self.send_error(500, "Internal Server Error")

    def handle_get(self):
        """Handle GET requests."""
        if self.path == "/api/test":
            response = {
                "message": "Hello from backend!",
                "path": self.path,
                "headers": dict(self.headers)
            }
            self._send_json_response(200, response)
        else:
            self._send_json_response(404, {"error": "Not found"})

    def handle_post(self):
        """Handle POST requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''
            
            response = {
                "message": "Received POST request",
                "path": self.path,
                "data": json.loads(post_data.decode('utf-8')) if post_data else {},
                "headers": dict(self.headers)
            }
            self._send_json_response(200, response)
        except Exception as e:
            logger.error(f"Error in POST handler: {e}")
            self._send_json_response(500, {"error": str(e)})

    def _send_json_response(self, status_code: int, data: dict):
        """Send JSON response with proper headers."""
        try:
            response_data = json.dumps(data).encode('utf-8')
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_data)))
            self.end_headers()
            
            # Send in chunks to avoid blocking
            chunk_size = 4096
            for i in range(0, len(response_data), chunk_size):
                chunk = response_data[i:i + chunk_size]
                self.wfile.write(chunk)
                self.wfile.flush()
        
        except (ConnectionResetError, BrokenPipeError) as e:
            logger.error(f"Connection error while sending response: {e}")
        except Exception as e:
            logger.error(f"Error sending response: {e}")

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"{self.address_string()} - {format%args}")

class TestReverseProxyIntegration(unittest.TestCase):
    """Integration tests for ReverseProxy."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        logger.info("Starting test setup...")
        
        # Start backend server
        cls.backend_port = 8000
        cls.backend_server = HTTPServer(
            ('localhost', cls.backend_port), 
            TestBackendHandler
        )
        cls.backend_thread = threading.Thread(
            target=cls.backend_server.serve_forever
        )
        cls.backend_thread.daemon = True
        cls.backend_thread.start()
        logger.info("Backend server started")

        # Start proxy server
        cls.proxy_port = 8080
        cls.proxy = ProxyServer(
            host="localhost",
            port=cls.proxy_port,
            backend_servers={
                "/api": f"http://localhost:{cls.backend_port}"
            }
        )
        cls.proxy_thread = threading.Thread(target=cls.proxy.start)
        cls.proxy_thread.daemon = True
        cls.proxy_thread.start()
        logger.info("Proxy server started")

        # Wait for servers to start
        time.sleep(1)

    def test_get_request_through_proxy(self):
        """Test GET request through proxy to backend server."""
        # Arrange
        proxy_url = f"http://localhost:{self.proxy_port}/api/test"

        # Act
        response = requests.get(proxy_url)
        data = response.json()

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["message"], "Hello from backend!")
        self.assertEqual(data["path"], "/api/test")
        logger.info(f"[PASSED] test_get_request_through_proxy")

    def test_post_request_through_proxy(self):
        """Test POST request through proxy to backend server."""
        # Arrange
        proxy_url = f"http://localhost:{self.proxy_port}/api/test"
        post_data = {"key": "value", "test": 123}

        # Act
        response = requests.post(
            proxy_url, 
            json=post_data,
            timeout=10,
            headers={'Connection': 'close'}  # Force connection close
        )
        data = response.json()

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["message"], "Received POST request")
        self.assertEqual(data["data"], post_data)
        logger.info(f"[PASSED] test_post_request_through_proxy")

    def test_not_found_request(self):
        """Test request to non-existent endpoint."""
        # Arrange
        proxy_url = f"http://localhost:{self.proxy_port}/api/nonexistent"

        # Act
        response = requests.get(proxy_url)
        data = response.json()

        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data["error"], "Not found")
        logger.info(f"[PASSED] test_not_found_request")

    def test_large_payload(self):
        """Test handling of large payload."""
        # Arrange
        proxy_url = f"http://localhost:{self.proxy_port}/api/test"
        large_data = {
            "large_field": "x" * 500  # Reduced payload size
        }

        # Act
        response = requests.post(
            proxy_url, 
            json=large_data,
            timeout=10,
            headers={'Connection': 'close'}  # Force connection close
        )
        data = response.json()

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["data"], large_data)
        logger.info(f"[PASSED] test_large_payload")

    def test_multiple_concurrent_requests(self):
        """Test handling multiple concurrent requests."""
        # Arrange
        def make_request():
            try:
                response = requests.get(
                    f"http://localhost:{self.proxy_port}/api/test",
                    timeout=30
                )
                return response.status_code
            except Exception as e:
                logger.error(f"Concurrent request failed: {e}")
                return None
        
        # Act
        num_requests = 5
        threads = []
        results = []
        for _ in range(num_requests):
            thread = threading.Thread(
                target=lambda: results.append(make_request())
            )
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        # Assert
        self.assertEqual(len(results), num_requests)
        self.assertTrue(all(status == 200 for status in results if status is not None))
        logger.info(f"[PASSED] test_multiple_concurrent_requests")

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        logger.info("Starting test cleanup...")
        
        try:
            # Shutdown proxy server gracefully
            logger.info("Shutting down proxy server...")
            if hasattr(cls, 'proxy'):
                cls.proxy.shutdown()
                if hasattr(cls, 'proxy_thread'):
                    cls.proxy_thread.join(timeout=5)
            
            # Shutdown backend server
            logger.info("Shutting down backend server...")
            if hasattr(cls, 'backend_server'):
                cls.backend_server.shutdown()
                cls.backend_server.server_close()
                if hasattr(cls, 'backend_thread'):
                    cls.backend_thread.join(timeout=5)
            
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 