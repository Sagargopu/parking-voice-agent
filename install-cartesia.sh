#!/bin/bash

set -e

# Cartesia CLI installation script
# Version: 2025-08-02-v4
# This script downloads and installs the latest version of the Cartesia CLI

API_BASE_URL="https://cartesia.sh/api/releases"
BINARY_NAME="cartesia"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.cartesia/bin}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    printf "${GREEN}[INFO]${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1"
}

# Detect OS and architecture
detect_platform() {
    local os arch

    case "$(uname -s)" in
        Darwin*)    os="darwin" ;;
        Linux*)     os="linux" ;;
        *)          print_error "Unsupported operating system: $(uname -s)"; exit 1 ;;
    esac

    case "$(uname -m)" in
        x86_64|amd64)   arch="amd64" ;;
        arm64|aarch64)  arch="arm64" ;;
        *)              print_error "Unsupported architecture: $(uname -m)"; exit 1 ;;
    esac

    echo "${os}-${arch}"
}

# Get the latest release info from Cartesia API
get_latest_release() {
    local platform="$1"
    local api_url="${API_BASE_URL}/latest"
    local response

    # Add platform parameters if provided
    if [ -n "$platform" ]; then
        local os_arch
        os_arch=$(echo "$platform" | tr '-' '\n')
        local os=$(echo "$os_arch" | head -n1)
        local arch=$(echo "$os_arch" | tail -n1)
        api_url="${api_url}?os=${os}&arch=${arch}"
    fi

    if command -v curl >/dev/null 2>&1; then
        response=$(curl -sL "${api_url}")
    elif command -v wget >/dev/null 2>&1; then
        response=$(wget -qO- "${api_url}")
    else
        print_error "Neither curl nor wget is available. Please install one of them."
        exit 1
    fi

    # Check if we got a valid response
    if [ -z "$response" ] || echo "$response" | grep -q '"error"'; then
        print_error "Failed to get release information from Cartesia API."
        if echo "$response" | grep -q '"error"'; then
            local error_msg
            error_msg=$(echo "$response" | sed -n 's/.*"error":"*\([^"]*\)"*.*/\1/p')
            print_error "API Error: $error_msg"
        fi
        exit 1
    fi

    echo "$response"
}

# Add directory to PATH in shell profile
add_to_path() {
    local install_dir="$1"
    local shell_profile=""

    # Detect shell and profile file
    case "$SHELL" in
        */bash*)
            if [ -f "$HOME/.bashrc" ]; then
                shell_profile="$HOME/.bashrc"
            elif [ -f "$HOME/.bash_profile" ]; then
                shell_profile="$HOME/.bash_profile"
            elif [ -f "$HOME/.profile" ]; then
                shell_profile="$HOME/.profile"
            fi
            ;;
        */zsh*)
            if [ -f "$HOME/.zshrc" ]; then
                shell_profile="$HOME/.zshrc"
            elif [ -f "$HOME/.zprofile" ]; then
                shell_profile="$HOME/.zprofile"
            fi
            ;;
        */fish*)
            # Fish uses a different syntax, handle separately if needed
            shell_profile=""
            ;;
        *)
            if [ -f "$HOME/.profile" ]; then
                shell_profile="$HOME/.profile"
            fi
            ;;
    esac

    # Check if directory is already in PATH
    case ":$PATH:" in
        *":$install_dir:"*)
            print_status "Directory $install_dir is already in PATH"
            return 0
            ;;
    esac

    # Add to PATH in shell profile
    if [ -n "$shell_profile" ] && [ -w "$shell_profile" ]; then
        if ! grep -q "export PATH.*$install_dir" "$shell_profile" 2>/dev/null; then
            echo "" >> "$shell_profile"
            echo "# Added by Cartesia CLI installer" >> "$shell_profile"
            echo "export PATH=\"$install_dir:\$PATH\"" >> "$shell_profile"
            print_status "Added $install_dir to PATH in $shell_profile"
            print_warning "Please restart your shell or run: source $shell_profile"
        else
            print_status "PATH entry already exists in $shell_profile"
        fi
    else
        print_warning "Could not automatically add to PATH. Please add the following to your shell profile:"
        print_warning "  export PATH=\"$install_dir:\$PATH\""
    fi
}

