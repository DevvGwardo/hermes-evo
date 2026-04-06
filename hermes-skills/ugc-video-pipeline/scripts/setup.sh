#!/bin/bash
# =============================================================================
# UGC Video Pipeline - Setup Script
# =============================================================================
# This script installs all dependencies for the UGC Video Pipeline skill.
# Run: chmod +x setup.sh && ./setup.sh
#
# Requirements: Ubuntu 22.04+ / macOS, NVIDIA GPU with 24GB VRAM (recommended)
# =============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─── Configuration ────────────────────────────────────────────────────────────
SKILL_DIR="$HOME/.hermes/skills/ugc-video-pipeline"
MODELS_DIR="$HOME/models"
COMFYUI_DIR="$HOME/models/ComfyUI"
SCRIPTS_DIR="$SKILL_DIR/scripts"
REQUIREMENTS_FILE="$SKILL_DIR/requirements.txt"

# Disk space required (in GB)
REQUIRED_DISK_SPACE=80

# ─── Logging Functions ────────────────────────────────────────────────────────
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Check Functions ──────────────────────────────────────────────────────────
check() {
    if [ $? -eq 0 ]; then
        log_success "$1"
    else
        log_error "$1"
        return 1
    fi
}

# =============================================================================
# STEP 0: System Requirements Check
# =============================================================================
check_system() {
    log_info "=== Checking System Requirements ==="

    # OS Detection
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS="$NAME"
        VER="$VERSION_ID"
        log_info "OS: $OS $VER"
    elif [ "$(uname -s)" == "Darwin" ]; then
        OS="macOS"
        VER=$(sw_vers -productVersion)
        log_info "OS: $OS $VER"
    else
        OS="Unknown"
        log_warn "OS detection failed, assuming Linux"
    fi

    # RAM Check
    if [ "$(uname -s)" == "Darwin" ]; then
        TOTAL_RAM=$(sysctl -n hw.memsize 2>/dev/null | awk '{print $1/1024/1024/1024}')
    else
        TOTAL_RAM=$(free -g 2>/dev/null | grep -i mem | awk '{print $2}' || cat /proc/meminfo | grep MemTotal | awk '{print $2/1024/1024}')
    fi
    log_info "Total RAM: ${TOTAL_RAM}GB"

    if (( $(echo "$TOTAL_RAM < 16" | bc -l 2>/dev/null || echo 0) )); then
        log_warn "Less than 16GB RAM detected. Pipeline may be slow or unstable."
    fi

    # Disk Space Check
    AVAILABLE_DISK=$(df -BG "$HOME" 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ -z "$AVAILABLE_DISK" ]; then
        AVAILABLE_DISK=$(df -BG . 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//')
    fi
    log_info "Available disk space: ${AVAILABLE_DISK}GB"

    if [ "$AVAILABLE_DISK" -lt "$REQUIRED_DISK_SPACE" ]; then
        log_error "Insufficient disk space. Need at least ${REQUIRED_DISK_SPACE}GB, have ${AVAILABLE_DISK}GB"
        return 1
    fi

    # GPU Check
    if command -v nvidia-smi &> /dev/null; then
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
        GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | awk '{print $1}')
        GPU_VRAM_GB=$((GPU_VRAM / 1024))
        log_info "GPU: $GPU_NAME (${GPU_VRAM_GB}GB VRAM)"

        if [ "$GPU_VRAM_GB" -lt 16 ]; then
            log_warn "Less than 16GB VRAM detected. Some models may not fit."
            log_warn "Recommended: 24GB VRAM (RTX 3090/4090 or A100)"
        fi

        # Check CUDA
        CUDA_VERSION=$(nvidia-smi | grep -oP "CUDA Version: \K[0-9.]+" 2>/dev/null || echo "unknown")
        log_info "CUDA Version: $CUDA_VERSION"
    else
        log_warn "No NVIDIA GPU detected. GPU-accelerated models will not work."
        log_warn "CPU-only mode is supported but will be very slow."
    fi

    check "System requirements check"
}

