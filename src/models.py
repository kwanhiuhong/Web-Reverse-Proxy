from typing import Dict, Optional, Union
from dataclasses import dataclass

@dataclass
class HTTPRequest:
    """Model representing an HTTP request."""
    method: str
    path: str
    protocol: str
    headers: Dict[str, str]
    raw: str
    body: Optional[bytes] = None

    @classmethod
    def from_raw_data(cls, request_data: str) -> Optional['HTTPRequest']:
        """Create HTTPRequest instance from raw request data."""
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

            return cls(
                method=method,
                path=path,
                protocol=protocol,
                headers=headers,
                raw=request_data
            )
        except Exception:
            return None

@dataclass
class HTTPResponse:
    """Model representing an HTTP response."""
    status_code: int
    status_message: str
    headers: Dict[str, str]
    body: Union[str, bytes]
    raw_response: Optional[bytes] = None

    @classmethod
    def from_raw_response(cls, raw_response: bytes) -> Optional['HTTPResponse']:
        """Create HTTPResponse instance from raw response data."""
        try:
            # Split headers and body
            header_end = raw_response.find(b'\r\n\r\n')
            if header_end == -1:
                return None

            headers_data = raw_response[:header_end].decode('utf-8')
            body = raw_response[header_end + 4:]

            # Parse status line
            status_line, *header_lines = headers_data.split('\r\n')
            protocol, status_code, *status_message = status_line.split(' ')
            
            # Parse headers
            headers = {}
            for line in header_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

            return cls(
                status_code=int(status_code),
                status_message=' '.join(status_message),
                headers=headers,
                body=body,
                raw_response=raw_response
            )
        except Exception:
            return None

    def to_string(self) -> str:
        """Convert response to string format."""
        if isinstance(self.body, bytes):
            body_str = self.body.decode('utf-8', errors='replace')
        else:
            body_str = self.body

        headers_str = '\r\n'.join(f"{k}: {v}" for k, v in self.headers.items())
        return (
            f"HTTP/1.1 {self.status_code} {self.status_message}\r\n"
            f"{headers_str}\r\n"
            f"\r\n"
            f"{body_str}"
        )

    @classmethod
    def create_error(cls, status_code: int, message: str) -> 'HTTPResponse':
        """Create an error response."""
        return cls(
            status_code=status_code,
            status_message=message,
            headers={
                'Content-Type': 'text/plain',
                'Content-Length': str(len(message))
            },
            body=message
        ) 