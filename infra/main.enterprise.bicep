// TAMBI — Enterprise deployment (Container Apps + Postgres + Azure AI Foundry + Key Vault).
// All secrets in Key Vault. Services authenticate via user-assigned managed identity —
// no API keys stored in app config or CI secrets.
//
// Deploy:
//   az deployment group create -g <rg> -f infra/main.enterprise.bicep \
//     -p @infra/enterprise.bicepparam

@description('Azure region')
param location string = resourceGroup().location

@description('Short prefix for resource names')
param namePrefix string = 'tambi-prod'

@description('Container image for the backend')
param backendImage string

@description('Container image for the frontend')
param frontendImage string

@secure()
@description('Postgres admin password (stored in Key Vault on first deploy)')
param postgresAdminPassword string

@secure()
@description('Anthropic API key — only needed when NOT using Azure AI Foundry for Claude')
param anthropicApiKey string = ''

var pgAdmin = 'dcih'
var pgDatabase = 'dcih'
var acrName = replace('${namePrefix}acr', '-', '')

// ── Managed Identity ──────────────────────────────────────────────────────────
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id'
  location: location
}

// ── Container Registry ────────────────────────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }  // auth via managed identity, not admin key
}

// Grant the managed identity AcrPull on the registry.
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, 'acrpull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Key Vault ─────────────────────────────────────────────────────────────────
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${namePrefix}-kv'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true   // use role assignments, not legacy access policies
    softDeleteRetentionInDays: 7
    enabledForDeployment: false
  }
}

// Grant the managed identity Key Vault Secrets User.
resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, identity.id, 'kvsecrets')
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Store the Postgres password as a Key Vault secret.
resource pgPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'postgres-admin-password'
  properties: { value: postgresAdminPassword }
}

// Store Anthropic key if provided (omit for pure-Azure mode).
resource anthropicSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(anthropicApiKey)) {
  parent: kv
  name: 'anthropic-api-key'
  properties: { value: anthropicApiKey }
}

// ── Azure OpenAI (embeddings: text-embedding-3-small) ────────────────────────
resource aoai 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${namePrefix}-aoai'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${namePrefix}-aoai'
    publicNetworkAccess: 'Enabled'
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: aoai
  name: 'text-embedding-3-small'
  sku: { name: 'Standard', capacity: 120 }  // 120K TPM
  properties: {
    model: { format: 'OpenAI', name: 'text-embedding-3-small', version: '1' }
  }
}

// Grant the managed identity Cognitive Services User on the AOAI resource.
resource aoaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoai.id, identity.id, 'coguser')
  scope: aoai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Azure AI Foundry (Claude via Azure Marketplace) ───────────────────────────
// Foundry project hosts the Claude model deployment.
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: '${namePrefix}-hub'
  location: location
  kind: 'Hub'
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: 'TAMBI AI Hub'
    publicNetworkAccess: 'Enabled'
  }
}

resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: '${namePrefix}-project'
  location: location
  kind: 'Project'
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    friendlyName: 'TAMBI Intelligence'
    hubResourceId: aiHub.id
    publicNetworkAccess: 'Enabled'
  }
}

// ── Postgres Flexible Server ──────────────────────────────────────────────────
resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${namePrefix}-pg'
  location: location
  sku: { name: 'Standard_B2ms', tier: 'Burstable' }  // 2 vCPU, 8GB — prod-lite
  properties: {
    version: '16'
    administratorLogin: pgAdmin
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 64 }
    backup: { backupRetentionDays: 14, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }

  resource db 'databases@2023-06-01-preview' = {
    name: pgDatabase
  }

  resource fwAzure 'firewallRules@2023-06-01-preview' = {
    name: 'AllowAzureServices'
    properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
  }
}

// ── Log Analytics + Container Apps environment ───────────────────────────────
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 90 }
}

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
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: { external: true, targetPort: 8000, transport: 'auto' }
      registries: [{
        server: acr.properties.loginServer
        identity: identity.id   // pull via managed identity, no admin key
      }]
      secrets: [
        { name: 'database-url', value: databaseUrl }
      ]
    }
    template: {
      containers: [{
        name: 'backend'
        image: backendImage
        resources: { cpu: json('1'), memory: '2Gi' }
        env: [
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          // Azure AI Foundry endpoint — set after hub/project deploy; the app will
          // use DefaultAzureCredential (managed identity) to get a bearer token.
          { name: 'AZURE_FOUNDRY_ENDPOINT', value: 'https://${namePrefix}-project.services.ai.azure.com/api/v1' }
          // Azure OpenAI embeddings — also uses managed identity, no key needed.
          { name: 'AZURE_OPENAI_EMBEDDINGS_ENDPOINT', value: aoai.properties.endpoints['OpenAI Language Model Instance API'] }
          { name: 'AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT', value: 'text-embedding-3-small' }
          { name: 'EMBEDDING_BACKEND', value: 'azure_openai' }
          { name: 'KEY_VAULT_URL', value: kv.properties.vaultUri }
          { name: 'ENVIRONMENT', value: 'production' }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }  // tells DefaultAzureCredential which identity to use
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
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: { external: true, targetPort: 80, transport: 'auto' }
      registries: [{
        server: acr.properties.loginServer
        identity: identity.id
      }]
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
output aoaiEndpoint string = aoai.properties.endpoints['OpenAI Language Model Instance API']
output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontend.properties.configuration.ingress.fqdn}'
