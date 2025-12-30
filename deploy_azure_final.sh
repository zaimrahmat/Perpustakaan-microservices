#!/usr/bin/env bash
set -euo pipefail

# =========================
# KONFIGURASI FINAL
# =========================
RG_NAME="rg-perpustakaan"
LOCATION="indonesiacentral"
ENV_NAME="env-perpustakaan"

# ACR yang benar (dari CLI Anda)
ACR_NAME="perpustakaanms"

AUTH_APP="auth-service"
PROJ_APP="project-service"
GATEWAY_APP="gateway-service"

# sesuai .env Anda
JWT_SECRET="CHANGE_ME_SUPER_SECRET"
JWT_ALG="HS256"
JWT_EXPIRE_MIN="120"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin123"

# PostgreSQL untuk project_service
PG_SERVER_NAME="pg-perpustakaan-$RANDOM$RANDOM"
PG_ADMIN_USER="pgadmin"
PG_ADMIN_PASS="1234!"   # WAJIB DIGANTI
PROJECT_DB_NAME="project_db"

echo "== Validasi login/subscription =="
az account show -o none

echo "== Validasi RG & ACR =="
az group show -n "$RG_NAME" -o none
az acr show -g "$RG_NAME" -n "$ACR_NAME" -o none

ACR_LOGIN_SERVER="$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)"

echo "== Enable ACR admin (agar Container Apps bisa pull image) =="
az acr update -n "$ACR_NAME" --admin-enabled true -o none
ACR_USER="$(az acr credential show -n "$ACR_NAME" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR_NAME" --query passwords[0].value -o tsv)"

echo "== Build image di ACR (remote build, tidak perlu az acr login) =="
az acr build -r "$ACR_NAME" -t auth_service:latest    -f services/auth_service/Dockerfile    services/auth_service
az acr build -r "$ACR_NAME" -t project_service:latest -f services/project_service/Dockerfile services/project_service
az acr build -r "$ACR_NAME" -t gateway_service:latest -f services/gateway_service/Dockerfile services/gateway_service

echo "== Buat PostgreSQL Flexible Server + project_db =="
az postgres flexible-server create \
  -g "$RG_NAME" -n "$PG_SERVER_NAME" -l "$LOCATION" \
  --admin-user "$PG_ADMIN_USER" \
  --admin-password "$PG_ADMIN_PASS" \
  --version 16 \
  --public-access 0.0.0.0 \
  --sku-name Standard_B1ms \
  -o none

az postgres flexible-server db create \
  -g "$RG_NAME" -s "$PG_SERVER_NAME" -d "$PROJECT_DB_NAME" -o none

PG_FQDN="$(az postgres flexible-server show -g "$RG_NAME" -n "$PG_SERVER_NAME" --query fullyQualifiedDomainName -o tsv)"
PROJECT_DB_URL="postgresql+psycopg2://${PG_ADMIN_USER}:${PG_ADMIN_PASS}@${PG_FQDN}:5432/${PROJECT_DB_NAME}?sslmode=require"

echo "== Setup Azure Container Apps Environment =="
az extension add --name containerapp --upgrade -o none || true
az provider register --namespace Microsoft.App -o none
az provider register --namespace Microsoft.OperationalInsights -o none

if ! az containerapp env show -g "$RG_NAME" -n "$ENV_NAME" >/dev/null 2>&1; then
  az containerapp env create -g "$RG_NAME" -n "$ENV_NAME" -l "$LOCATION" -o none
fi

echo "== Deploy auth-service (internal) =="
az containerapp create \
  -g "$RG_NAME" -n "$AUTH_APP" \
  --environment "$ENV_NAME" \
  --image "${ACR_LOGIN_SERVER}/auth_service:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --ingress internal \
  --target-port 8000 \
  --env-vars \
    JWT_SECRET="$JWT_SECRET" \
    JWT_ALG="$JWT_ALG" \
    JWT_EXPIRE_MIN="$JWT_EXPIRE_MIN" \
    ADMIN_USERNAME="$ADMIN_USERNAME" \
    ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  -o none

echo "== Deploy project-service (internal) =="
az containerapp create \
  -g "$RG_NAME" -n "$PROJ_APP" \
  --environment "$ENV_NAME" \
  --image "${ACR_LOGIN_SERVER}/project_service:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --ingress internal \
  --target-port 8000 \
  --env-vars \
    PROJECT_DB_URL="$PROJECT_DB_URL" \
    JWT_SECRET="$JWT_SECRET" \
    JWT_ALG="$JWT_ALG" \
  -o none

echo "== Deploy gateway-service (external/public) =="
az containerapp create \
  -g "$RG_NAME" -n "$GATEWAY_APP" \
  --environment "$ENV_NAME" \
  --image "${ACR_LOGIN_SERVER}/gateway_service:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --ingress external \
  --target-port 8000 \
  --env-vars \
    AUTH_SERVICE_URL="http://${AUTH_APP}:8000" \
    PROJECT_SERVICE_URL="http://${PROJ_APP}:8000" \
  -o none

GATEWAY_FQDN="$(az containerapp show -g "$RG_NAME" -n "$GATEWAY_APP" --query properties.configuration.ingress.fqdn -o tsv)"
echo ""
echo "=== DEPLOYMENT SELESAI ==="
echo "Gateway URL: https://${GATEWAY_FQDN}"
