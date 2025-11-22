"""
Configuration for Isaac Sim orchestration layer
"""
from pydantic_settings import BaseSettings
from typing import Dict, List


class Settings(BaseSettings):
    """Application settings"""
    
    # Maximum number of concurrent Isaac Sim instances
    max_instances: int = 4
    
    # Docker configuration
    isaac_sim_image: str = "nvcr.io/nvidia/isaac-sim:5.1.0"
    docker_network: str = "bridge"
    
    # Port ranges for each instance
    # Each instance gets: HTTP port, WebRTC port, Native streaming port
    http_port_base: int = 8211
    webrtc_port_base: int = 8011
    native_port_base: int = 8899
    
    # Resource limits per container
    memory_limit: str = "8g"
    shm_size: str = "2g"
    
    # GPU configuration
    gpu_enabled: bool = True
    
    # WebRTC configuration
    enable_webrtc: bool = True
    
    class Config:
        env_prefix = "ISAAC_"


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
    }


def get_all_port_mappings() -> List[Dict[str, int]]:
    """Get port mappings for all possible instances"""
    return [get_instance_ports(i) for i in range(settings.max_instances)]