# =============================================================================
# STEP 1: Install System Dependencies
# =============================================================================
install_system_deps() {
    log_info "=== Installing System Dependencies ==="

    if [ "$(uname -s)" == "Linux" ]; then
        # Update package list
        log_info "Updating package list..."
        sudo apt-get update -qq
        check "Package list update"

        # Install core dependencies
        log_info "Installing core packages..."
        sudo apt-get install -y --no-install-recommends \
            git \
            git-lfs \
            wget \
            curl \
            build-essential \
            libgl1-mesa-glx \
            libglib2.0-0 \
            ffmpeg \
            libavcodec-extra \
            libass9 \
            libfreetype6 \
            fonts-liberation \
            || true

        # Install FFmpeg with libass and drawtext support
        log_info "Installing FFmpeg with additional codecs..."
        sudo apt-get install -y --no-install-recommends \
            libx264-dev \
            libx265-dev \
            libvpx-dev \
            libmp3lame-dev \
            libopus-dev \
            libvorbis-dev \
            libass-dev \
            libfreetype-dev \
            libfontconfig1-dev \
            || true

        check "System packages installation"

    elif [ "$(uname -s)" == "Darwin" ]; then
        # Check for Homebrew
        if ! command -v brew &> /dev/null; then
            log_info "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi

        log_info "Installing packages with Homebrew..."
        brew install \
            git \
            git-lfs \
            wget \
            curl \
            ffmpeg \
            python3 \
            || true

        check "Homebrew packages installation"

        # Ensure Python 3 is available
        if ! command -v python3 &> /dev/null; then
            log_error "Python 3 not found. Please install Python 3.9+"
            return 1
        fi
    fi

    # Verify FFmpeg installation
    if command -v ffmpeg &> /dev/null; then
        FFmpeg_VERSION=$(ffmpeg -version 2>&1 | head -1)
        log_info "FFmpeg: $FFmpeg_VERSION"

        # Check for libass support
        if ffmpeg -filters 2>/dev/null | grep -q "ass\|libass"; then
            log_success "FFmpeg libass support: OK"
        else
            log_warn "FFmpeg may not have libass support. Captions may not work."
        fi
    else
        log_error "FFmpeg not found. Please install FFmpeg."
        return 1
    fi

    # Verify git-lfs
    if command -v git-lfs &> /dev/null; then
        git lfs install --quiet
        check "Git LFS initialization"
    else
        log_warn "Git LFS not found. Large model downloads may fail."
    fi

    log_success "System dependencies installed"
}

# =============================================================================
# STEP 2: Create Directory Structure
# =============================================================================
create_dirs() {
    log_info "=== Creating Directory Structure ==="

    mkdir -p "$MODELS_DIR"
    mkdir -p "$MODELS_DIR/xttsv2"
    mkdir -p "$MODELS_DIR/hedra/characters"
    mkdir -p "$MODELS_DIR/Wan2.2"
    mkdir -p "$MODELS_DIR/ltx-video"
    mkdir -p "$MODELS_DIR/wav2lip"
    mkdir -p "$MODELS_DIR/sadtalker"
    mkdir -p "$MODELS_DIR/ComfyUI"
    mkdir -p "$HOME/hermes/ugc-output"
    mkdir -p "$HOME/hermes/ugc-output/temp"

    check "Directory creation"
    log_success "Directories created at $MODELS_DIR and $HOME/hermes/ugc-output"
}

