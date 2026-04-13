#!/bin/bash
# ===================================================================
# MiniStack — Run OBS Terraform Examples
# ===================================================================
#
# This script demonstrates creating OBS buckets via Terraform
# against the local MiniStack emulator.
#
# Usage:
#   chmod +x run_obs_examples.sh
#   ./run_obs_examples.sh
# ===================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MINISTACK_URL="http://localhost:4566"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MiniStack — OBS Terraform Examples                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check if MiniStack is running
echo -e "${YELLOW}[1/4] Checking MiniStack status...${NC}"
if curl -sf "${MINISTACK_URL}/_huawei/health" > /dev/null; then
    echo -e "${GREEN}✓ MiniStack is running at ${MINISTACK_URL}${NC}"
else
    echo -e "${RED}✗ MiniStack is not running!${NC}"
    echo "   Start it with: docker compose up -d"
    exit 1
fi

# Step 2: Choose example
echo ""
echo -e "${YELLOW}[2/4] Select example to run:${NC}"
echo "   1) obs-simple     — Basic bucket + object upload"
echo "   2) obs-bucket     — Comprehensive (8 buckets with all features)"
echo ""
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        EXAMPLE_DIR="obs-simple"
        ;;
    2)
        EXAMPLE_DIR="obs-bucket"
        ;;
    *)
        echo -e "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

EXAMPLE_PATH="${SCRIPT_DIR}/${EXAMPLE_DIR}"

if [ ! -d "${EXAMPLE_PATH}" ]; then
    echo -e "${RED}✗ Example directory not found: ${EXAMPLE_PATH}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Selected: ${EXAMPLE_DIR}${NC}"

# Step 3: Run Terraform
echo ""
echo -e "${YELLOW}[3/4] Running Terraform in ${EXAMPLE_DIR}...${NC}"
cd "${EXAMPLE_PATH}"

echo -e "${BLUE}   → terraform init${NC}"
terraform init -input=false

echo -e "${BLUE}   → terraform plan${NC}"
terraform plan -input=false -out=tfplan

echo -e "${BLUE}   → terraform apply${NC}"
terraform apply -input=false tfplan

# Step 4: Verify
echo ""
echo -e "${YELLOW}[4/4] Verifying created resources...${NC}"

# Get bucket name from outputs
BUCKET_NAME=$(terraform output -raw bucket_name 2>/dev/null || \
              terraform output -raw bucket_names 2>/dev/null | head -1 || \
              echo "unknown")

echo -e "${GREEN}✓ Terraform apply completed${NC}"
echo -e "${GREEN}  Bucket(s) created: ${BUCKET_NAME}${NC}"

# Show MiniStack health
echo ""
echo -e "${BLUE}MiniStack Huawei Cloud Status:${NC}"
curl -s "${MINISTACK_URL}/_huawei/health" | python3 -m json.tool 2>/dev/null || \
curl -s "${MINISTACK_URL}/_huawei/health"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Cleanup                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "To destroy created resources, run:"
echo -e "  ${YELLOW}cd ${EXAMPLE_PATH}${NC}"
echo -e "  ${YELLOW}terraform destroy -auto-approve${NC}"
echo ""
echo -e "${GREEN}Done!${NC}"
