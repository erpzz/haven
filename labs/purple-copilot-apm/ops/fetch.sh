#!/usr/bin/env bash
# Run from the lab directory. Data, dependencies and credentials live outside Git.
set -euo pipefail
umask 077
state=${APM_STATE:-"$HOME/.local/state/purple-copilot-apm"}
mkdir -p "$state"
cd "$state"
if command -v sha256sum >/dev/null; then sha() { sha256sum "$1" | cut -d' ' -f1; }
else sha() { shasum -a 256 "$1" | cut -d' ' -f1; }; fi  # macOS ships shasum, not sha256sum.
fetch() {
    local url=$1 file=$2 hash=$3
    if [[ ! -f "$file" || "$(sha "$file")" != "$hash" ]]; then
        curl --fail --location --retry 2 "$url" --output "$file.part"
        [[ "$(sha "$file.part")" == "$hash" ]] || { echo "Checksum mismatch for $file" >&2; rm -f "$file.part"; exit 1; }
        mv "$file.part" "$file"
    fi
}
docs=https://raw.githubusercontent.com/SpecterOps/BloodHound-Docs/61d0859a461ccc0aad8b06fefabd6b4df0c079bc/docs/assets/sample-data
skills=https://raw.githubusercontent.com/SpecterOps/skills/f5dbbb23059c1186c695c832eedf88c8f3a0fcb4/plugins/bloodhound/skills
fetch "$docs/ad_sampledata.zip" ad_sampledata.zip d32eb854bfaa1610078681c508a0ff7f2567f089eb9de00429a1cc951bf0b96e
fetch "$docs/entra_sampledata.zip" entra_sampledata.zip 77c457ae41698844b28441827ca9c0ae74b6d1a3d47bfeea96ab7894aaa94662
fetch "$skills/azurehound-analysis/SKILL.md" azurehound-analysis.md a8e8d3db10bced5d59bf4f0b603f6ac0c0bd4d62aa54b120b1e6142529b56973
fetch "$skills/bloodhound-ad-analysis/SKILL.md" bloodhound-ad-analysis.md 342633765b46176b8acbb5a748ffc2e3f5f9376fb4a99fd8d03b725fcb1c8dcb
# bloodhound-cli v0.2.1. The release publishes no checksum file; linux-amd64 is the original pin and the
# other platforms were hashed from the same GitHub release on 2026-11-22.
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) cli=linux-amd64 hash=2f932d8174f3ed69adf38a8ae94fa58f56d92fadecae8e240f767bb88d449983 ;;
    Linux-aarch64|Linux-arm64) cli=linux-arm64 hash=fd7197939c40fd8dc4b239d2696b610b8aa2f2fc5480bb834ff52e204458a18e ;;
    Darwin-arm64) cli=darwin-arm64 hash=6b46ec1bef4b4e05d3c5b631d4afae7346d8a76abd069292aaab9831a9e82cd0 ;;
    Darwin-x86_64) cli=darwin-amd64 hash=2c26e8736a24cbcff97e0e54e4fc6d999203c40b175ba33001f7f35310d5fb5c ;;
    *) echo "Unsupported platform $(uname -s)-$(uname -m)" >&2; exit 2 ;;
esac
fetch "https://github.com/SpecterOps/bloodhound-cli/releases/download/v0.2.1/bloodhound-cli-$cli.tar.gz" "cli-$cli.tgz" "$hash"
tar xzf "cli-$cli.tgz" bloodhound-cli
mcp=cdb17097e761c8a8622cb93bc3ba49a9e150bb6e
rm -rf community && mkdir -p community
if [[ -n "${APM_MCP_CHECKOUT:-}" ]]; then
    # Offline mirror: a clean git checkout of the community MCP at exactly the pinned commit.
    [[ "$(git -C "$APM_MCP_CHECKOUT" rev-parse HEAD)" == "$mcp" && -z "$(git -C "$APM_MCP_CHECKOUT" status --porcelain)" ]] \
        || { echo "APM_MCP_CHECKOUT must be a clean checkout of $mcp" >&2; exit 1; }
    git -C "$APM_MCP_CHECKOUT" archive "$mcp" | tar x -C community
else
    fetch "https://api.github.com/repos/mwnickerson/bloodhound_mcp/tarball/$mcp" mcp.tgz 8b6692f4eb4094717d93b23be9454d3ef11f15011299d5d74d268ced01e23d16
    tar xzf mcp.tgz --strip-components=1 -C community
fi
uv sync --directory community --frozen --no-dev