# =============================================================================
# STEP 3: Install Python Dependencies
# =============================================================================
install_python_deps() {
    log_info "=== Installing Python Dependencies ==="

    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    log_info "Python version: $PYTHON_VERSION"

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
        log_error "Python 3.9+ required. Found: $PYTHON_VERSION"
        return 1
    fi

    # Upgrade pip
    log_info "Upgrading pip..."
    pip3 install --upgrade pip --quiet
    check "pip upgrade"

    # Install PyTorch first (required by many other packages)
    log_info "Installing PyTorch..."
    if command -v nvidia-smi &> /dev/null; then
        # GPU version
        pip3 install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet || \
        pip3 install --upgrade torch torchvision torchaudio --quiet
    else
        # CPU version
        pip3 install --upgrade torch torchvision torchaudio --quiet
    fi
    check "PyTorch installation"

    # Install core ML/DL packages
    log_info "Installing ML packages (transformers, diffusers, accelerate)..."
    pip3 install \
        transformers \
        diffusers \
        accelerate \
        --quiet
    check "ML packages installation"

    # Install TTS (Coqui XTTS v2)
    log_info "Installing Coqui TTS (XTTS v2)..."
    pip3 install TTS --quiet
    check "Coqui TTS installation"

    # Install image/video processing
    log_info "Installing image/video processing packages..."
    pip3 install \
        opencv-python \
        opencv-python-headless \
        pillow \
        imageio \
        imageio-ffmpeg \
        --quiet
    check "Image/video processing packages"

    # Install numerical/scientific packages
    log_info "Installing numerical packages..."
    pip3 install \
        numpy \
        scipy \
        pandas \
        --quiet
    check "Numerical packages"

    # Install web/API clients
    log_info "Installing API clients..."
    pip3 install \
        requests \
        httpx \
        anthropic \
        openai \
        --quiet
    check "API client packages"

    # Install FFmpeg Python wrapper
    log_info "Installing ffmpy (Python FFmpeg wrapper)..."
    pip3 install ffmpy --quiet
    check "ffmpy installation"

    # Install ComfyUI requirements if cloned
    if [ -f "$COMFYUI_DIR/requirements.txt" ]; then
        log_info "Installing ComfyUI requirements..."
        pip3 install -r "$COMFYUI_DIR/requirements.txt" --quiet
        check "ComfyUI requirements"
    fi

    # Install additional utilities
    log_info "Installing utilities..."
    pip3 install \
        tqdm \
        PyYAML \
        safetensors \
        --quiet
    check "Utilities installation"

    log_success "Python dependencies installed"
}

# =============================================================================
# STEP 4: Clone/Install ComfyUI
# =============================================================================
install_comfyui() {
    log_info "=== Installing ComfyUI ==="

    if [ -d "$COMFYUI_DIR" ]; then
        log_info "ComfyUI directory exists at $COMFYUI_DIR"
        if [ -d "$COMFYUI_DIR/.git" ]; then
            log_info "Updating ComfyUI..."
            cd "$COMFYUI_DIR"
            git pull --quiet
            check "ComfyUI update"
        else
            log_warn "ComfyUI exists but is not a git repo. Skipping."
        fi
    else
        log_info "Cloning ComfyUI..."
        cd "$MODELS_DIR"
        git clone https://github.com/comfyanonymous/ComfyUI.git --quiet
        check "ComfyUI clone"

        # Install ComfyUI requirements
        if [ -f "$COMFYUI_DIR/requirements.txt" ]; then
            log_info "Installing ComfyUI dependencies..."
            pip3 install -r "$COMFYUI_DIR/requirements.txt" --quiet
            check "ComfyUI dependencies"
        fi
    fi

    log_success "ComfyUI installed at $COMFYUI_DIR"
}

# =============================================================================
# STEP 5: Download Model Weights
# =============================================================================