# Download and install the binary
install_binary() {
    local release_info="$1"
    local temp_dir

    # Extract info from release JSON
    local version
    local download_url
    local archive_name

    version=$(echo "$release_info" | sed -n 's/.*"version":"*\([^"]*\)"*.*/\1/p')
    download_url=$(echo "$release_info" | sed -n 's/.*"download_url":"*\([^"]*\)"*.*/\1/p')
    archive_name=$(echo "$release_info" | sed -n 's/.*"archive_name":"*\([^"]*\)"*.*/\1/p')

    if [ -z "$version" ] || [ -z "$download_url" ] || [ -z "$archive_name" ]; then
        print_error "Invalid release information received from API"
        print_error "Debug info: version='$version' download_url='$download_url' archive_name='$archive_name'"
        print_error "Raw API response: $release_info"
        exit 1
    fi

    temp_dir=$(mktemp -d)
    trap "rm -rf ${temp_dir}" EXIT

    print_status "Downloading ${BINARY_NAME} ${version}..."

    if command -v curl >/dev/null 2>&1; then
        curl -sL "${download_url}" -o "${temp_dir}/${archive_name}"
    elif command -v wget >/dev/null 2>&1; then
        wget -q "${download_url}" -O "${temp_dir}/${archive_name}"
    fi

    if [ ! -f "${temp_dir}/${archive_name}" ]; then
        print_error "Failed to download ${archive_name}"
        exit 1
    fi

    print_status "Extracting archive..."

    # Handle different archive formats
    case "$archive_name" in
        *.tar.gz)
            tar -xzf "${temp_dir}/${archive_name}" -C "${temp_dir}"
            ;;
        *.zip)
            if command -v unzip >/dev/null 2>&1; then
                unzip -q "${temp_dir}/${archive_name}" -d "${temp_dir}"
            else
                print_error "unzip is required to extract .zip archives but is not installed"
                exit 1
            fi
            ;;
        *)
            print_error "Unsupported archive format: ${archive_name}"
            exit 1
            ;;
    esac

    # Create install directory if it doesn't exist
    mkdir -p "${INSTALL_DIR}"

    # Find the binary (handle .exe for Windows if needed)
    local binary_path
    if [ -f "${temp_dir}/${BINARY_NAME}" ]; then
        binary_path="${temp_dir}/${BINARY_NAME}"
    elif [ -f "${temp_dir}/${BINARY_NAME}.exe" ]; then
        binary_path="${temp_dir}/${BINARY_NAME}.exe"
    else
        print_error "Binary ${BINARY_NAME} not found in archive"
        exit 1
    fi

    # Install binary (no sudo needed for user directory)
    install -m 755 "${binary_path}" "${INSTALL_DIR}/$(basename "${binary_path}")"

    print_status "Successfully installed ${BINARY_NAME} to ${INSTALL_DIR}/$(basename "${binary_path}")"
}

# Verify installation
verify_installation() {
    # Check if binary exists in install directory
    if [ -f "${INSTALL_DIR}/${BINARY_NAME}" ] || [ -f "${INSTALL_DIR}/${BINARY_NAME}.exe" ]; then
        local binary_path
        if [ -f "${INSTALL_DIR}/${BINARY_NAME}" ]; then
            binary_path="${INSTALL_DIR}/${BINARY_NAME}"
        else
            binary_path="${INSTALL_DIR}/${BINARY_NAME}.exe"
        fi

        # Try to get version from the installed binary
        local installed_version
        installed_version=$("${binary_path}" version 2>/dev/null | head -n1 || echo "unknown")
        print_status "Installation verified: ${installed_version}"
        print_status ""
        print_status "Get started with: ${BINARY_NAME} auth login"

        # Check if it's already in PATH, if not provide instructions
        if ! command -v "${BINARY_NAME}" >/dev/null 2>&1; then
            printf "${GREEN}[INFO]${NC} ${BOLD}Restart your shell or run 'source ~/.zshrc' (or your shell's config file) to use ${BINARY_NAME} from anywhere.${NC}\n"
        fi
    else
        print_error "Installation failed. ${BINARY_NAME} not found in ${INSTALL_DIR}."
        exit 1
    fi
}

# Main installation flow
main() {
    print_status "Installing Cartesia CLI..."

    # Check for required tools
    if ! command -v tar >/dev/null 2>&1; then
        print_error "tar is required but not installed."
        exit 1
    fi

    # Detect platform
    local platform
    platform=$(detect_platform)
    print_status "Detected platform: ${platform}"

    # Get latest release info
    local release_info
    release_info=$(get_latest_release "${platform}")
    if [ -z "${release_info}" ]; then
        print_error "Failed to get release information"
        exit 1
    fi

    # Extract version for display
    local version
    version=$(echo "$release_info" | sed -n 's/.*"version":"*\([^"]*\)"*.*/\1/p')
    print_status "Latest version: ${version}"

    # Install binary
    install_binary "${release_info}"

    # Add to PATH
    add_to_path "${INSTALL_DIR}"

    # Verify installation
    verify_installation
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Cartesia CLI Installation Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  INSTALL_DIR    Installation directory (default: ~/.cartesia/bin)"
        echo ""
        echo "Examples:"
        echo "  # Install to default location"
        echo "  curl -sSL https://cartesia.sh | bash"
        echo ""
        echo "  # Install to custom location"
        echo "  INSTALL_DIR=~/.local/bin curl -sSL https://cartesia.sh | bash"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
