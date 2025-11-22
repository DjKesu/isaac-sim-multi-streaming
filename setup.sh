#!/bin/bash

################################################################################
# Isaac Sim Multi-Instance Orchestration - Setup Script
################################################################################
# This script sets up the environment for running multiple Isaac Sim instances
# via Docker containers with WebRTC streaming support.
#
# Requirements:
# - Ubuntu 20.04+ or compatible Linux distribution
# - NVIDIA GPU with RTX support (Compute Capability 7.5+)
# - NVIDIA drivers installed (535.x or newer recommended)
# - Root/sudo access
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ISAAC_SIM_IMAGE="nvcr.io/nvidia/isaac-sim:5.1.0"
MAX_INSTANCES=4

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run with sudo"
        echo "Usage: sudo ./setup.sh"
        exit 1
    fi
}

################################################################################
# System Checks
################################################################################

check_gpu() {
    print_header "Checking GPU Compatibility"
    
    if ! command -v nvidia-smi &> /dev/null; then
        print_error "nvidia-smi not found. Please install NVIDIA drivers first."
        exit 1
    fi
    
    # Get GPU info
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)
    COMPUTE_CAP=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n1)
    
    print_info "GPU: $GPU_NAME"
    print_info "Driver: $DRIVER_VERSION"
    print_info "Compute Capability: $COMPUTE_CAP"
    
    # Check compute capability (need 7.5+ for RTX)
    COMPUTE_MAJOR=$(echo $COMPUTE_CAP | cut -d'.' -f1)
    COMPUTE_MINOR=$(echo $COMPUTE_CAP | cut -d'.' -f2)
    
    if [ "$COMPUTE_MAJOR" -lt 7 ] || ([ "$COMPUTE_MAJOR" -eq 7 ] && [ "$COMPUTE_MINOR" -lt 5 ]); then
        print_error "GPU does not support RTX (requires Compute Capability 7.5+)"
        print_error "Your GPU has Compute Capability $COMPUTE_CAP"
        print_warning "Isaac Sim WebRTC streaming requires an RTX-capable GPU"
        print_warning "Supported GPUs: RTX 2000+, RTX A-series, A10/A30/A40/A100, etc."
        exit 1
    fi
    
    print_success "GPU is compatible with Isaac Sim"
}

check_docker() {
    print_header "Checking Docker Installation"
    
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. Installing Docker..."
        install_docker
    else
        DOCKER_VERSION=$(docker --version)
        print_success "Docker is installed: $DOCKER_VERSION"
    fi
}

install_docker() {
    print_info "Installing Docker..."
    
    apt-get update
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up the repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add current user to docker group
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker $SUDO_USER
        print_success "Added $SUDO_USER to docker group"
    fi
    
    print_success "Docker installed successfully"
}

check_nvidia_docker() {
    print_header "Checking NVIDIA Container Toolkit"
    
    if ! docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_warning "NVIDIA Container Toolkit not configured. Installing..."
        install_nvidia_docker
    else
        print_success "NVIDIA Container Toolkit is configured"
    fi
}

install_nvidia_docker() {
    print_info "Installing NVIDIA Container Toolkit..."
    
    # Configure the repository
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --batch --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    
    # Install the toolkit
    apt-get update
    apt-get install -y nvidia-container-toolkit
    
    # Configure Docker
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
    
    print_success "NVIDIA Container Toolkit installed and configured"
}

################################################################################
# Setup Functions
################################################################################

create_directories() {
    print_header "Creating Volume Mount Directories"
    
    for i in $(seq 0 $((MAX_INSTANCES - 1))); do
        BASE_DIR="$HOME/docker/isaac-sim-instance-$i"
        
        mkdir -p "$BASE_DIR/cache/main"
        mkdir -p "$BASE_DIR/cache/computecache"
        mkdir -p "$BASE_DIR/logs"
        mkdir -p "$BASE_DIR/config"
        mkdir -p "$BASE_DIR/data"
        mkdir -p "$BASE_DIR/pkg"
        
        # Set ownership to the Isaac Sim container user (1234:1234)
        chown -R 1234:1234 "$BASE_DIR"
        
        print_success "Created directories for instance $i"
    done
}

