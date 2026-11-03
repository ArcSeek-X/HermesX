#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <normalize|check> <artifact-path>" >&2
}

mode="${1:-}"
artifact_root="${2:-}"

if [[ "${mode}" != "normalize" ]] && [[ "${mode}" != "check" ]]; then
  usage
  exit 2
fi
if [[ -z "${artifact_root}" ]] || [[ ! -e "${artifact_root}" ]]; then
  echo "ERROR: macOS signature audit target does not exist: ${artifact_root:-<empty>}" >&2
  exit 2
fi
if ! command -v codesign >/dev/null 2>&1; then
  echo "ERROR: codesign is required for macOS signature auditing." >&2
  exit 2
fi
if ! command -v file >/dev/null 2>&1; then
  echo "ERROR: file is required for macOS signature auditing." >&2
  exit 2
fi

checked_count=0
signed_count=0
removed_count=0
repaired_count=0

# Apple Silicon requires a valid signature on loaded Mach-O code. Removing a
# damaged library signature makes the Python runtime unloadable; repair it with
# an ad-hoc signature. This does not add an Apple Developer identity or notarize
# the application; the outer bundle also needs a consistent ad-hoc seal.
repair_runtime_signature() {
  local candidate="$1"
  echo "Repairing runtime signature with ad-hoc identity: ${candidate}"
  codesign --force --sign - --timestamp=none "${candidate}"
  codesign --verify --strict --verbose=4 "${candidate}"
  repaired_count=$((repaired_count + 1))
}

audit_candidate() {
  local candidate="$1"
  local signature_details=""

  checked_count=$((checked_count + 1))
  if ! signature_details="$(codesign -d "${candidate}" 2>&1)"; then
    if [[ "${signature_details}" == *"code object is not signed at all"* ]]; then
      if [[ -f "${candidate}" || "${candidate}" == *.app || "${candidate}" == *.framework || "${candidate}" == *.xpc ]]; then
        if [[ "${mode}" == "normalize" ]]; then
          repair_runtime_signature "${candidate}"
        else
          echo "ERROR: unsigned runtime code in macOS artifact: ${candidate}" >&2
          exit 1
        fi
      fi
      return 0
    fi
    if [[ "${mode}" == "normalize" ]]; then
      repair_runtime_signature "${candidate}"
      return 0
    fi
    echo "ERROR: unreadable or invalid signature in macOS artifact: ${candidate}" >&2
    echo "${signature_details}" >&2
    exit 1
  fi

  signed_count=$((signed_count + 1))
  if codesign --verify --strict --verbose=4 "${candidate}" >/dev/null 2>&1; then
    return 0
  fi

  if [[ "${mode}" == "normalize" ]]; then
    repair_runtime_signature "${candidate}"
    return 0
  fi

  echo "ERROR: invalid signature in macOS artifact: ${candidate}" >&2
  codesign --verify --strict --verbose=4 "${candidate}" || true
  exit 1
}

while IFS= read -r -d '' candidate; do
  if [[ -d "${candidate}" ]]; then
    audit_candidate "${candidate}"
  elif file -b "${candidate}" | grep -q "Mach-O"; then
    audit_candidate "${candidate}"
  fi
done < <(
  find "${artifact_root}" -depth \
    \( -type f -o -type d \( -name "*.app" -o -name "*.framework" -o -name "*.xpc" \) \) \
    -print0
)

echo "macOS signature audit complete: mode=${mode}, checked=${checked_count}, signed=${signed_count}, removed=${removed_count}, repaired=${repaired_count}"
