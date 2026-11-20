#!/bin/bash
# Wait for the generic_v5 official run to finish (by PID file), then run generic_v6.
cd "$(dirname "$0")/../.."
until grep -q "step3e (official generic_v5, 8 tasks)" runs/generic-queue.log; do sleep 30; done
./scripts/generic/run_official_v6.sh
