import socket
import threading
import logging
from typing import Dict

from .handler import RequestHandler

logger = logging.getLogger(__name__)

class ProxyServer:
    """Core server implementation for the reverse proxy."""
    
    def __init__(self, host: str = "localhost", port: int = 8080,
                 backend_servers: Dict[str, str] = None):
        """
        Initialize the proxy server.
        
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
        
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Initialize request handler
        self._handler = RequestHandler(self._backend_servers)
        
        self._running = False

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
        return self._backend_servers.copy()

    @property
    def server_socket(self) -> socket.socket:
        """Get the server socket."""
        return self._server_socket

    def start(self) -> None:
        """Start the proxy server."""
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
                        target=self._handler.handle_client,
                        args=(client_socket, client_address)
                    )
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    if self._running:  # Only log if we're still meant to be running
                        logger.error(f"Server error: {e}")
                
        finally:
            self._server_socket.close()

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