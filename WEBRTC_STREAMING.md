# Isaac Sim WebRTC Streaming Guide

## Overview

Isaac Sim uses WebRTC for streaming the 3D viewport from the server to clients. This orchestration layer manages multiple Isaac Sim instances, each accessible via WebRTC.

## Important: GPU Access Issue Fixed

The orchestration system now properly configures Docker containers with:
- `--runtime=nvidia` flag for explicit NVIDIA runtime
- `--gpus all` for GPU passthrough
- Proper volume mounts for cache and configuration

## How WebRTC Streaming Works

According to the [official documentation](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html), Isaac Sim provides two ways to access the WebRTC stream:

### Option 1: Official WebRTC Streaming Client (Recommended)

**Best for**: Production use, better performance, more reliable

1. Download the Isaac Sim WebRTC Streaming Client from the [official releases](https://github.com/isaac-sim/IsaacSim-dockerfiles/releases)
2. Install and run the client application
3. Enter the server IP address (e.g., `localhost` or your server IP)
4. Click "Connect" to begin streaming

**Advantages**:
- Optimized for Isaac Sim streaming
- Better performance and lower latency
- More stable connection handling

### Option 2: Web-Based Client

**Best for**: Quick testing, development, browser-based access

Access the web-based WebRTC client directly at:
```
http://localhost:PORT/streaming/webrtc-client/
```

Where PORT is:
- Instance 0: `8211`
- Instance 1: `8212`
- Instance 2: `8213`
- Instance 3: `8214`

**Example**:
```
http://localhost:8211/streaming/webrtc-client/
```

## Dashboard iframe Integration

The orchestration dashboard embeds the web-based client in iframes. While this works for demonstration purposes, be aware:

- Some browsers may have security restrictions with iframe embedding
- Performance may be slightly lower than the standalone client
- For production deployments, use the official client application

## Startup Time

**Important**: Isaac Sim takes time to fully initialize:

1. **Container Start**: ~10 seconds
2. **Extension Loading**: ~30-60 seconds
3. **Shader Compilation**: 2-5 minutes (first run), ~30 seconds (subsequent runs)
4. **Streaming Ready**: Look for this message in logs:
   ```
   Isaac Sim Full Streaming App is loaded.
   ```

## Troubleshooting

### GPU Not Detected

**Error**: `CUDA libs are present, but no suitable CUDA GPU was found!`

**Solution**: Ensure `--runtime=nvidia` flag is set (now included in the updated docker_manager.py)

### Streaming Plugin Failed

**Error**: `Failed to acquire rtx::resourcemanager::ResourceManager!`

**Cause**: This happens when the GPU is not accessible to the container

**Solution**: 
1. Verify NVIDIA Container Toolkit is installed
2. Restart Docker: `sudo systemctl restart docker`
3. Test GPU access: `docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi`

### WebRTC Client Shows Blank Screen

**Possible Causes**:
1. Isaac Sim is still loading (wait for "Full Streaming App is loaded" message)
2. GPU not properly passed to container
3. Network/firewall issues blocking WebRTC ports

**Solution**:
1. Check logs: Click "Logs" button in dashboard or run `docker logs isaac-sim-instance-X`
2. Wait 2-5 minutes for complete initialization
3. Try the standalone WebRTC client instead of browser

### High Memory Usage

Isaac Sim is resource-intensive. Each instance requires:
- ~8GB RAM
- Significant GPU VRAM
- CPU cores for physics simulation

Adjust `memory_limit` in `.env` if needed.

## Architecture

```
Browser/Client
     ↓ (WebRTC)
Web Dashboard (localhost:8000)
     ↓ (iframe or link)
Isaac Sim WebRTC Client (localhost:8211-8214)
     ↓ (WebRTC stream)
Isaac Sim Container (with GPU access)
     ↓ (CUDA/RTX)
NVIDIA GPU
```

## Configuration

### Port Mapping

Each instance uses 3 ports:
- **HTTP Port** (8211-8214): Main web interface and WebRTC client
- **WebRTC Port** (8011-8014): WebRTC signaling and data
- **Native Port** (8899-8902): Native streaming protocol

### Host Networking

The containers use `--network=host` for simplicity and to avoid port mapping issues with WebRTC.

## Performance Tips

1. **Use SSD for cache**: Mount cache volumes on SSD for faster shader loading
2. **Limit concurrent instances**: Start with 1-2 instances to verify GPU memory
3. **Monitor GPU usage**: Use `nvidia-smi` or `watch -n 1 nvidia-smi` to monitor VRAM
4. **Close unused instances**: Stop instances when not in use to free resources

## References

- [Isaac Sim Container Documentation](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html)
- [Isaac Sim WebRTC Client Releases](https://github.com/isaac-sim/IsaacSim-dockerfiles/releases)
- [NVIDIA Container Toolkit Documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

