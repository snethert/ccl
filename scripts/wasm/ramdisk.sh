#!/bin/bash
# ramdisk.sh — Create/destroy a macOS RAM disk for CCL WASM builds.
#
# Usage:
#   ./ramdisk.sh create [SIZE_MB]   — create ramdisk (default 5120 = 5GB)
#   ./ramdisk.sh destroy             — unmount and destroy ramdisk
#   ./ramdisk.sh status              — show current ramdisk status
#
# After create, build/wasm32 is a symlink to /Volumes/CCLBuild.
# The original build/wasm32 is preserved as build/wasm32.disk-backup.
# On destroy, the symlink is removed and the backup is restored.
#
# NOTE: RAM disks do not survive reboot. Re-run `create` after restart.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_LINK="$REPO_ROOT/build/wasm32"
BACKUP_DIR="$REPO_ROOT/build/wasm32.disk-backup"
VOLUME_NAME="CCLBuild"
MOUNT_POINT="/Volumes/$VOLUME_NAME"
STAMP_FILE="$MOUNT_POINT/.ccl-ramdisk"

DEFAULT_SIZE_MB=5120  # 5 GB

die() { echo "ERROR: $*" >&2; exit 1; }

cmd_create() {
  local size_mb="${1:-$DEFAULT_SIZE_MB}"
  local sectors=$(( size_mb * 2048 ))  # 512-byte sectors

  # Check if already mounted
  if [ -f "$STAMP_FILE" ]; then
    echo "RAM disk already mounted at $MOUNT_POINT ($(cat "$STAMP_FILE"))"
    return 0
  fi

  echo "Creating ${size_mb}MB RAM disk..."
  local dev
  dev=$(hdiutil attach -nomount "ram://$sectors")
  dev=$(echo "$dev" | xargs)  # trim whitespace

  echo "Formatting $dev as HFS+ '$VOLUME_NAME'..."
  diskutil erasevolume HFS+ "$VOLUME_NAME" "$dev" >/dev/null

  # Stamp it so we can identify our ramdisk later
  echo "created=$(date -u +%Y-%m-%dT%H:%M:%SZ) size_mb=$size_mb dev=$dev" > "$STAMP_FILE"

  # Create build subdirectory structure
  mkdir -p "$MOUNT_POINT"/{kernel,subprims,modules,images,boot,l1-fasls,bin}

  # Handle the symlink
  if [ -L "$BUILD_LINK" ]; then
    echo "build/wasm32 is already a symlink — updating target."
    rm "$BUILD_LINK"
  elif [ -d "$BUILD_LINK" ]; then
    echo "Backing up existing build/wasm32 → build/wasm32.disk-backup..."
    if [ -d "$BACKUP_DIR" ]; then
      die "Backup dir already exists: $BACKUP_DIR — remove it first."
    fi
    mv "$BUILD_LINK" "$BACKUP_DIR"

    # Copy non-image artifacts to ramdisk (skip the 2.3GB root.image)
    echo "Copying build artifacts to ramdisk (skipping images/*.image)..."
    rsync -a --exclude='images/*.image' "$BACKUP_DIR/" "$MOUNT_POINT/"
    echo "Copied. (Skipped large .image files to save RAM.)"
  fi

  # Create symlink
  mkdir -p "$(dirname "$BUILD_LINK")"
  ln -s "$MOUNT_POINT" "$BUILD_LINK"

  echo ""
  echo "RAM disk ready:"
  echo "  Mount:   $MOUNT_POINT"
  echo "  Symlink: build/wasm32 → $MOUNT_POINT"
  echo "  Size:    ${size_mb}MB"
  echo "  Device:  $dev"
  echo ""
  echo "All builds now write to RAM. Run '$0 destroy' to tear down."
}

cmd_destroy() {
  if [ ! -f "$STAMP_FILE" ]; then
    # Try to find it anyway
    if mount | grep -q "$VOLUME_NAME"; then
      echo "Warning: $VOLUME_NAME is mounted but missing stamp file."
    else
      echo "No CCL ramdisk found."
      return 0
    fi
  fi

  echo "Destroying ramdisk at $MOUNT_POINT..."

  # Remove symlink
  if [ -L "$BUILD_LINK" ]; then
    rm "$BUILD_LINK"
    echo "Removed symlink: build/wasm32"
  fi

  # Restore backup if it exists
  if [ -d "$BACKUP_DIR" ]; then
    mv "$BACKUP_DIR" "$BUILD_LINK"
    echo "Restored build/wasm32 from disk backup."
  else
    echo "No disk backup found — build/wasm32 removed."
  fi

  # Unmount
  hdiutil detach "$MOUNT_POINT" -force 2>/dev/null || true
  echo "RAM disk destroyed."
}

cmd_status() {
  echo "=== CCL WASM Ramdisk Status ==="
  if [ -f "$STAMP_FILE" ]; then
    echo "  Active: YES"
    echo "  Info:   $(cat "$STAMP_FILE")"
    echo "  Usage:"
    df -h "$MOUNT_POINT" | tail -1 | awk '{printf "    Total: %s  Used: %s  Avail: %s  (%s)\n", $2, $3, $4, $5}'
  else
    echo "  Active: NO"
  fi
  echo ""
  if [ -L "$BUILD_LINK" ]; then
    echo "  build/wasm32 → $(readlink "$BUILD_LINK") (symlink)"
  elif [ -d "$BUILD_LINK" ]; then
    echo "  build/wasm32 is a real directory ($(du -sh "$BUILD_LINK" | cut -f1))"
  else
    echo "  build/wasm32 does not exist"
  fi
  if [ -d "$BACKUP_DIR" ]; then
    echo "  build/wasm32.disk-backup exists ($(du -sh "$BACKUP_DIR" | cut -f1))"
  fi
}

case "${1:-status}" in
  create)  cmd_create "${2:-}" ;;
  destroy) cmd_destroy ;;
  status)  cmd_status ;;
  *)       echo "Usage: $0 {create [SIZE_MB]|destroy|status}" ;;
esac
