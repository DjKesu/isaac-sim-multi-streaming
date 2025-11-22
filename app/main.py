"""
FastAPI application for Isaac Sim orchestration
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path

from .docker_manager import DockerManager
from .models import (
    InstanceStatus,
    StartInstanceRequest,
    StopInstanceRequest,
    RestartInstanceRequest,
    RemoveInstanceRequest,
    LogsRequest,
    ApiResponse,
    InstancesListResponse,
)
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Isaac Sim Orchestration API",
    description="API for managing multiple Isaac Sim instances with WebRTC streaming",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Docker manager
docker_manager = DockerManager()

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Isaac Sim Orchestration API")
    logger.info(f"Max instances: {settings.max_instances}")
    logger.info(f"Docker image: {settings.isaac_sim_image}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Isaac Sim Orchestration API")
    # Optionally cleanup all containers on shutdown
    # docker_manager.cleanup_all()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard page"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse(
        content="<h1>Isaac Sim Orchestration</h1><p>Dashboard not found. Please ensure static/index.html exists.</p>"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        docker_manager.client.ping()
        return {"status": "healthy", "docker": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "docker": "disconnected", "error": str(e)}
        )


@app.get("/api/instances", response_model=InstancesListResponse)
async def list_instances():
    """Get status of all instances"""
    try:
        instances = docker_manager.get_all_instances_status()
        return InstancesListResponse(instances=instances)
    except Exception as e:
        logger.error(f"Error listing instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list instances: {str(e)}"
        )


@app.get("/api/instances/{instance_id}", response_model=InstanceStatus)
async def get_instance(instance_id: int):
    """Get status of a specific instance"""
    if instance_id < 0 or instance_id >= settings.max_instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance ID must be between 0 and {settings.max_instances - 1}"
        )
    
    try:
        instance_status = docker_manager.get_instance_status(instance_id)
        return InstanceStatus(**instance_status)
    except Exception as e:
        logger.error(f"Error getting instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get instance status: {str(e)}"
        )


@app.post("/api/instances/start", response_model=ApiResponse)
async def start_instance(request: StartInstanceRequest):
    """Start an Isaac Sim instance"""
    try:
        result = docker_manager.start_instance(request.instance_id)
        return ApiResponse(
            success=True,
            message=f"Instance {request.instance_id} started successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting instance {request.instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start instance: {str(e)}"
        )


@app.post("/api/instances/stop", response_model=ApiResponse)
async def stop_instance(request: StopInstanceRequest):
    """Stop an Isaac Sim instance"""
    try:
        result = docker_manager.stop_instance(request.instance_id)
        return ApiResponse(
            success=True,
            message=f"Instance {request.instance_id} stopped successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error stopping instance {request.instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop instance: {str(e)}"
        )


@app.post("/api/instances/restart", response_model=ApiResponse)
async def restart_instance(request: RestartInstanceRequest):
    """Restart an Isaac Sim instance"""
    try:
        result = docker_manager.restart_instance(request.instance_id)
        return ApiResponse(
            success=True,
            message=f"Instance {request.instance_id} restarted successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error restarting instance {request.instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart instance: {str(e)}"
        )


@app.delete("/api/instances/{instance_id}", response_model=ApiResponse)
async def remove_instance(instance_id: int):
    """Remove an Isaac Sim instance container"""
    if instance_id < 0 or instance_id >= settings.max_instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance ID must be between 0 and {settings.max_instances - 1}"
        )
    
    try:
        result = docker_manager.remove_instance(instance_id)
        return ApiResponse(
            success=True,
            message=f"Instance {instance_id} removed successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error removing instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove instance: {str(e)}"
        )


@app.get("/api/instances/{instance_id}/logs")
async def get_instance_logs(instance_id: int, tail: int = 100):
    """Get logs from an instance"""
    if instance_id < 0 or instance_id >= settings.max_instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance ID must be between 0 and {settings.max_instances - 1}"
        )
    
    if tail < 1 or tail > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tail parameter must be between 1 and 1000"
        )
    
    try:
        logs = docker_manager.get_logs(instance_id, tail=tail)
        return {"instance_id": instance_id, "logs": logs}
    except Exception as e:
        logger.error(f"Error getting logs for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get logs: {str(e)}"
        )


@app.post("/api/cleanup", response_model=ApiResponse)
async def cleanup_all_instances():
    """Stop and remove all instances"""
    try:
        result = docker_manager.cleanup_all()
        return ApiResponse(
            success=True,
            message="All instances cleaned up successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup instances: {str(e)}"
        )


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "max_instances": settings.max_instances,
        "isaac_sim_image": settings.isaac_sim_image,
        "http_port_base": settings.http_port_base,
        "webrtc_port_base": settings.webrtc_port_base,
        "native_port_base": settings.native_port_base,
        "memory_limit": settings.memory_limit,
        "gpu_enabled": settings.gpu_enabled,
        "webrtc_enabled": settings.enable_webrtc,
    }


