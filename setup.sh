#!/usr/bin/env bash
# FitFinder AI – Project Setup Script
# Run this from the FitFinderAI/ directory on macOS to generate the Xcode project.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/FitFinderAI"

echo "==================================="
echo "  FitFinder AI – Setup"
echo "==================================="
echo ""

# ── 1. Check Xcode ─────────────────────────────────────────────────────────────
if ! command -v xcodebuild &>/dev/null; then
    echo "❌  Xcode not found. Install Xcode from the App Store."
    exit 1
fi
echo "✅  Xcode: $(xcodebuild -version | head -1)"

# ── 2. Check / install XcodeGen ────────────────────────────────────────────────
if ! command -v xcodegen &>/dev/null; then
    echo "📦  Installing XcodeGen via Homebrew…"
    if ! command -v brew &>/dev/null; then
        echo "❌  Homebrew not found. Install it from https://brew.sh"
        exit 1
    fi
    brew install xcodegen
fi
echo "✅  XcodeGen: $(xcodegen --version)"

# ── 3. Generate Xcode project ──────────────────────────────────────────────────
echo ""
echo "⚙️   Generating Xcode project…"
cd "$PROJECT_DIR"
xcodegen generate --spec project.yml
echo "✅  Xcode project generated: FitFinderAI.xcodeproj"

# ── 4. Remind user to add API keys ─────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1. Open the project:"
echo "     open FitFinderAI/FitFinderAI.xcodeproj"
echo ""
echo "  2. Add your API keys in:"
echo "     FitFinderAI/Configuration/APIConfiguration.swift"
echo ""
echo "     • Claude API key  → https://console.anthropic.com"
echo "     • SerpAPI key     → https://serpapi.com"
echo ""
echo "  3. Set your development team in Xcode:"
echo "     Target → Signing & Capabilities → Team"
echo ""
echo "  4. Run on device or simulator: ⌘R"
echo ""
echo "  Tip: set useMockData = true in APIConfiguration.swift"
echo "  to preview the UI without API keys."
echo ""
echo "✅  Setup complete!"
