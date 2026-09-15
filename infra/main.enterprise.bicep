// TAMBI — Enterprise deployment (Container Apps + Postgres + Key Vault + Managed Identity).
// Hybrid model backend:
//   - Embeddings run on Azure OpenAI (text-embedding-3-small) via managed identity — no key.
//   - Claude runs on the Anthropic API; the key lives in Key Vault and reaches the backend
//     as a Container Apps Key Vault secret reference (resolved by managed identity), so the
//     key value is never stored in app config, Bicep, or CI.
//     (Claude has no Azure quota on this subscription, so it stays on the Anthropic API.)
//
// Deploy:
//   az deployment group create -g <rg> -f infra/main.enterprise.bicep \
//     -p @infra/enterprise.bicepparam \
//     -p postgresAdminPassword=<pw> anthropicApiKey=<key>

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

// ── Azure OpenAI (embeddings only — Claude stays on the Anthropic API) ─────────
resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-oai'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${namePrefix}-oai'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

resource embedDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'text-embedding-3-small'
  sku: { name: 'Standard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: 'text-embedding-3-small', version: '1' }
  }
}

// Managed identity → Cognitive Services OpenAI User (call the embeddings endpoint, no key).
resource openaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, identity.id, 'openaiuser')
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
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
        // Anthropic key resolved from Key Vault by the managed identity — value never in config.
        {
          name: 'anthropic-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/anthropic-api-key'
          identity: identity.id
        }
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
          { name: 'EMBEDDING_BACKEND', value: 'azure_openai' }
          { name: 'AZURE_OPENAI_EMBEDDINGS_ENDPOINT', value: openai.properties.endpoint }
          { name: 'AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT', value: 'text-embedding-3-small' }
          { name: 'ENVIRONMENT', value: 'production' }
          { name: 'KEY_VAULT_URL', value: kv.properties.vaultUri }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
  dependsOn: [kvSecretsUser, openaiUser, embedDeployment]
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
output openaiEndpoint string = openai.properties.endpoint
output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontend.properties.configuration.ingress.fqdn}'
