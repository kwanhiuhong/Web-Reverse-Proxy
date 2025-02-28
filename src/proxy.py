import socket
import threading
import logging
from typing import Dict, Tuple, Optional
from urllib.parse import urlparse
import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReverseProxy:
    """
    A simple HTTP reverse proxy implementation.
    Handles incoming HTTP requests and forwards them to backend servers.
    """
    def __init__(self, host: str = "localhost", port: int = 8080, 
                 backend_servers: Dict[str, str] = None):
        """
        Initialize the reverse proxy.
        
        Args:
            host: Host address to bind the proxy
            port: Port number to listen on
            backend_servers: Dictionary mapping paths to backend server URLs
        """
        self._host = host
        self._port = port
        self._backend_servers = backend_servers or {
            "/": "http://localhost:8000"  # Default backend
        }
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._running = False
        self._timeout = 5 # seconds

    @property
    def host(self) -> str:
        """Get the host address."""
        return self._host

    @property
    def port(self) -> int:
        """Get the port number."""
        return self._port

    @property
    def backend_servers(self) -> Dict[str, str]:
        """Get the backend servers configuration."""
        return self._backend_servers.copy()  # Return a copy to prevent direct modification
    
    @property
    def server_socket(self) -> socket.socket:
        """Get the server socket."""
        return self._server_socket

    def shutdown(self) -> None:
        """Shutdown the proxy server gracefully."""
        self._running = False
        # Create a dummy connection to unblock accept()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self._host, self._port))
        except:
            pass
        self._server_socket.close()

    def start(self) -> None:
        """Start the reverse proxy server."""
        self._running = True
        try:
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(128)
            logger.info(f"Reverse proxy started on {self._host}:{self._port}")
            
            while self._running:
                try:
                    client_socket, client_address = self._server_socket.accept()
                    if not self._running:
                        client_socket.close()
                        break
                    # Handle each client in a separate thread
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    if self._running:  # Only log if we're still meant to be running
                        logger.error(f"Server error: {e}")
                
        finally:
            self._server_socket.close()

    def _handle_client(self, client_socket: socket.socket, 
                      client_address: Tuple[str, int]) -> None:
        """
        Handle individual client connections.
        
        Args:
            client_socket: Socket object for client connection
            client_address: Tuple of client's IP and port
        """
        client_socket.settimeout(self._timeout)
        
        try:
            # Read request using select
            request_data = bytearray()
            while True:
                ready = select.select([client_socket], [], [], self._timeout)
                if not ready[0]:  # Timeout
                    break
                
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                
                request_data.extend(chunk)
                if b'\r\n\r\n' in request_data:  # End of headers
                    # If Content-Length is present, read the body
                    headers = request_data.split(b'\r\n\r\n')[0].decode('utf-8')
                    for line in headers.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            content_length = int(line.split(':')[1].strip())
                            while len(request_data) < len(headers) + 4 + content_length:
                                chunk = client_socket.recv(4096)
                                if not chunk:
                                    break
                                request_data.extend(chunk)
                    break

            if not request_data:
                return

            # Parse and forward request
            request = self._parse_request(request_data.decode('utf-8'))
            if not request:
                return

            response = self._forward_request(request)
            if response:
                client_socket.sendall(response.encode('utf-8'))

        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()

    def _parse_request(self, request_data: str) -> Optional[Dict]:
        """
        Parse HTTP request data.
        
        Args:
            request_data: Raw HTTP request string
        
        Returns:
            Dictionary containing parsed request information
        """
        try:
            lines = request_data.split('\n')
            if not lines:
                return None

            # Parse request line
            method, path, protocol = lines[0].strip().split()
            
            # Parse headers
            headers = {}
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    break
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()

            return {
                'method': method,
                'path': path,
                'protocol': protocol,
                'headers': headers,
                'raw': request_data
            }
        except Exception as e:
            logger.error(f"Error parsing request: {e}")
            return None

    def _forward_request(self, request: Dict) -> Optional[str]:
        """
        Forward the request to appropriate backend server.
        
        Args:
            request: Parsed request dictionary
        
        Returns:
            Response string from backend server
        """
        backend_url = None
        for path_prefix, server in self._backend_servers.items():
            if request['path'].startswith(path_prefix):
                backend_url = server
                break

        if not backend_url:
            return self._create_error_response(404, "Not Found")

        try:
            parsed_url = urlparse(backend_url)
            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.settimeout(self._timeout)

            try:
                # Connect to backend
                backend_socket.connect((parsed_url.hostname, parsed_url.port or 80))
                
                # Send request
                backend_socket.sendall(request['raw'].encode('utf-8'))
                
                # Use select for reading response
                response = bytearray()
                while True:
                    ready = select.select([backend_socket], [], [], self._timeout)
                    if not ready[0]:  # Timeout
                        break
                    
                    data = backend_socket.recv(4096)
                    if not data:
                        break
                    response.extend(data)

                return response.decode('utf-8')

            finally:
                backend_socket.close()

        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            return self._create_error_response(502, "Bad Gateway")

    def _create_error_response(self, status_code: int, 
                             message: str) -> str:
        """
        Create an HTTP error response.
        
        Args:
            status_code: HTTP status code
            message: Error message
        
        Returns:
            Formatted HTTP response string
        """
        return (
            f"HTTP/1.1 {status_code} {message}\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(message)}\r\n"
            "\r\n"
            f"{message}"
        ) 