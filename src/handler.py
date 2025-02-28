import socket
import select
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from .models import HTTPRequest, HTTPResponse

logger = logging.getLogger(__name__)

class RequestHandler:
    """Handles processing of individual HTTP requests."""
    
    def __init__(self, backend_servers: Dict[str, str], timeout: int = 5):
        """
        Initialize the request handler.
        
        Args:
            backend_servers: Dictionary mapping paths to backend server URLs
            timeout: Socket timeout in seconds
        """
        self._backend_servers = backend_servers
        self._timeout = timeout

    def handle_client(self, client_socket: socket.socket, 
                     client_address: Tuple[str, int]) -> None:
        """
        Handle an individual client connection.
        
        Args:
            client_socket: Socket object for client connection
            client_address: Tuple of client's IP and port
        """
        client_socket.settimeout(self._timeout)
        
        try:
            request_data = self._read_request(client_socket)
            if not request_data:
                return

            request = HTTPRequest.from_raw_data(request_data.decode('utf-8'))
            if not request:
                return

            response = self._forward_request(request)
            if response:
                client_socket.sendall(response.raw_response or response.to_string().encode('utf-8'))

        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()

    def _read_request(self, client_socket: socket.socket) -> Optional[bytearray]:
        """Read the complete HTTP request from the client socket."""
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

        return request_data if request_data else None

    def _forward_request(self, request: HTTPRequest) -> Optional[HTTPResponse]:
        """Forward the request to appropriate backend server."""
        backend_url = None
        for path_prefix, server in self._backend_servers.items():
            if request.path.startswith(path_prefix):
                backend_url = server
                break

        if not backend_url:
            return HTTPResponse.create_error(404, "Not Found")

        try:
            parsed_url = urlparse(backend_url)
            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.settimeout(self._timeout)

            try:
                # Connect to backend
                backend_socket.connect((parsed_url.hostname, parsed_url.port or 80))
                
                # Send request
                backend_socket.sendall(request.raw.encode('utf-8'))
                
                # Read response
                response_data = self._read_response(backend_socket)
                if response_data:
                    # Try to parse the response
                    response = HTTPResponse.from_raw_response(response_data)
                    if response:
                        return response
                    
                    # Fallback to basic response if parsing fails
                    return HTTPResponse(
                        status_code=200,
                        status_message="OK",
                        headers={'Content-Type': 'application/octet-stream'},
                        body=response_data
                    )

            finally:
                backend_socket.close()

        except Exception as e:
            logger.error(f"Error forwarding request: {e}")
            return HTTPResponse.create_error(502, "Bad Gateway")

        return None

    def _read_response(self, socket: socket.socket) -> Optional[bytes]:
        """Read the complete response from a socket."""
        response = bytearray()
        while True:
            ready = select.select([socket], [], [], self._timeout)
            if not ready[0]:  # Timeout
                break
            
            data = socket.recv(4096)
            if not data:
                break
            response.extend(data)

        return bytes(response) if response else None 