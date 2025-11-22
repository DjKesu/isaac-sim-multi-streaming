# Isaac Sim Multiple Instance Orchestration

A Python-based orchestration layer with web dashboard for managing multiple NVIDIA Isaac Sim instances with WebRTC streaming capabilities.

## Features

- **Multi-Instance Management**: Launch and manage up to 4 concurrent Isaac Sim instances
- **Web Dashboard**: Modern, responsive interface with live WebRTC stream viewing
- **Docker Integration**: Each instance runs in an isolated Docker container
- **Real-time Monitoring**: View instance status, logs, and resource usage
- **WebRTC Streaming**: Access Isaac Sim streams directly in the browser via iframes
- **RESTful API**: Comprehensive API for programmatic control

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Web Dashboard (Browser)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ Instance │ │ Instance │ │ Instance │ │ Instance ││
│  │    0     │ │    1     │ │    2     │ │    3     ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘│
└───────────────────────┬─────────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────▼─────────────────────────────┐
│          FastAPI Orchestration Service               │
│              (Python Backend)                        │
└───────────────────────┬─────────────────────────────┘
                        │ Docker API
┌───────────────────────▼─────────────────────────────┐
│              Docker Engine                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │Isaac Sim │ │Isaac Sim │ │Isaac Sim │ │Isaac Sim ││
│  │Container │ │Container │ │Container │ │Container ││
│  │    0     │ │    1     │ │    2     │ │    3     ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘│
└─────────────────────────────────────────────────────┘
```

## Prerequisites

### System Requirements

- **OS**: Linux (tested on Ubuntu 20.04+)
- **GPU**: NVIDIA GPU with sufficient VRAM (recommended: 32GB+ for 4 instances)
- **RAM**: 32GB+ recommended
- **Docker**: 20.10+
- **NVIDIA Container Toolkit**: For GPU passthrough to Docker containers
- **Python**: 3.10+

### Required Software

1. **Docker** with GPU support
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

2. **NVIDIA Container Toolkit**
   ```bash
   # Add NVIDIA package repositories
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list

   # Install NVIDIA Docker runtime
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

3. **NVIDIA Isaac Sim Docker Image**
   ```bash
   # Pull the Isaac Sim image (requires NGC account)
   docker pull nvcr.io/nvidia/isaac-sim:2023.1.1
   ```

## Installation

