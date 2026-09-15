// TAMBI — Enterprise deployment (Container Apps + Postgres + Key Vault + Managed Identity).
// API keys (Anthropic, OpenAI) live in Key Vault. Container Apps access them via a
// user-assigned managed identity — no secrets in app config or CI pipelines.
//
// Does NOT require Azure OpenAI or AI Foundry approval.
//
// Deploy:
//   az deployment group create -g <rg> -f infra/main.enterprise.bicep \
//     -p @infra/enterprise.bicepparam \
//     -p postgresAdminPassword=<pw> anthropicApiKey=<key> openaiApiKey=<key>

@description('Azure region')
param location string = resourceGroup().location

@description('Short prefix for resource names')
param namePrefix string = 'tambi-prod'

@description('Resource ID of the existing Container Apps environment to reuse. Personal subscriptions allow only 1 per region — pass the dev env ID here.')
param existingCaEnvId string

@description('Container image for the backend')
param backendImage string

@description('Container image for the frontend')
param frontendImage string

@secure()
param postgresAdminPassword string

@secure()
param anthropicApiKey string

@secure()
param openaiApiKey string

var pgAdmin = 'dcih'
var pgDatabase = 'dcih'
var acrName = replace('${namePrefix}acr', '-', '')

// ── User-assigned Managed Identity ───────────────────────────────────────────
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id'
  location: location
}

// ── Container Registry (pull via managed identity, no admin key) ──────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, 'acrpull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Key Vault — stores all API keys, no secrets in app config ────────────────
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${namePrefix}-kv'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    softDeleteRetentionInDays: 7
  }
}

resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, identity.id, 'kvsecrets')
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource pgPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'postgres-admin-password'
  properties: { value: postgresAdminPassword }
}

resource anthropicSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'anthropic-api-key'
  properties: { value: anthropicApiKey }
}

resource openaiSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'openai-api-key'
  properties: { value: openaiApiKey }
}

// ── Postgres Flexible Server ──────────────────────────────────────────────────
resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${namePrefix}-pg'
  location: location
  sku: { name: 'Standard_B2ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: pgAdmin
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 64 }
    backup: { backupRetentionDays: 14, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
  resource db 'databases' = { name: pgDatabase }
  resource fw 'firewallRules' = {
    name: 'AllowAzureServices'
    properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
  }
}

// ── Container Apps environment ────────────────────────────────────────────────
// Personal subscriptions allow only 1 CA environment per region — always pass the
// existing env ID. Enterprise subscriptions: create one first and pass its resource ID.
var caEnvId = existingCaEnvId

// ── Backend Container App ─────────────────────────────────────────────────────
var databaseUrl = 'postgresql://${pgAdmin}:${postgresAdminPassword}@${pg.properties.fullyQualifiedDomainName}:5432/${pgDatabase}?sslmode=require'

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-backend'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    managedEnvironmentId: caEnvId
    configuration: {
      ingress: { external: true, targetPort: 8000, transport: 'auto' }
      registries: [{ server: acr.properties.loginServer, identity: identity.id }]
      secrets: [
        { name: 'database-url', value: databaseUrl }
        { name: 'anthropic-key', value: anthropicApiKey }
        { name: 'openai-key', value: openaiApiKey }
      ]
    }
    template: {
      containers: [{
        name: 'backend'
        image: backendImage
        resources: { cpu: json('1'), memory: '2Gi' }
        env: [
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-key' }
          { name: 'OPENAI_API_KEY', secretRef: 'openai-key' }
          { name: 'EMBEDDING_BACKEND', value: 'openai' }
          { name: 'ENVIRONMENT', value: 'production' }
          { name: 'KEY_VAULT_URL', value: kv.properties.vaultUri }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// ── Frontend Container App ────────────────────────────────────────────────────
resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-frontend'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    managedEnvironmentId: caEnvId
    configuration: {
      ingress: { external: true, targetPort: 80, transport: 'auto' }
      registries: [{ server: acr.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'frontend'
        image: frontendImage
        resources: { cpu: json('0.5'), memory: '1Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 2 }
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────
output identityClientId string = identity.properties.clientId
output acrLoginServer string = acr.properties.loginServer
output keyVaultUrl string = kv.properties.vaultUri
output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontend.properties.configuration.ingress.fqdn}'
