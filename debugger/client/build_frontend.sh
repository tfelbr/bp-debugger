#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
BACKEND_DIR="${SCRIPT_DIR}/backend"

cd ${FRONTEND_DIR}
npm run build

rm -r ${BACKEND_DIR}/static
rm -r ${BACKEND_DIR}/templates

mkdir -p ${BACKEND_DIR}/static
mkdir -p ${BACKEND_DIR}/templates

cp ${FRONTEND_DIR}/build/*.html ${BACKEND_DIR}/templates
cp ${FRONTEND_DIR}/build/*.css ${BACKEND_DIR}/static
cp ${FRONTEND_DIR}/build/*.png ${BACKEND_DIR}/static
cp -r ${FRONTEND_DIR}/build/_app ${BACKEND_DIR}/static