1. **Clone the repository** (or ensure you're in the project directory):
   ```bash
   cd isaac-sim-multiple
   ```

2. **Create Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env to customize settings
   ```

## Usage

### Quick Start

Use the provided run script:

```bash
./run.sh
```

Or manually start the service:

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8000
```

### Using Docker Compose

Alternatively, run the entire orchestration service in Docker:

```bash
docker-compose up -d
```

## Configuration

### Environment Variables

Configure the system using environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ISAAC_MAX_INSTANCES` | 4 | Maximum number of concurrent instances |
| `ISAAC_ISAAC_SIM_IMAGE` | `nvcr.io/nvidia/isaac-sim:2023.1.1` | Docker image for Isaac Sim |
| `ISAAC_HTTP_PORT_BASE` | 8211 | Starting HTTP port for instances |
| `ISAAC_WEBRTC_PORT_BASE` | 8011 | Starting WebRTC port for instances |
| `ISAAC_NATIVE_PORT_BASE` | 8899 | Starting native streaming port |
| `ISAAC_MEMORY_LIMIT` | 8g | Memory limit per container |
| `ISAAC_SHM_SIZE` | 2g | Shared memory size per container |
| `ISAAC_GPU_ENABLED` | true | Enable GPU passthrough |
| `ISAAC_ENABLE_WEBRTC` | true | Enable WebRTC streaming |

### Port Allocations

Each instance requires 3 ports:

| Instance | HTTP Port | WebRTC Port | Native Port |
|----------|-----------|-------------|-------------|
| 0 | 8211 | 8011 | 8899 |
| 1 | 8212 | 8012 | 8900 |
| 2 | 8213 | 8013 | 8901 |
| 3 | 8214 | 8014 | 8902 |

**Orchestration API**: Port 8000

## API Documentation

### Endpoints

#### Health Check
```
GET /health
```
Returns Docker connection status.

#### List All Instances
```
GET /api/instances
```
Returns status of all instances.

#### Get Instance Status
```
GET /api/instances/{instance_id}
```
Get detailed status of a specific instance.

#### Start Instance
```
POST /api/instances/start
Body: {"instance_id": 0}
```
Start an Isaac Sim instance.

#### Stop Instance
```
POST /api/instances/stop
Body: {"instance_id": 0}
```
Stop a running instance.

#### Restart Instance
```
POST /api/instances/restart
Body: {"instance_id": 0}
```
Restart an instance.

#### Remove Instance
```
DELETE /api/instances/{instance_id}
```
Remove an instance container.

#### Get Instance Logs
```
GET /api/instances/{instance_id}/logs?tail=100
```
Retrieve container logs.

#### Cleanup All
```
POST /api/cleanup
```
Stop and remove all instances.

#### Get Configuration
```
GET /api/config
```
Returns current system configuration.

### Interactive API Documentation

Once the service is running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Dashboard Usage

### Starting an Instance

1. Navigate to http://localhost:8000
2. Click the **Start** button on any instance card
3. Wait for the container to start (status will change to "running")
4. The WebRTC stream will automatically load in the iframe

### Viewing Streams

Once an instance is running, its WebRTC stream appears in the iframe. You can interact with the Isaac Sim interface directly through the browser.

### Stopping an Instance

Click the **Stop** button to gracefully stop an instance. The container remains available for restart.

### Viewing Logs

Click the **Logs** button to view container output and debug information.

### Cleanup

The **Cleanup All** button in the header stops and removes all instance containers.

## Troubleshooting

### Docker Connection Failed

**Error**: "Failed to initialize Docker client"

**Solution**:
- Ensure Docker daemon is running: `sudo systemctl status docker`
- Verify user is in docker group: `groups $USER`
- Re-login or run: `newgrp docker`

### GPU Not Available

**Error**: Container starts but no GPU access

**Solution**:
- Verify NVIDIA drivers: `nvidia-smi`
- Check NVIDIA Docker runtime: `docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi`
- Ensure NVIDIA Container Toolkit is installed

### Port Already in Use

**Error**: "Port 8211 is already allocated"

**Solution**:
- Check for existing Isaac Sim containers: `docker ps`
- Stop conflicting containers: `docker stop <container_id>`
- Or modify port base in `.env` file

### Container Fails to Start

**Solution**:
1. Check container logs via the dashboard or CLI:
   ```bash
   docker logs isaac-sim-instance-0
   ```
2. Verify Isaac Sim image is available:
   ```bash
   docker images | grep isaac-sim
   ```
3. Ensure sufficient GPU memory is available

### WebRTC Stream Not Loading

**Solution**:
- Wait 30-60 seconds for Isaac Sim to fully start
- Check instance status is "running"
- Verify the HTTP port is accessible: `curl http://localhost:8211`
- Check browser console for errors
- Try refreshing the page

## Performance Optimization

### Running Multiple Instances

When running multiple instances simultaneously:

1. **Reduce memory per instance**: Adjust `ISAAC_MEMORY_LIMIT` in `.env`
2. **Limit GPU memory**: Modify Docker configuration to limit GPU memory fraction
3. **Reduce rendering quality**: Configure Isaac Sim settings in `config/isaac_sim_config.json`
4. **Stagger instance startup**: Start instances one at a time to avoid resource spikes

### Resource Monitoring

Monitor system resources:
```bash
# GPU usage
nvidia-smi -l 1

# Docker stats
docker stats

# System resources
htop
```

## Development

### Project Structure

```
isaac-sim-multiple/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application
│   ├── docker_manager.py    # Docker container management
│   ├── config.py            # Configuration management
│   └── models.py            # Pydantic models
├── static/
│   ├── index.html           # Dashboard HTML
│   ├── css/
│   │   └── style.css        # Dashboard styles
│   └── js/
│       └── app.js           # Dashboard JavaScript
├── config/
│   └── isaac_sim_config.json # Instance configurations
├── requirements.txt         # Python dependencies
├── Dockerfile              # Orchestrator container image
├── docker-compose.yml      # Docker Compose configuration
├── .env.example            # Environment template
├── run.sh                  # Quick start script
└── README.md              # This file
```

### Running in Development Mode

```bash
# With auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Adding Custom Features

1. **Modify backend**: Edit files in `app/`
2. **Update dashboard**: Edit files in `static/`
3. **Change configuration**: Update `app/config.py` and `.env`

## Security Considerations

⚠️ **Important Security Notes**:

1. **Docker Socket**: The orchestrator requires access to Docker socket for container management. This grants significant privileges.
2. **Network Exposure**: By default, the service binds to `0.0.0.0`. For production, use a reverse proxy with authentication.
3. **Resource Limits**: Set appropriate limits to prevent resource exhaustion.
4. **GPU Access**: Docker containers have GPU access, which could be a security concern in multi-tenant environments.

## References

- [NVIDIA Isaac Sim Documentation](https://docs.isaacsim.omniverse.nvidia.com/)
- [Isaac Sim WebRTC Streaming Guide](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/manual_livestream_clients.html)
- [Scalable Streaming with WebRTC](https://medium.com/@BeingOttoman/scalable-streaming-nvidia-omniverse-applications-over-the-internet-using-webrtc-8946a574fef2)

## License

This project is provided as-is for educational and development purposes.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues related to:
- **Isaac Sim**: Consult [NVIDIA Isaac Sim Forums](https://forums.developer.nvidia.com/c/agx-autonomous-machines/isaac/isaac-sim/)
- **This orchestration layer**: Open an issue in the repository


