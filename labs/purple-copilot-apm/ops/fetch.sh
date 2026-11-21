#!/usr/bin/env bash
# Run from the lab directory. Data, dependencies and credentials live outside Git.
set -euo pipefail
umask 077
state=${APM_STATE:-"$HOME/.local/state/purple-copilot-apm"}
mkdir -p "$state"
cd "$state"
fetch() {
    local url=$1 file=$2 hash=$3
    if ! echo "$hash  $file" | sha256sum --check --status 2>/dev/null; then
        curl --fail --location --retry 2 "$url" --output "$file.part"
        echo "$hash  $file.part" | sha256sum --check --status
        mv "$file.part" "$file"
    fi
}
docs=https://raw.githubusercontent.com/SpecterOps/BloodHound-Docs/61d0859a461ccc0aad8b06fefabd6b4df0c079bc/docs/assets/sample-data
skills=https://raw.githubusercontent.com/SpecterOps/skills/f5dbbb23059c1186c695c832eedf88c8f3a0fcb4/plugins/bloodhound/skills
fetch "$docs/ad_sampledata.zip" ad_sampledata.zip d32eb854bfaa1610078681c508a0ff7f2567f089eb9de00429a1cc951bf0b96e
fetch "$docs/entra_sampledata.zip" entra_sampledata.zip 77c457ae41698844b28441827ca9c0ae74b6d1a3d47bfeea96ab7894aaa94662
fetch "$skills/azurehound-analysis/SKILL.md" azurehound-analysis.md a8e8d3db10bced5d59bf4f0b603f6ac0c0bd4d62aa54b120b1e6142529b56973
fetch "$skills/bloodhound-ad-analysis/SKILL.md" bloodhound-ad-analysis.md 342633765b46176b8acbb5a748ffc2e3f5f9376fb4a99fd8d03b725fcb1c8dcb
fetch https://github.com/SpecterOps/bloodhound-cli/releases/download/v0.2.1/bloodhound-cli-linux-amd64.tar.gz cli.tgz 2f932d8174f3ed69adf38a8ae94fa58f56d92fadecae8e240f767bb88d449983
tar xzf cli.tgz bloodhound-cli
fetch https://api.github.com/repos/mwnickerson/bloodhound_mcp/tarball/cdb17097e761c8a8622cb93bc3ba49a9e150bb6e mcp.tgz 8b6692f4eb4094717d93b23be9454d3ef11f15011299d5d74d268ced01e23d16
mkdir -p community
tar xzf mcp.tgz --strip-components=1 -C community
uv sync --directory community --frozen --no-dev
