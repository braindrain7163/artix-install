#!/usr/bin/env bash
set -euo pipefail

MANIFEST="${1:-}"

if [[ -z "${MANIFEST}" ]]; then
  echo "Usage: $0 <manifest-file>"
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "[ERROR] Manifest file '$MANIFEST' not found."
  exit 1
fi

# --- Check yay ---
if ! command -v yay >/dev/null 2>&1; then
  echo "[INFO] yay not found, installing..."
  sudo pacman -S --needed --noconfirm git base-devel
  tmpdir="$(mktemp -d)"
  git clone https://aur.archlinux.org/yay.git "$tmpdir/yay"
  pushd "$tmpdir/yay" >/dev/null
  makepkg -si --noconfirm
  popd >/dev/null
  rm -rf "$tmpdir"
else
  echo "[INFO] yay is already installed."
fi

# --- Refresh mirrors and update system ---
echo "[INFO] Refreshing package databases..."
sudo pacman -Sy --noconfirm

echo "[INFO] Updating system packages..."
yay -Syu --noconfirm

# --- Parse manifest (strip inline comments, trim, drop blanks) ---
# Supports lines like:  world/krita   # image editor
# Also supports multiple packages on one line (they'll be split by xargs).
echo "[INFO] Installing packages from '$MANIFEST'..."
# Create a cleaned, tokenized stream for xargs:
cleaned_pkgs=()
while IFS= read -r line; do
  # remove inline comments
  line="${line%%#*}"
  # trim leading/trailing whitespace
  line="$(printf '%s' "$line" | sed -e 's/^[[:space:]]\+//' -e 's/[[:space:]]\+$//')"
  [[ -z "$line" ]] && continue
  # split line into words (handles multiple packages on one line)
  for tok in $line; do
    cleaned_pkgs+=("$tok")
  done
done < "$MANIFEST"

if (( ${#cleaned_pkgs[@]} == 0 )); then
  echo "[WARN] No packages found in manifest after parsing."
  exit 0
fi

# Install all packages safely with proper quoting
yay -S --needed --noconfirm "${cleaned_pkgs[@]}"

echo "[SUCCESS] All packages installed successfully."

# --- Prompt for reboot ---
read -rp "Do you want to reboot now? [y/N]: " answer
case "$answer" in
  [yY]|[yY][eE][sS])
    echo "[INFO] Rebooting..."
    sudo reboot
    ;;
  *)
    echo "[INFO] Reboot skipped. Please reboot later to apply changes."
    ;;
esac