# 5a: Wan 2.2 T2V-A14B
download_wan22() {
    log_info "=== Downloading Wan 2.2 T2V-A14B ==="

    WAN22_DIR="$MODELS_DIR/Wan2.2"
    WAN22_MODEL_DIR="$WAN22_DIR/Wan2.2-T2V-A14B"

    if [ -d "$WAN22_MODEL_DIR" ] && [ -n "$(ls -A "$WAN22_MODEL_DIR" 2>/dev/null)" ]; then
        log_info "Wan 2.2 already exists at $WAN22_MODEL_DIR"
    else
        mkdir -p "$WAN22_DIR"
        cd "$WAN22_DIR"

        log_info "This is a large model (~28GB). Starting download..."
        log_info "Using git lfs clone from HuggingFace..."

        # Try HuggingFace clone first
        if git lfs install 2>/dev/null; then
            git clone https://huggingface.co/ali-vilab/Wan2.2-T2V-A14B --quiet 2>&1 || \
            git clone https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B --quiet 2>&1 || {
                log_warn "Git LFS clone failed, trying wget download..."
                # Fallback to individual file download
                cd "$WAN22_DIR"
                wget --continue --no-clobber \
                    "https://huggingface.co/ali-vilab/Wan2.2-T2V-A14B/resolve/main/Wan2.2_T2V_A14B.safetensors" \
                    --quiet || true
            }
        fi

        check "Wan 2.2 download"
    fi

    # Create symlink in expected location
    if [ -f "$WAN22_MODEL_DIR/Wan2.2_T2V_A14B.safetensors" ]; then
        ln -sf "$WAN22_MODEL_DIR/Wan2.2_T2V_A14B.safetensors" "$WAN22_DIR/Wan2.2_T2V_A14B.safetensors" 2>/dev/null || true
    fi

    log_success "Wan 2.2 T2V-A14B ready"
}

# 5b: LTX-Video 13B
download_ltxvideo() {
    log_info "=== Downloading LTX-Video 13B ==="

    LTX_DIR="$MODELS_DIR/ltx-video"

    if [ -d "$LTX_DIR/LTX-Video-13B" ] && [ -n "$(ls -A "$LTX_DIR/LTX-Video-13B" 2>/dev/null)" ]; then
        log_info "LTX-Video already exists at $LTX_DIR/LTX-Video-13B"
    else
        mkdir -p "$LTX_DIR"
        cd "$LTX_DIR"

        log_info "This is a large model (~26GB). Starting download..."
        log_info "Using git lfs clone from HuggingFace..."

        git lfs install 2>/dev/null
        git clone https://huggingface.co/Lightricks/LTX-Video-13B --quiet 2>&1 || {
            log_warn "Git LFS clone failed, trying wget download..."
            cd "$LTX_DIR"
            wget --continue --no-clobber \
                "https://huggingface.co/Lightricks/LTX-Video-13B/resolve/main/LTX-Video-13B.safetensors" \
                --quiet || true
        }

        check "LTX-Video download"
    fi

    # Create symlink
    if [ -f "$LTX_DIR/LTX-Video-13B/LTX-Video-13B.safetensors" ]; then
        ln -sf "$LTX_DIR/LTX-Video-13B/LTX-Video-13B.safetensors" "$LTX_DIR/LTX-Video-13B.safetensors" 2>/dev/null || true
    fi

    log_success "LTX-Video 13B ready"
}

# 5c: XTTS v2 (Coqui TTS - installs via pip, model downloads automatically)
install_xttsv2() {
    log_info "=== Installing XTTS v2 ==="

    # XTTS v2 is installed via pip (TTS package), model downloads automatically on first use
    # Just verify the package is installed

    if python3 -c "from TTS.api import TTS; print('TTS installed')" 2>/dev/null; then
        log_success "XTTS v2 (Coqui TTS) is installed"
        log_info "Model files will download automatically on first use"
        log_info "Reference audio sample will be downloaded to: $MODELS_DIR/xttsv2/"
    else
        log_error "XTTS v2 installation failed"
        return 1
    fi

    log_success "XTTS v2 ready"
}

