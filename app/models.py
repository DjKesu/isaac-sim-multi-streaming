"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class InstanceStatus(BaseModel):
    """Instance status response model"""
    instance_id: int
    status: str
    ports: Dict[str, int]
    webrtc_url: str
    container_id: Optional[str] = None
    created: Optional[str] = None


class StartInstanceRequest(BaseModel):
    """Request to start an instance"""
    instance_id: int = Field(..., ge=0, lt=4, description="Instance ID (0-3)")


class StopInstanceRequest(BaseModel):
    """Request to stop an instance"""
    instance_id: int = Field(..., ge=0, lt=4, description="Instance ID (0-3)")


class RestartInstanceRequest(BaseModel):
    """Request to restart an instance"""
    instance_id: int = Field(..., ge=0, lt=4, description="Instance ID (0-3)")


class RemoveInstanceRequest(BaseModel):
    """Request to remove an instance"""
    instance_id: int = Field(..., ge=0, lt=4, description="Instance ID (0-3)")


class LogsRequest(BaseModel):
    """Request to get instance logs"""
    instance_id: int = Field(..., ge=0, lt=4, description="Instance ID (0-3)")
    tail: int = Field(100, ge=1, le=1000, description="Number of log lines to retrieve")


class ApiResponse(BaseModel):
    """Generic API response"""
    success: bool
    message: str
    data: Optional[Dict] = None


class InstancesListResponse(BaseModel):
    """Response with list of all instances"""
    instances: List[InstanceStatus]


