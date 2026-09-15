// TAMBI — Azure dev deployment (Container Apps + Postgres Flexible Server).
// Deploy:  az deployment group create -g <rg> -f infra/main.bicep -p @infra/main.dev.bicepparam
//
// Provisions: Container Registry, Log Analytics, Container Apps env, Postgres Flexible
// Server (+ db), and the backend/frontend container apps. Secrets are passed as secure
// params (wire them from GitHub Actions secrets or Key Vault — never commit them).

@description('Azure region')
param location string = resourceGroup().location

@description('Short prefix for resource names (dev)')
param namePrefix string = 'tambi-dev'

@description('Container image for the backend (e.g. <acr>.azurecr.io/tambi-backend:sha)')
param backendImage string

@description('Container image for the frontend')
param frontendImage string

@secure()
@description('Postgres admin password')
param postgresAdminPassword string

@secure()
param anthropicApiKey string

@secure()
param openaiApiKey string

var pgAdmin = 'dcih'
var pgDatabase = 'dcih'
var acrName = replace('${namePrefix}acr', '-', '')

// --- Container Registry ---
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

// --- Log Analytics (required by Container Apps env) ---
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

// --- Container Apps environment ---
resource caEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

// --- Postgres Flexible Server (dev: burstable) ---
resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${namePrefix}-pg'
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: pgAdmin
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }

  resource db 'databases@2023-06-01-preview' = {
    name: pgDatabase
  }

  // Dev only: allow Azure services (Container Apps) to reach the DB.
  resource fwAzure 'firewallRules@2023-06-01-preview' = {
    name: 'AllowAzureServices'
    properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
  }
}

var databaseUrl = 'postgresql://${pgAdmin}:${postgresAdminPassword}@${pg.properties.fullyQualifiedDomainName}:5432/${pgDatabase}?sslmode=require'

// --- Backend Container App ---
resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-backend'
  location: location
  properties: {
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: { external: true, targetPort: 8000, transport: 'auto' }
      registries: [{ server: acr.properties.loginServer, username: acr.listCredentials().username, passwordSecretRef: 'acr-password' }]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'database-url', value: databaseUrl }
        { name: 'anthropic-key', value: anthropicApiKey }
        { name: 'openai-key', value: openaiApiKey }
      ]
    }
    template: {
      containers: [{
        name: 'backend'
        image: backendImage
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-key' }
          { name: 'OPENAI_API_KEY', secretRef: 'openai-key' }
          { name: 'EMBEDDING_BACKEND', value: 'openai' }
          { name: 'ENVIRONMENT', value: 'staging' }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 2 }
    }
  }
}

// --- Frontend Container App ---
resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-frontend'
  location: location
  properties: {
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: { external: true, targetPort: 80, transport: 'auto' }
      registries: [{ server: acr.properties.loginServer, username: acr.listCredentials().username, passwordSecretRef: 'acr-password' }]
      secrets: [{ name: 'acr-password', value: acr.listCredentials().passwords[0].value }]
    }
    template: {
      containers: [{
        name: 'frontend'
        image: frontendImage
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 2 }
    }
  }
}

output acrLoginServer string = acr.properties.loginServer
output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontend.properties.configuration.ingress.fqdn}'
