using './main.enterprise.bicep'

param namePrefix = 'tambi-prod'
param backendImage = 'replace-after-build'   // set by deploy-enterprise.sh
param frontendImage = 'replace-after-build'
// postgresAdminPassword and anthropicApiKey are @secure() — pass via --parameters on CLI
// or store in a local .bicepparam.local file (gitignored).
