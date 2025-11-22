# Isaac Sim Multi-Instance Orchestration - Quick Start Guide

Get up and running with Isaac Sim orchestration in minutes!

## Prerequisites

- **GPU**: NVIDIA RTX GPU (RTX 2000+, RTX A-series, A10/A30/A40/A100, etc.)
  - Compute Capability 7.5 or higher required
  - **Tesla V100 and older GPUs are NOT supported**
- **OS**: Ubuntu 20.04+ or compatible Linux
- **Drivers**: NVIDIA drivers 535.x or newer
- **RAM**: 16GB minimum, 32GB recommended
- **Disk**: 30GB free space (for Docker image and cache)

## Quick Setup (Single Command)

```bash
cd ~/isaac-sim-multiple
sudo ./setup.sh
```

This script will automatically:
- ✅ Check GPU compatibility
- ✅ Install Docker (if needed)
- ✅ Install NVIDIA Container Toolkit
- ✅ Pull Isaac Sim Docker image (~20GB, takes 10-30 min)
- ✅ Create volume mount directories
- ✅ Set up Python environment
- ✅ Test GPU access from Docker
- ✅ Configure everything for you

## Manual Setup (Step by Step)

If you prefer to set up manually or troubleshoot:

### 1. Install Docker
```bash
sudo apt update
sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Install NVIDIA Container Toolkit
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 3. Pull Isaac Sim Image
```bash
sudo docker pull nvcr.io/nvidia/isaac-sim:5.1.0
```

### 4. Set Up Directories
```bash
for i in {0..3}; do
    mkdir -p ~/docker/isaac-sim-instance-$i/{cache/main,cache/computecache,logs,config,data,pkg}
    sudo chown -R 1234:1234 ~/docker/isaac-sim-instance-$i
done
```

### 5. Install Python Dependencies
```bash
cd ~/isaac-sim-multiple
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Service

### Start the Orchestration Service
```bash
cd ~/isaac-sim-multiple
./run.sh
```

The service will start on http://localhost:8000

### Access the Dashboard
Open your browser to:
```
http://localhost:8000
```

### Start an Isaac Sim Instance (via API)
```bash
curl -X POST http://localhost:8000/api/instances/start \
  -H 'Content-Type: application/json' \
  -d '{"instance_id": 0}'
```

### Stop an Instance
```bash
curl -X POST http://localhost:8000/api/instances/stop \
  -H 'Content-Type: application/json' \
  -d '{"instance_id": 0}'
```

### Check Instance Status
```bash
curl http://localhost:8000/api/instances/0/status
```

## Port Configuration

Each instance uses 3 ports:

| Instance | HTTP   | WebRTC | Native |
|----------|--------|--------|--------|
| 0        | 8211   | 8011   | 8899   |
| 1        | 8212   | 8012   | 8900   |
| 2        | 8213   | 8013   | 8901   |
| 3        | 8214   | 8014   | 8902   |

- **HTTP Port**: Isaac Sim HTTP server for WebRTC client
- **WebRTC Port**: WebRTC streaming port
- **Native Port**: Native streaming protocol (optional)

## Accessing WebRTC Streams

Once an instance is running, access its WebRTC client at:
```
http://localhost:8211/streaming/webrtc-client/  (for instance 0)
http://localhost:8212/streaming/webrtc-client/  (for instance 1)
# etc.
```

**Note**: Isaac Sim takes 2-3 minutes to fully initialize on first run (shader cache building). Subsequent runs are faster.

## Troubleshooting

### Check GPU is Detected
```bash
nvidia-smi
```

### Check Docker Can Access GPU
```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

### Check Compute Capability
```bash
nvidia-smi --query-gpu=compute_cap --format=csv
```
Should be 7.5 or higher for RTX support.

### View Instance Logs
```bash
sudo docker logs isaac-sim-instance-0
```

### Check Service Logs
```bash
# Service runs in the terminal, check output there
# Or if running as systemd service:
journalctl -u isaac-sim-orchestration -f
```

### Common Issues

**"HydraEngine rtx failed creating scene renderer"**
- Your GPU doesn't support RTX (requires Compute Capability 7.5+)
- Tesla V100 and older GPUs are NOT supported
- Solution: Upgrade to RTX-capable GPU (RTX A6000, RTX 3000+, etc.)

**"Docker not found"**
- Docker is not installed
- Solution: Run `sudo ./setup.sh` or install Docker manually

**"Permission denied" on docker commands**
- User not in docker group
- Solution: `sudo usermod -aG docker $USER` then log out and back in

**Instance stuck in "creating" state**
- First run takes 2-3 minutes to build shader cache
- Solution: Wait and monitor with `sudo docker logs isaac-sim-instance-0`

## Configuration

Edit `.env` file to customize:

```bash
ISAAC_MAX_INSTANCES=4
ISAAC_ISAAC_SIM_IMAGE=nvcr.io/nvidia/isaac-sim:5.1.0
ISAAC_HTTP_PORT_BASE=8211
ISAAC_WEBRTC_PORT_BASE=8011
ISAAC_NATIVE_PORT_BASE=8899
ISAAC_MEMORY_LIMIT=8g
ISAAC_SHM_SIZE=2g
ISAAC_GPU_ENABLED=true
ISAAC_ENABLE_WEBRTC=true
```

## Next Steps

- Review `README.md` for detailed architecture documentation
- Check `app/` directory for API implementation details
- Explore `static/` for frontend dashboard code
- See `WEBRTC_STREAMING.md` for WebRTC client setup

## Support

For issues or questions:
- Check the troubleshooting section above
- Review Isaac Sim documentation: https://docs.isaacsim.omniverse.nvidia.com/
- Check NVIDIA forums: https://forums.developer.nvidia.com/c/omniverse/isaac-sim/

