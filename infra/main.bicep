targetScope = 'resourceGroup'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Short name used as prefix for all resources')
param appName string = 'parking'

@description('Container image to deploy, e.g. acrname.azurecr.io/parking:latest')
param containerImage string

// Custom domain is configured manually in Azure Portal

param azureTenantId string
param emailFrom string = 'parking@alintrust.cz'
param reservationHorizonDays int = 31

@secure()
param azureClientId string
@secure()
param azureClientSecret string
@secure()
param sessionSecret string
@secure()
param adminUsername string
@secure()
param adminPasswordHash string
@secure()
param acsConnectionString string

// ── Modules ────────────────────────────────────────────────────────────────

module network 'modules/network.bicep' = {
  name: 'network'
  params: { location: location, appName: appName }
}

module acr 'modules/containerregistry.bicep' = {
  name: 'acr'
  params: { location: location, appName: appName }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    location: location
    appName: appName
    subnetId: network.outputs.postgresSubnetId
    privateDnsZoneId: network.outputs.postgresDnsZoneId
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    appName: appName
    subnetId: network.outputs.privateEndpointSubnetId
    vnetId: network.outputs.vnetId
    privateDnsZoneId: network.outputs.keyvaultDnsZoneId
    secrets: {
      'db-url': 'postgresql://${postgres.outputs.adminUser}:${postgres.outputs.adminPassword}@${postgres.outputs.fqdn}/parking?sslmode=require'
      'session-secret': sessionSecret
      'azure-client-id': azureClientId
      'azure-client-secret': azureClientSecret
      'admin-username': adminUsername
      'admin-password-hash': adminPasswordHash
      'acs-connection-string': acsConnectionString
    }
  }
}

module containerapp 'modules/containerapp.bicep' = {
  name: 'containerapp'
  params: {
    location: location
    appName: appName
    containerImage: containerImage
    subnetId: network.outputs.containerAppsSubnetId
    acrLoginServer: acr.outputs.loginServer
    acrId: acr.outputs.id
    keyVaultUri: keyvault.outputs.vaultUri
    keyVaultId: keyvault.outputs.id
    azureTenantId: azureTenantId
    emailFrom: emailFrom
    reservationHorizonDays: reservationHorizonDays
  }
}

module frontdoor 'modules/frontdoor.bicep' = {
  name: 'frontdoor'
  params: {
    appName: appName
    originHostname: containerapp.outputs.fqdn
  }
}

// ── Outputs ────────────────────────────────────────────────────────────────

output frontDoorEndpoint string = frontdoor.outputs.endpointHostname
output containerAppFqdn string = containerapp.outputs.fqdn
output acrLoginServer string = acr.outputs.loginServer
