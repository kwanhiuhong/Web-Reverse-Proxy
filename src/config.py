from typing import Dict, Any
import json
import os

class ProxyConfig:
    """Configuration manager for the reverse proxy."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration with optional config file path.
        
        Args:
            config_path: Path to JSON configuration file
        """
        self.config_path = config_path
        self.config = self._load_default_config()
        
        if config_path and os.path.exists(config_path):
            self._load_config_file()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration settings."""
        return {
            "host": "localhost",
            "port": 8080,
            "backend_servers": {
                "/": "http://localhost:8000"
            },
            "max_connections": 128,
            "buffer_size": 4096
        }

    def _load_config_file(self) -> None:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}")

    def get(self, key: str) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
        
        Returns:
            Configuration value
        """
        return self.config.get(key) 