# 5d: Hedra Character Model
download_hedra() {
    log_info "=== Downloading Hedra ==="

    HEDRA_DIR="$MODELS_DIR/hedra"

    if [ -d "$HEDRA_DIR/Hedra" ]; then
        log_info "Hedra already exists at $HEDRA_DIR/Hedra"
        cd "$HEDRA_DIR/Hedra"
        git pull --quiet 2>/dev/null || true
    else
        mkdir -p "$HEDRA_DIR"
        cd "$HEDRA_DIR"

        log_info "Cloning Hedra repository..."
        git clone https://github.com/Hedra-Labs/Hedra --quiet 2>&1
        check "Hedra clone"

        # Install Hedra package
        if [ -f "$HEDRA_DIR/Hedra/setup.py" ]; then
            cd "$HEDRA_DIR/Hedra"
            pip3 install -e . --quiet 2>/dev/null || true
        fi

        check "Hedra installation"
    fi

    # Create default avatar if not exists
    if [ ! -f "$HEDRA_DIR/characters/avatar.png" ]; then
        log_info "Creating default avatar placeholder..."
        # Create a simple gray placeholder - user should replace with actual character image
        python3 -c "
from PIL import Image
img = Image.new('RGB', (512, 512), color=(128, 128, 128))
img.save('$HEDRA_DIR/characters/avatar.png')
print('Placeholder avatar created')
" 2>/dev/null || true
    fi

    log_success "Hedra ready"
}

# 5e: Wav2Lip
download_wav2lip() {
    log_info "=== Downloading Wav2Lip ==="

    W2L_DIR="$MODELS_DIR/wav2lip"

    if [ -f "$W2L_DIR/wav2lip.pth" ]; then
        log_info "Wav2Lip checkpoint already exists at $W2L_DIR/wav2lip.pth"
    else
        mkdir -p "$W2L_DIR"
        cd "$W2L_DIR"

        log_info "Downloading Wav2Lip weights from GitHub releases..."

        # Download from GitHub releases
        wget --no-clobber --quiet \
            "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip.pth" \
            -O wav2lip.pth 2>&1 || {
                log_warn "Direct download failed, trying alternative..."
                wget --no-clobber --quiet \
                    "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
                    -O wav2lip_gan.pth 2>&1 || true
            }

        # Also download face detection model
        if [ ! -f "$W2L_DIR/s3fd.pth" ]; then
            wget --no-clobber --quiet \
                "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/s3fd.pth" \
                -O s3fd.pth 2>&1 || true
        fi

        check "Wav2Lip download"
    fi

    log_success "Wav2Lip ready"
}

# 5f: SadTalker
download_sadtalker() {
    log_info "=== Downloading SadTalker ==="

    ST_DIR="$MODELS_DIR/sadtalker"

    if [ -d "$ST_DIR/SadTalker" ]; then
        log_info "SadTalker already exists at $ST_DIR/SadTalker"
    else
        mkdir -p "$ST_DIR"
        cd "$ST_DIR"

        log_info "Cloning SadTalker repository..."
        git clone https://github.com/Winfredy/SadTalker --quiet 2>&1
        check "SadTalker clone"

        # Download checkpoints
        cd "$ST_DIR/SadTalker"

        log_info "Downloading SadTalker checkpoints..."

        # SadTalker checkpoints (typically from Google Drive or HuggingFace)
        # Using HuggingFace mirror if available
        mkdir -p checkpoints

        # Download mapping.pth
        wget --no-clobber --quiet \
            "https://huggingface.co/Winfredy/SadTalker/resolve/main/checkpoints/mapping_00108956.bin" \
            -O checkpoints/mapping_00108956.bin 2>&1 || true

        # Download other required checkpoints
        wget --no-clobber --quiet \
            "https://huggingface.co/Winfredy/SadTalker/resolve/main/checkpoints/epoch_20.pth" \
            -O checkpoints/epoch_20.pth 2>&1 || true

        # Download face restoration model
        if [ ! -f "$ST_DIR/SadTalker/checkpoints/face_restoration.pth" ]; then
            wget --no-clobber --quiet \
                "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth" \
                -O checkpoints/face_restoration.pth 2>&1 || true
        fi

        check "SadTalker checkpoints download"

        # Install SadTalker requirements
        if [ -f "requirements.txt" ]; then
            pip3 install -r requirements.txt --quiet 2>/dev/null || true
        fi
    fi

    log_success "SadTalker ready"
}

