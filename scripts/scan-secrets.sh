#!/usr/bin/env bash
# The open-source CLI needs no organization license or repository write token.
set -euo pipefail

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'This scanner entrypoint requires Linux x86_64.' >&2
  exit 2
fi

scan_tool_dir=$(mktemp -d)
trap 'rm -rf "$scan_tool_dir"' EXIT
scan_archive="$scan_tool_dir/gitleaks.tar.gz"
curl --fail --silent --show-error --location --retry 3 \
  https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz \
  --output "$scan_archive"
echo "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb  $scan_archive" | sha256sum --check --status
tar -xzf "$scan_archive" -C "$scan_tool_dir" gitleaks
"$scan_tool_dir/gitleaks" git --redact=100 --no-banner --exit-code=1 "${1:-.}"
