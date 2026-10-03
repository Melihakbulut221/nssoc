#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Source from a SoC flow. Project defaults; explicit environment mode supports
# the pinned LibreLane devshell without guessing another project's tool paths.
_SOC_FLOW_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
FLOW_TOOL_MODE=${FLOW_TOOL_MODE:-project}
case "$FLOW_TOOL_MODE" in
  project)
    SHIMS=${SHIMS:-$_SOC_FLOW_ROOT/hw/soc/tools/physical/bin}
    VENV=${VENV:-$_SOC_FLOW_ROOT/hw/soc/tools/flow-venv}
    OSS_CAD=${OSS_CAD:-${OSS_CAD_SUITE:-$_SOC_FLOW_ROOT/hw/soc/tools/oss-cad-suite}/bin}
    export PATH="$SHIMS:$VENV/bin:$OSS_CAD:$PATH"
    FLOW_PY=${FLOW_PY:-$VENV/bin/python}
    LIBRELANE=${LIBRELANE:-$VENV/bin/librelane}
    FLOW_OPENROAD=${FLOW_OPENROAD:-$SHIMS/openroad}
    ;;
  environment)
    # Opt-in only. Missing commands stay missing, never fall back to siblings.
    FLOW_PY=${FLOW_PY:-$(command -v python3 || true)}
    LIBRELANE=${LIBRELANE:-$(command -v librelane || true)}
    FLOW_OPENROAD=${FLOW_OPENROAD:-$(command -v openroad || true)}
    ;;
  *) echo "unknown FLOW_TOOL_MODE: $FLOW_TOOL_MODE" >&2; return 2 ;;
esac
if [ -n "$FLOW_OPENROAD" ]; then
    [ "$(basename "$FLOW_OPENROAD")" = openroad ] || { echo "FLOW_OPENROAD must name an openroad executable" >&2; return 2; }
    export PATH="$(dirname "$FLOW_OPENROAD"):$PATH"
fi
export PDK_ROOT=${PDK_ROOT:-$_SOC_FLOW_ROOT/hw/soc/tools/pdk}
# Custom per-tool wrappers set their own library paths. Never contaminate host tools.
unset LD_LIBRARY_PATH
unset _SOC_FLOW_ROOT