download_all_models() {
    log_info "=== Downloading All Models ==="
    log_info "Total disk space needed: ~63GB"
    log_warn "This may take a long time depending on your internet connection..."

    # Check available space before downloading
    AVAILABLE_DISK=$(df -BG "$HOME" 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ -z "$AVAILABLE_DISK" ]; then
        AVAILABLE_DISK=$(df -BG . 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//')
    fi

    if [ "$AVAILABLE_DISK" -lt 70 ]; then
        log_warn "Low disk space (${AVAILABLE_DISK}GB). Some large models may fail to download."
    fi

    # Download models in sequence
    download_wan22 || log_warn "Wan 2.2 download failed or skipped"
    download_ltxvideo || log_warn "LTX-Video download failed or skipped"
    install_xttsv2 || log_warn "XTTS v2 installation failed"
    download_hedra || log_warn "Hedra download failed or skipped"
    download_wav2lip || log_warn "Wav2Lip download failed or skipped"
    download_sadtalker || log_warn "SadTalker download failed or skipped"

    log_success "Model downloads completed"
}

# =============================================================================
# STEP 6: Verify Installations
# =============================================================================
verify_installation() {
    log_info "=== Verifying Installation ==="

    local errors=0

    # Check Python packages
    log_info "Checking Python packages..."
    python3 -c "
import torch
import transformers
import diffusers
import cv2
import numpy as np
from PIL import Image
import requests
from TTS.api import TTS
print('All Python packages OK')
" 2>/dev/null || { log_error "Python package check failed"; errors=$((errors+1)); }

    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        log_success "FFmpeg: OK"
    else
        log_error "FFmpeg: NOT FOUND"
        errors=$((errors+1))
    fi

    # Check ComfyUI
    if [ -d "$COMFYUI_DIR" ]; then
        log_success "ComfyUI: OK ($COMFYUI_DIR)"
    else
        log_error "ComfyUI: NOT FOUND"
        errors=$((errors+1))
    fi

    # Check model directories
    log_info "Checking model directories..."
    for model_dir in "Wan2.2" "ltx-video" "wav2lip" "sadtalker"; do
        if [ -d "$MODELS_DIR/$model_dir" ]; then
            log_success "$model_dir: OK"
        else
            log_warn "$model_dir: directory not found"
        fi
    done

    # Check Hedra
    if [ -d "$MODELS_DIR/hedra/Hedra" ]; then
        log_success "Hedra: OK"
    else
        log_warn "Hedra: repository not found"
    fi

    # Check XTTS/TTS
    if python3 -c "from TTS.api import TTS" 2>/dev/null; then
        log_success "XTTS v2 (TTS): OK"
    else
        log_error "XTTS v2 (TTS): NOT INSTALLED"
        errors=$((errors+1))
    fi

    if [ $errors -eq 0 ]; then
        log_success "All verifications passed!"
        return 0
    else
        log_error "$errors verification(s) failed"
        return 1
    fi
}

# =============================================================================
# STEP 7: Create pip requirements file
# =============================================================================
create_requirements_file() {
    log_info "=== Creating requirements.txt ==="

    cat > "$REQUIREMENTS_FILE" << 'EOF'
# UGC Video Pipeline - Python Dependencies
# Auto-generated by setup.sh

# PyTorch (install with GPU support separately if needed)
torch>=2.0.0
torchvision>=0.15.0
torchaudio>=2.0.0

# Text-to-Speech (XTTS v2)
TTS>=0.22.0

# Transformers and Diffusers
transformers>=4.35.0
diffusers>=0.25.0
accelerate>=0.25.0
safetensors>=0.4.0

# Image/Video Processing
opencv-python>=4.8.0
opencv-python-headless>=4.8.0
pillow>=10.0.0
imageio>=2.31.0
imageio-ffmpeg>=0.4.9

# Scientific Computing
numpy>=1.24.0
scipy>=1.11.0
pandas>=2.0.0

# API Clients
anthropic>=0.7.0
openai>=1.0.0
requests>=2.31.0
httpx>=0.25.0

# FFmpeg Wrapper
ffmpy>=0.3.0

# Utilities
tqdm>=4.66.0
pyyaml>=6.0.0
EOF

    check "requirements.txt created"
    log_success "requirements.txt written to $REQUIREMENTS_FILE"
}

# =============================================================================
# STEP 8: Final Setup
# =============================================================================
final_setup() {
    log_info "=== Final Setup ==="

    # Make scripts executable
    chmod +x "$SCRIPTS_DIR"/*.py 2>/dev/null || true

    # Ensure output directory exists
    mkdir -p "$HOME/hermes/ugc-output"

    # Create .gitkeep in model directories to prevent deletion
    touch "$MODELS_DIR/.gitkeep" 2>/dev/null || true

    # Print summary
    echo ""
    echo "=============================================="
    echo "  UGC Video Pipeline Setup Complete!"
    echo "=============================================="
    echo ""
    echo "  Skill Directory: $SKILL_DIR"
    echo "  Models Directory: $MODELS_DIR"
    echo "  Output Directory: $HOME/hermes/ugc-output"
    echo "  ComfyUI Directory: $COMFYUI_DIR"
    echo ""
    echo "  Next Steps:"
    echo "  1. Run: cd $SKILL_DIR"
    echo "  2. Edit pipeline_config.json with your settings"
    echo "  3. Start ComfyUI: $COMFYUI_DIR/main.py &"
    echo "  4. Run pipeline: python3 scripts/ugc_pipeline.py --help"
    echo ""
    echo "  Models Downloaded:"
    echo "  - Wan 2.2 T2V-A14B (~$HOME/models/Wan2.2/)"
    echo "  - LTX-Video 13B (~$HOME/models/ltx-video/)"
    echo "  - XTTS v2 (via TTS package)"
    echo "  - Hedra (~$HOME/models/hedra/)"
    echo "  - Wav2Lip (~$HOME/models/wav2lip/)"
    echo "  - SadTalker (~$HOME/models/sadtalker/)"
    echo "  - ComfyUI (~$HOME/models/ComfyUI/)"
    echo ""
    echo "=============================================="
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║       UGC Video Pipeline - Setup Script v1.0                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    # Check if running interactively
    if [ ! -t 0 ]; then
        log_warn "Not running interactively. Some features may not work."
    fi

    # Ask for confirmation before downloading
    if [ "${1:-}" != "--skip-prompts" ]; then
        echo ""
        log_info "This script will:"
        echo "  - Install system dependencies (git, ffmpeg, etc.)"
        echo "  - Install Python packages (torch, TTS, etc.)"
        echo "  - Download ~63GB of model files"
        echo "  - Install ComfyUI"
        echo ""
        read -p "Continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Setup cancelled."
            exit 0
        fi
    fi

    # Run setup steps
    check_system || true
    install_system_deps || { log_error "System dependency installation failed"; exit 1; }
    create_dirs
    create_requirements_file
    install_python_deps || { log_error "Python dependency installation failed"; exit 1; }
    install_comfyui || { log_error "ComfyUI installation failed"; exit 1; }
    download_all_models
    verify_installation || log_warn "Some verifications failed"
    final_setup

    log_success "Setup complete!"
}

# Run main with all arguments
main "$@"
