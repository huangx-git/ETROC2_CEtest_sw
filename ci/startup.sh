#! /bin/bash

RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
NC='\033[0m'
function info() { echo -e "${BLUE}${@}${NC}"; }
function error() { echo -e "${RED}${@}${NC}"; }
function success() { echo -e "${GREEN}${@}${NC}"; }

if [ -z "${TAMALERO_BASE}" ]; then
	error "Must source setup tamalero first."
	return 1
fi

cd $TAMALERO_BASE
# power cycle the PSUs with cocina
info "Power cycle of PSUs with cocina..."
/usr/bin/python3 power_cycle.py

# run test_tamalero with power up
info "Running test_tamalero..."
/usr/bin/python3 test_tamalero.py --kcu 192.168.0.11 --power_up --control_hub --verbose --adcs
EXIT=$?
if [ ${EXIT} -ne 0 ]; then
	error "Failure when running test_tamalero.py; exit code is ${EXIT}. Blocking merge."
	return ${EXIT}
else
	success "Success! test_tamalero.py exit with code 0"
fi
