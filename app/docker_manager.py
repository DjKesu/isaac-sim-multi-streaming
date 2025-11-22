"""
Docker container manager for Isaac Sim instances
"""
import docker
from docker.models.containers import Container
from docker.errors import DockerException, NotFound, APIError
from typing import Dict, Optional, List
import logging
import subprocess
from .config import settings, get_instance_ports

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker containers for Isaac Sim instances"""
    
    def __init__(self):
        """Initialize Docker client"""
        self.client = None
        self.containers: Dict[int, Container] = {}
        self.container_prefix = "isaac-sim-instance"
        self.docker_available = False
        
        try:
            # Try multiple connection methods
            # Method 1: Try default (from_env) but catch and try explicit socket
            try:
                self.client = docker.from_env()
                self.client.ping()
            except Exception as e1:
                logger.debug(f"from_env failed: {e1}")
                # Method 2: Try explicit unix socket
                try:
                    self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
                    self.client.ping()
                except Exception as e2:
                    logger.debug(f"explicit socket failed: {e2}")
                    raise e2
            
            self.docker_available = True
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Docker Python client not available: {e}")
            # Check if Docker CLI is available as fallback
            try:
                import subprocess
                result = subprocess.run(['docker', 'ps'], capture_output=True, timeout=5, check=True)
                logger.info("Docker CLI is available - using subprocess fallback")
                self.docker_available = True
                self.client = None  # Will use subprocess instead
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as cli_error:
                logger.error(f"Docker CLI also not available: {cli_error}")
                logger.error("Service cannot manage containers. Please ensure Docker is installed and running.")
                self.docker_available = False
                self.client = None
    
    def _check_docker(self):
        """Check if Docker is available and raise error if not"""
        if not self.docker_available:
            raise DockerException("Docker is not available. Please install and start Docker service.")
    
    def _docker_cmd(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a docker command via subprocess"""
        import subprocess
        full_cmd = ['docker'] + cmd
        try:
            return subprocess.run(full_cmd, capture_output=True, text=True, check=check, timeout=30)
        except subprocess.TimeoutExpired:
            raise DockerException(f"Docker command timed out: {' '.join(full_cmd)}")
        except subprocess.CalledProcessError as e:
            raise DockerException(f"Docker command failed: {' '.join(full_cmd)} - {e.stderr}")
    
    def _container_exists(self, container_name: str) -> bool:
        """Check if container exists using subprocess"""
        try:
            result = self._docker_cmd(['ps', '-a', '--filter', f'name={container_name}', '--format', '{{.Names}}'], check=False)
            return container_name in result.stdout
        except Exception:
            return False
    
    def _get_container_status(self, container_name: str) -> Optional[str]:
        """Get container status using subprocess"""
        try:
            result = self._docker_cmd(['ps', '-a', '--filter', f'name={container_name}', '--format', '{{.Status}}'], check=False)
            if result.stdout.strip():
                status_line = result.stdout.strip().split()[0]
                return status_line.lower()
            return None
        except Exception:
            return None
    
    def _get_container_name(self, instance_id: int) -> str:
        """Generate container name for instance"""
        return f"{self.container_prefix}-{instance_id}"
    
    def _build_container_config(self, instance_id: int) -> Dict:
        """
        Build Docker container configuration for an instance
        According to: https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html
        
        Args:
            instance_id: Instance identifier (0-based)
            
        Returns:
            Dictionary with container configuration
        """
        import os
        ports = get_instance_ports(instance_id)
        container_name = self._get_container_name(instance_id)
        
        # Get home directory for volume mounts
        home_dir = os.path.expanduser("~")
        base_cache_dir = f"{home_dir}/docker/isaac-sim-{instance_id}"
        
        # Volume mounts as per official documentation
        volumes = {
            f"{base_cache_dir}/cache/main": {"bind": "/isaac-sim/.cache", "mode": "rw"},
            f"{base_cache_dir}/cache/computecache": {"bind": "/isaac-sim/.nv/ComputeCache", "mode": "rw"},
            f"{base_cache_dir}/logs": {"bind": "/isaac-sim/.nvidia-omniverse/logs", "mode": "rw"},
            f"{base_cache_dir}/config": {"bind": "/isaac-sim/.nvidia-omniverse/config", "mode": "rw"},
            f"{base_cache_dir}/data": {"bind": "/isaac-sim/.local/share/ov/data", "mode": "rw"},
            f"{base_cache_dir}/pkg": {"bind": "/isaac-sim/.local/share/ov/pkg", "mode": "rw"},
        }
        
        # Create volume directories if they don't exist
        for host_path in volumes.keys():
            os.makedirs(host_path, exist_ok=True)
            # Set ownership to 1234:1234 (Isaac Sim container user)
            try:
                import subprocess
                subprocess.run(["sudo", "chown", "-R", "1234:1234", host_path], 
                             check=False, capture_output=True)
            except Exception as e:
                logger.warning(f"Could not set permissions on {host_path}: {e}")
        
        # Environment variables for Isaac Sim 5.1.0
        environment = {
            "ACCEPT_EULA": "Y",
            "PRIVACY_CONSENT": "Y",
            "DISPLAY": ":1",  # VNC Xvfb display
        }
        
        # GPU configuration
        device_requests = []
        if settings.gpu_enabled:
            device_requests = [
                docker.types.DeviceRequest(
                    count=-1,  # All GPUs
                    capabilities=[['gpu', 'compute', 'utility']]
                )
            ]
        
        # Build command for Isaac Sim
        if settings.enable_webrtc:
            # Use VNC-enabled startup script
            command = [
                "/isaac-sim/start_with_vnc.sh",
                "./isaac-sim.sh",  # Use full GUI version with VNC
                "--allow-root",
            ]
        else:
            command = ["/isaac-sim/start_with_vnc.sh", "./runheadless.sh", "-v"]
        
        config = {
            "image": settings.isaac_sim_image,
            "name": container_name,
            "detach": True,
            "volumes": volumes,
            "environment": environment,
            "device_requests": device_requests,
            "network_mode": "host",  # Use host networking as per documentation
            "runtime": "nvidia",  # Explicitly set NVIDIA runtime for GPU access
            "shm_size": settings.shm_size,  # Shared memory for GPU operations
            "mem_limit": settings.memory_limit,  # Memory limit per container
            "remove": False,
            "auto_remove": False,
            "user": "1234:1234",  # Run as rootless user
            "command": command,
        }
        
        return config
    
    def start_instance(self, instance_id: int) -> Dict:
        """
        Start an Isaac Sim instance
        
        Args:
            instance_id: Instance identifier (0-based)
            
        Returns:
            Dictionary with instance status
        """
        self._check_docker()
        
        if instance_id < 0 or instance_id >= settings.max_instances:
            raise ValueError(f"Instance ID must be between 0 and {settings.max_instances - 1}")
        
        container_name = self._get_container_name(instance_id)
        
        # Use subprocess if Python client not available
        if self.client is None:
            # Check if container exists
            if self._container_exists(container_name):
                status = self._get_container_status(container_name)
                if status == "running" or "Up" in status:
                    logger.info(f"Instance {instance_id} is already running")
                    return self.get_instance_status(instance_id)
                else:
                    # Start existing stopped container
                    logger.info(f"Starting existing container for instance {instance_id}")
                    self._docker_cmd(['start', container_name])
                    return self.get_instance_status(instance_id)
            
            # Create new container using subprocess
            logger.info(f"Creating new container for instance {instance_id}")
            config = self._build_container_config(instance_id)
            
            # Build docker run command
            cmd = ['run', '-d', '--name', container_name]
            cmd.extend(['--runtime', 'nvidia'])
            cmd.extend(['--network', 'host'])
            cmd.extend(['--shm-size', config['shm_size']])
            cmd.extend(['--memory', config['mem_limit']])
            cmd.extend(['--user', config['user']])
            
            # Add volumes
            for host_path, bind_info in config['volumes'].items():
                cmd.extend(['-v', f"{host_path}:{bind_info['bind']}"])
            
            # Add environment variables
            for key, value in config['environment'].items():
                cmd.extend(['-e', f"{key}={value}"])
            
            # Add device requests (GPU)
            if config.get('device_requests'):
                cmd.extend(['--gpus', 'all'])
            
            # Add image and command
            cmd.append(config['image'])
            cmd.extend(config['command'])
            
            self._docker_cmd(cmd)
            logger.info(f"Successfully started instance {instance_id}")
            return self.get_instance_status(instance_id)
        
        # Use Python client if available
        # Check if container already exists
        try:
            existing = self.client.containers.get(container_name)
            if existing.status == "running":
                logger.info(f"Instance {instance_id} is already running")
                self.containers[instance_id] = existing
                return self.get_instance_status(instance_id)
            else:
                # Start existing stopped container
                logger.info(f"Starting existing container for instance {instance_id}")
                existing.start()
                self.containers[instance_id] = existing
                return self.get_instance_status(instance_id)
        except NotFound:
            # Container doesn't exist, create it
            pass
        
        try:
            logger.info(f"Creating new container for instance {instance_id}")
            config = self._build_container_config(instance_id)
            container = self.client.containers.run(**config)
            self.containers[instance_id] = container
            logger.info(f"Successfully started instance {instance_id}")
            return self.get_instance_status(instance_id)
        except APIError as e:
            logger.error(f"Failed to start instance {instance_id}: {e}")
            raise
    
    def stop_instance(self, instance_id: int) -> Dict:
        """
        Stop an Isaac Sim instance
        
        Args:
            instance_id: Instance identifier (0-based)
            
        Returns:
            Dictionary with instance status
        """
        container_name = self._get_container_name(instance_id)
        
        # Use subprocess if Python client not available
        if self.client is None:
            if not self._container_exists(container_name):
                logger.warning(f"Container for instance {instance_id} not found")
                return self.get_instance_status(instance_id)
            
            status = self._get_container_status(container_name)
            if status and ("running" in status.lower() or "up" in status.lower()):
                logger.info(f"Stopping instance {instance_id}")
                self._docker_cmd(['stop', container_name], check=False)
            else:
                logger.info(f"Instance {instance_id} is not running")
            
            if instance_id in self.containers:
                del self.containers[instance_id]
            
            return self.get_instance_status(instance_id)
        
        # Use Python client if available
        try:
            container = self.client.containers.get(container_name)
            if container.status == "running":
                logger.info(f"Stopping instance {instance_id}")
                container.stop(timeout=10)
                if instance_id in self.containers:
                    del self.containers[instance_id]
            else:
                logger.info(f"Instance {instance_id} is not running")
        except NotFound:
            logger.warning(f"Container for instance {instance_id} not found")
        except APIError as e:
            logger.error(f"Failed to stop instance {instance_id}: {e}")
            raise
        
        return self.get_instance_status(instance_id)
    
    def restart_instance(self, instance_id: int) -> Dict:
        """
        Restart an Isaac Sim instance
        
        Args:
            instance_id: Instance identifier (0-based)
            
        Returns:
            Dictionary with instance status
        """
        logger.info(f"Restarting instance {instance_id}")
        self.stop_instance(instance_id)
        return self.start_instance(instance_id)
    
    def remove_instance(self, instance_id: int) -> Dict:
        """
        Remove an Isaac Sim instance container
        
        Args:
            instance_id: Instance identifier (0-based)
            
        Returns:
            Dictionary with result
        """
        container_name = self._get_container_name(instance_id)
        
        # Use subprocess if Python client not available
        if self.client is None:
            if not self._container_exists(container_name):
                logger.warning(f"Container for instance {instance_id} not found")
                return {"status": "not_found", "instance_id": instance_id}
            
            # Stop if running
            status = self._get_container_status(container_name)
            if status and ("running" in status.lower() or "up" in status.lower()):
                self._docker_cmd(['stop', container_name], check=False)
            
            # Remove container
            self._docker_cmd(['rm', container_name], check=False)
            if instance_id in self.containers:
                del self.containers[instance_id]
            logger.info(f"Removed instance {instance_id}")
            return {"status": "removed", "instance_id": instance_id}
        
        # Use Python client if available
        try:
            container = self.client.containers.get(container_name)
            if container.status == "running":
                container.stop(timeout=10)
            container.remove()
            if instance_id in self.containers:
                del self.containers[instance_id]
            logger.info(f"Removed instance {instance_id}")
            return {"status": "removed", "instance_id": instance_id}
        except NotFound:
            logger.warning(f"Container for instance {instance_id} not found")
            return {"status": "not_found", "instance_id": instance_id}
        except APIError as e:
            logger.error(f"Failed to remove instance {instance_id}: {e}")
            raise
    
    def get_instance_status(self, instance_id: int) -> Dict:
        """
        Get status of an Isaac Sim instance
        
        Args:
            instance_id: Instance identifier (0-based)
            
        Returns:
            Dictionary with instance status and details
        """
        container_name = self._get_container_name(instance_id)
        ports = get_instance_ports(instance_id)
        
        # Use subprocess if Python client not available
        if self.client is None:
            exists = self._container_exists(container_name)
            if not exists:
                return {
                    "instance_id": instance_id,
                    "status": "not_created",
                    "ports": ports,
                    "webrtc_url": f"http://localhost:{ports['http']}/streaming/webrtc-client/",
                }
            
            status = self._get_container_status(container_name)
            if status is None:
                status = "unknown"
            
            # Get container ID
            try:
                result = self._docker_cmd(['ps', '-a', '--filter', f'name={container_name}', '--format', '{{.ID}}'], check=False)
                container_id = result.stdout.strip()[:12] if result.stdout.strip() else ""
            except Exception:
                container_id = ""
            
            # Get created time
            try:
                result = self._docker_cmd(['inspect', '--format', '{{.Created}}', container_name], check=False)
                created = result.stdout.strip() if result.returncode == 0 else ""
            except Exception:
                created = ""
            
            return {
                "instance_id": instance_id,
                "status": status,
                "container_id": container_id,
                "ports": ports,
                "webrtc_url": f"http://localhost:{ports['http']}/streaming/webrtc-client/",
                "created": created,
            }
        
        # Use Python client if available
        try:
            container = self.client.containers.get(container_name)
            container.reload()  # Refresh container info
            
            return {
                "instance_id": instance_id,
                "status": container.status,
                "container_id": container.id[:12],
                "ports": ports,
                "webrtc_url": f"http://localhost:{ports['http']}/streaming/webrtc-client/",
                "created": container.attrs.get("Created", ""),
            }
        except NotFound:
            return {
                "instance_id": instance_id,
                "status": "not_created",
                "ports": ports,
                "webrtc_url": f"http://localhost:{ports['http']}/streaming/webrtc-client/",
            }
    
    def get_all_instances_status(self) -> List[Dict]:
        """
        Get status of all possible instances
        
        Returns:
            List of instance status dictionaries
        """
        return [self.get_instance_status(i) for i in range(settings.max_instances)]
    
    def cleanup_all(self) -> Dict:
        """
        Stop and remove all Isaac Sim instances
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Cleaning up all instances")
        results = []
        
        for instance_id in range(settings.max_instances):
            try:
                result = self.remove_instance(instance_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error cleaning up instance {instance_id}: {e}")
                results.append({
                    "instance_id": instance_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return {"results": results}
    
    def get_logs(self, instance_id: int, tail: int = 100) -> str:
        """
        Get logs from an instance
        
        Args:
            instance_id: Instance identifier (0-based)
            tail: Number of lines to retrieve
            
        Returns:
            Log string
        """
        container_name = self._get_container_name(instance_id)
        
        # Use subprocess if Python client not available
        if self.client is None:
            if not self._container_exists(container_name):
                return f"Container for instance {instance_id} not found"
            
            try:
                result = self._docker_cmd(['logs', '--tail', str(tail), '--timestamps', container_name], check=False)
                return result.stdout if result.returncode == 0 else f"Error retrieving logs: {result.stderr}"
            except Exception as e:
                return f"Error retrieving logs: {str(e)}"
        
        # Use Python client if available
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode('utf-8')
        except NotFound:
            return f"Container for instance {instance_id} not found"
        except Exception as e:
            return f"Error retrieving logs: {str(e)}"

