"""
Configuration for Isaac Sim orchestration layer
"""
from pydantic_settings import BaseSettings
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv
import os

# Get the project root directory (parent of app directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Load .env file from project root before creating settings
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()  # Try to find .env in current directory or parent directories


class Settings(BaseSettings):
    """Application settings"""
    
    # Maximum number of concurrent Isaac Sim instances
    max_instances: int = 4
    
    # Docker configuration (VNC-enabled for browser access)
    isaac_sim_image: str = "isaac-sim-vnc:5.1.0"
    docker_network: str = "bridge"
    
    # Port ranges for each instance
    # Each instance gets: HTTP port, WebRTC port, Native streaming port, VNC web port
    http_port_base: int = 8211
    webrtc_port_base: int = 8011
    native_port_base: int = 8899
    vnc_port_base: int = 6080  # noVNC web interface
    
    # Resource limits per container
    memory_limit: str = "32g"
    shm_size: str = "4g"
    
    # GPU configuration
    gpu_enabled: bool = True
    
    # WebRTC configuration
    enable_webrtc: bool = True
    
    class Config:
        env_prefix = "ISAAC_"
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def get_instance_ports(instance_id: int) -> Dict[str, int]:
    """
    Get port mappings for a specific instance
    
    Args:
        instance_id: Instance identifier (0-based)
        
    Returns:
        Dictionary with port mappings
    """
    if instance_id < 0 or instance_id >= settings.max_instances:
        raise ValueError(f"Instance ID must be between 0 and {settings.max_instances - 1}")
    
    return {
        "http": settings.http_port_base + instance_id,
        "webrtc": settings.webrtc_port_base + instance_id,
        "native": settings.native_port_base + instance_id,
        "vnc": settings.vnc_port_base + instance_id,  # noVNC web interface
    }


def get_all_port_mappings() -> List[Dict[str, int]]:
    """Get port mappings for all possible instances"""
    return [get_instance_ports(i) for i in range(settings.max_instances)]


