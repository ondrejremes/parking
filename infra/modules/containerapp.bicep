param location string
param appName string
param containerImage string
param subnetId string
param acrLoginServer string
param acrId string
param keyVaultUri string
param keyVaultId string
param azureTenantId string
param emailFrom string
param reservationHorizonDays int

var envName = '${appName}-env'
var appIdentityName = '${appName}-identity'

// ── Managed identity ───────────────────────────────────────────────────────

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: appIdentityName
  location: location
}

// AcrPull — pull images from ACR
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acrId, identity.id, 'acrpull')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Key Vault Secrets User — read secrets
resource kvSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultId, identity.id, 'kv-secrets-user')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Container Apps Environment ─────────────────────────────────────────────

resource env 'Microsoft.App/managedEnvironments@2023-11-02-preview' = {
  name: envName
  location: location
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: subnetId
      internal: false
    }
    workloadProfiles: [
      { name: 'Consumption'; workloadProfileType: 'Consumption' }
    ]
  }
}

// ── Container App ──────────────────────────────────────────────────────────

var kvRef = '${keyVaultUri}secrets'

resource app 'Microsoft.App/containerApps@2023-11-02-preview' = {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    managedEnvironmentId: env.id
    workloadProfileName: 'Consumption'
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acrLoginServer
          identity: identity.id
        }
      ]
      secrets: [
        { name: 'db-url';              keyVaultUrl: '${kvRef}/db-url/';              identity: identity.id }
        { name: 'session-secret';      keyVaultUrl: '${kvRef}/session-secret/';      identity: identity.id }
        { name: 'azure-client-id';     keyVaultUrl: '${kvRef}/azure-client-id/';     identity: identity.id }
        { name: 'azure-client-secret'; keyVaultUrl: '${kvRef}/azure-client-secret/'; identity: identity.id }
        { name: 'admin-username';      keyVaultUrl: '${kvRef}/admin-username/';      identity: identity.id }
        { name: 'admin-password-hash'; keyVaultUrl: '${kvRef}/admin-password-hash/'; identity: identity.id }
        { name: 'acs-connection-str';  keyVaultUrl: '${kvRef}/acs-connection-string/'; identity: identity.id }
      ]
    }
    template: {
      containers: [
        {
          name: appName
          image: containerImage
          resources: { cpu: json('0.5'); memory: '1Gi' }
          env: [
            { name: 'DATABASE_URL';              secretRef: 'db-url' }
            { name: 'SESSION_SECRET';            secretRef: 'session-secret' }
            { name: 'AZURE_CLIENT_ID';           secretRef: 'azure-client-id' }
            { name: 'AZURE_CLIENT_SECRET';       secretRef: 'azure-client-secret' }
            { name: 'ADMIN_USERNAME';            secretRef: 'admin-username' }
            { name: 'ADMIN_PASSWORD_HASH';       secretRef: 'admin-password-hash' }
            { name: 'ACS_CONNECTION_STRING';     secretRef: 'acs-connection-str' }
            { name: 'AZURE_TENANT_ID';           value: azureTenantId }
            { name: 'EMAIL_FROM';                value: emailFrom }
            { name: 'RESERVATION_HORIZON_DAYS';  value: string(reservationHorizonDays) }
          ]
        }
      ]
      scale: { minReplicas: 1; maxReplicas: 2 }
    }
  }
  dependsOn: [acrPullRole, kvSecretsUserRole]
}

// ── Reminder job (daily cron) ──────────────────────────────────────────────

resource reminderJob 'Microsoft.App/jobs@2023-11-02-preview' = {
  name: '${appName}-reminder'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    managedEnvironmentId: env.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 300
      scheduleTriggerConfig: { cronExpression: '0 7 * * *'; replicaCompletionCount: 1 }
      registries: [
        { server: acrLoginServer; identity: identity.id }
      ]
      secrets: [
        { name: 'db-url';            keyVaultUrl: '${kvRef}/db-url/';            identity: identity.id }
        { name: 'acs-connection-str'; keyVaultUrl: '${kvRef}/acs-connection-string/'; identity: identity.id }
      ]
    }
    template: {
      containers: [
        {
          name: 'reminder'
          image: containerImage
          command: ['python', '-m', 'app.jobs.reminder']
          resources: { cpu: json('0.25'); memory: '0.5Gi' }
          env: [
            { name: 'DATABASE_URL';          secretRef: 'db-url' }
            { name: 'ACS_CONNECTION_STRING'; secretRef: 'acs-connection-str' }
          ]
        }
      ]
    }
  }
  dependsOn: [acrPullRole, kvSecretsUserRole]
}

output fqdn string = app.properties.configuration.ingress.fqdn
output identityPrincipalId string = identity.properties.principalId
