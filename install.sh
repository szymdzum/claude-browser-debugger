#!/bin/bash
# install.sh - Install Browser Debugger skill for Claude Code
# Supports both symlink (recommended) and copy installation modes

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
GLOBAL_SKILLS_DIR="${HOME}/.claude/skills"
SKILL_NAME="browser-debugger"
TARGET_DIR="${GLOBAL_SKILLS_DIR}/${SKILL_NAME}"

echo "═══════════════════════════════════════════════════════════"
echo "    Browser Debugger Skill Installer"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Detect installation mode
if [ "$1" == "--symlink" ] || [ "$1" == "-s" ]; then
    INSTALL_MODE="symlink"
elif [ "$1" == "--copy" ] || [ "$1" == "-c" ]; then
    INSTALL_MODE="copy"
else
    # Auto-detect: if running from a git repo, offer symlink
    if git -C "$SCRIPT_DIR" rev-parse --git-dir > /dev/null 2>&1; then
        echo "📍 This skill appears to be in a git repository."
        echo "   Symlink mode keeps the skill version-controlled and easy to update."
        echo ""
        echo "Choose installation mode:"
        echo "  [1] Symlink (recommended - easy updates via git pull)"
        echo "  [2] Copy (standalone installation)"
        echo ""
        read -p "Enter choice (1 or 2): " choice
        case $choice in
            1) INSTALL_MODE="symlink" ;;
            2) INSTALL_MODE="copy" ;;
            *) echo "Invalid choice. Exiting."; exit 1 ;;
        esac
    else
        INSTALL_MODE="copy"
    fi
fi

echo ""
echo "📦 Installation mode: ${INSTALL_MODE}"
echo "📍 Target directory: ${TARGET_DIR}"
echo ""

# Create global skills directory if it doesn't exist
if [ ! -d "$GLOBAL_SKILLS_DIR" ]; then
    echo "Creating global skills directory..."
    mkdir -p "$GLOBAL_SKILLS_DIR"
    echo "  ✓ Created ${GLOBAL_SKILLS_DIR}"
fi

# Check if skill already exists
if [ -e "$TARGET_DIR" ]; then
    echo "⚠️  Skill already installed at: $TARGET_DIR"

    # Show current installation type
    if [ -L "$TARGET_DIR" ]; then
        LINK_TARGET=$(readlink "$TARGET_DIR")
        echo "   Current: Symlink → ${LINK_TARGET}"
    else
        echo "   Current: Copy installation"
    fi

    echo ""
    read -p "Remove existing installation? (y/n): " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi

    echo "Removing existing installation..."
    rm -rf "$TARGET_DIR"
    echo "  ✓ Removed"
fi

echo ""

# Perform installation based on mode
if [ "$INSTALL_MODE" == "symlink" ]; then
    echo "🔗 Creating symlink..."
    ln -s "$SCRIPT_DIR" "$TARGET_DIR"
    echo "  ✓ Symlinked: ${TARGET_DIR} → ${SCRIPT_DIR}"
    echo ""
    echo "💡 To update: cd ${SCRIPT_DIR} && git pull"
else
    echo "📄 Copying files..."
    mkdir -p "$TARGET_DIR"

    # Copy all necessary files
    for file in SKILL.md README.md QUICK-START.md install.sh \
                cdp-console.py cdp-network.py cdp-network-with-body.py debug-page.sh; do
        if [ -f "$SCRIPT_DIR/$file" ]; then
            cp "$SCRIPT_DIR/$file" "$TARGET_DIR/"
            # Make scripts executable
            if [[ "$file" == *.py ]] || [[ "$file" == *.sh ]]; then
                chmod +x "$TARGET_DIR/$file"
            fi
            echo "  ✓ $file"
        else
            echo "  ⚠️  $file not found (skipping)"
        fi
    done

    echo ""
    echo "💡 To update: Re-run this installer"
fi

echo ""
echo "✅ Installation complete!"
echo ""

# Check prerequisites
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Checking prerequisites..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

MISSING_DEPS=0

# Check Chrome
echo "1. Chrome/Chromium:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    if [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
        echo "  ✓ Chrome found"
    else
        echo "  ❌ Chrome not found"
        echo "     Install from: https://www.google.com/chrome/"
        MISSING_DEPS=1
    fi
elif command -v google-chrome &> /dev/null; then
    echo "  ✓ google-chrome found"
elif command -v chromium-browser &> /dev/null; then
    echo "  ✓ chromium-browser found"
else
    echo "  ❌ Chrome not found"
    echo "     Install: sudo apt-get install google-chrome-stable"
    MISSING_DEPS=1
fi
echo ""

# Check Python
echo "2. Python 3.7+:"
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "  ✓ Python found ($PY_VERSION)"
else
    echo "  ❌ Python 3 not found"
    echo "     Install from: https://www.python.org/downloads/"
    MISSING_DEPS=1
fi
echo ""

# Check websockets
echo "3. Python websockets library:"
if python3 -c "import websockets" &> /dev/null 2>&1; then
    echo "  ✓ websockets installed"
else
    echo "  ❌ websockets not installed"
    echo "     Install: pip3 install websockets --break-system-packages"
    MISSING_DEPS=1
fi
echo ""

# Check jq
echo "4. jq (JSON parser):"
if command -v jq &> /dev/null; then
    echo "  ✓ jq found ($(jq --version))"
else
    echo "  ❌ jq not found"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "     Install: brew install jq"
    else
        echo "     Install: sudo apt-get install jq"
    fi
    MISSING_DEPS=1
fi
echo ""

# Check curl
echo "5. curl:"
if command -v curl &> /dev/null; then
    echo "  ✓ curl found"
else
    echo "  ❌ curl not found"
    MISSING_DEPS=1
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $MISSING_DEPS -eq 0 ]; then
    echo "✅ All dependencies satisfied!"
else
    echo "⚠️  Some dependencies are missing."
    echo "   Install them before using the skill."
fi

echo ""
echo "📍 Skill installed at:"
echo "   ${TARGET_DIR}"

if [ "$INSTALL_MODE" == "symlink" ]; then
    echo ""
    echo "🔗 Symlinked to:"
    echo "   ${SCRIPT_DIR}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Usage"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Start Claude Code and ask questions like:"
echo "  • 'Debug https://example.com'"
echo "  • 'Check https://example.com for JavaScript errors'"
echo "  • 'What API calls does https://example.com make?'"
echo ""
echo "📖 View skill details:"
echo "   cat ${TARGET_DIR}/SKILL.md"
echo ""
echo "📚 Quick start guide:"
echo "   cat ${TARGET_DIR}/QUICK-START.md"
echo ""
echo "🧪 Test manually:"
echo "   chrome --headless=new --dump-dom https://example.com"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