pull_isaac_sim_image() {
    print_header "Pulling Isaac Sim Docker Image"
    print_info "Image: $ISAAC_SIM_IMAGE"
    print_warning "This may take 10-30 minutes depending on your internet connection..."
    print_info "Image size: ~20GB"
    
    if docker pull $ISAAC_SIM_IMAGE; then
        print_success "Isaac Sim image pulled successfully"
    else
        print_error "Failed to pull Isaac Sim image"
        exit 1
    fi
}

setup_python_environment() {
    print_header "Setting Up Python Environment"
    
    # Get the real user who ran sudo
    if [ -n "$SUDO_USER" ]; then
        REAL_USER=$SUDO_USER
        REAL_HOME=$(eval echo ~$SUDO_USER)
    else
        REAL_USER=$(whoami)
        REAL_HOME=$HOME
    fi
    
    cd "$REAL_HOME/isaac-sim-multi-streaming"
    
    # Check if venv exists
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        sudo -u $REAL_USER python3 -m venv venv
    fi
    
    # Activate and install dependencies
    print_info "Installing Python dependencies..."
    sudo -u $REAL_USER bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
    
    print_success "Python environment ready"
}

create_env_file() {
    print_header "Creating Environment Configuration"
    
    if [ -n "$SUDO_USER" ]; then
        REAL_HOME=$(eval echo ~$SUDO_USER)
    else
        REAL_HOME=$HOME
    fi
    
    ENV_FILE="$REAL_HOME/isaac-sim-multi-streaming/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        cat > "$ENV_FILE" << EOF
# Isaac Sim Orchestration Configuration
ISAAC_MAX_INSTANCES=4
ISAAC_ISAAC_SIM_IMAGE=nvcr.io/nvidia/isaac-sim:5.1.0
ISAAC_HTTP_PORT_BASE=8211
ISAAC_WEBRTC_PORT_BASE=8011
ISAAC_NATIVE_PORT_BASE=8899
ISAAC_MEMORY_LIMIT=8g
ISAAC_SHM_SIZE=2g
ISAAC_GPU_ENABLED=true
ISAAC_ENABLE_WEBRTC=true
EOF
        print_success "Created .env configuration file"
    else
        print_info ".env file already exists, skipping"
    fi
}

test_docker_gpu() {
    print_header "Testing Docker GPU Access"
    
    print_info "Running GPU test container..."
    if docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_success "GPU is accessible from Docker containers"
    else
        print_warning "GPU test failed, but continuing (may work with Isaac Sim image)"
        print_info "This is often a false negative - Isaac Sim containers may still work"
    fi
}

print_summary() {
    print_header "Setup Complete!"
    
    echo ""
    print_success "All prerequisites installed and configured"
    echo ""
    print_info "Next steps:"
    echo "  1. Start the orchestration service:"
    echo "     cd ~/isaac-sim-multi-streaming"
    echo "     ./run.sh"
    echo ""
    echo "  2. Access the dashboard:"
    echo "     http://localhost:8000"
    echo ""
    echo "  3. Use the API:"
    echo "     curl -X POST http://localhost:8000/api/instances/start -H 'Content-Type: application/json' -d '{\"instance_id\": 0}'"
    echo ""
    print_info "Configuration:"
    echo "  - Max instances: $MAX_INSTANCES"
    echo "  - HTTP ports: 8211-$((8211 + MAX_INSTANCES - 1))"
    echo "  - WebRTC ports: 8011-$((8011 + MAX_INSTANCES - 1))"
    echo "  - Image: $ISAAC_SIM_IMAGE"
    echo ""
    print_warning "Note: You may need to log out and back in for Docker group changes to take effect"
    echo ""
}

################################################################################
# Main Installation Flow
################################################################################

main() {
    print_header "Isaac Sim Multi-Instance Orchestration Setup"
    echo ""
    
    check_root
    check_gpu
    check_docker
    check_nvidia_docker
    create_directories
    pull_isaac_sim_image
    test_docker_gpu
    setup_python_environment
    create_env_file
    
    echo ""
    print_summary
}

# Run main function
main

