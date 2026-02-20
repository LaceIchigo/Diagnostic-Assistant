#!/usr/bin/env bash
# install_rocm.sh — Install ROCm and PyTorch for AMD GPU on Ubuntu 20.04/22.04

set -euo pipefail

ROCM_VERSION="${ROCM_VERSION:-6.0.2}"
UBUNTU_CODENAME=$(lsb_release -cs 2>/dev/null || echo "jammy")

echo "=============================================="
echo "  Diagnostic Assistant — ROCm Installer"
echo "  ROCm version: $ROCM_VERSION"
echo "  Ubuntu: $UBUNTU_CODENAME"
echo "=============================================="

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
    echo "This script requires sudo privileges."
    SUDO="sudo"
else
    SUDO=""
fi

# ── Step 1: Install prerequisites ──────────────────────────────────────────
echo ""
echo "[1/5] Installing prerequisites..."
$SUDO apt-get update -y
$SUDO apt-get install -y wget curl gnupg2 lsb-release python3 python3-pip python3-venv

# ── Step 2: Download and install amdgpu-install ───────────────────────────
echo ""
echo "[2/5] Downloading amdgpu-install..."
AMDGPU_INSTALL_DEB="amdgpu-install_${ROCM_VERSION}.60002-1_all.deb"
AMDGPU_URL="https://repo.radeon.com/amdgpu-install/${ROCM_VERSION}/ubuntu/${UBUNTU_CODENAME}/${AMDGPU_INSTALL_DEB}"

wget -q --show-progress -O "/tmp/${AMDGPU_INSTALL_DEB}" "$AMDGPU_URL"
$SUDO apt-get install -y "/tmp/${AMDGPU_INSTALL_DEB}"

# ── Step 3: Install ROCm ──────────────────────────────────────────────────
echo ""
echo "[3/5] Installing ROCm (this may take several minutes)..."
$SUDO amdgpu-install -y --usecase=rocm --no-dkms

# ── Step 4: Add user to required groups ───────────────────────────────────
echo ""
echo "[4/5] Adding current user to render and video groups..."
$SUDO usermod -a -G render,video "$LOGNAME"

# ── Step 5: Install PyTorch with ROCm support ─────────────────────────────
echo ""
echo "[5/5] Installing PyTorch with ROCm support..."
ROCM_SHORT=$(echo "$ROCM_VERSION" | cut -d. -f1-2)
pip3 install torch torchvision torchaudio \
    --index-url "https://download.pytorch.org/whl/rocm${ROCM_SHORT}"

# ── Verification ──────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  Verification"
echo "=============================================="
echo "ROCm info:"
rocminfo 2>/dev/null | grep -E "^(Name|Device Type)" | head -20 || echo "Run 'rocminfo' after reboot."
echo ""
echo "PyTorch ROCm check:"
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'ROCm available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
"

echo ""
echo "=============================================="
echo "  Installation complete!"
echo "  IMPORTANT: Log out and back in (or reboot)"
echo "  to apply group membership changes."
echo "=============================================="
