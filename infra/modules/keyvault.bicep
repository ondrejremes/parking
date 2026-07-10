param location string
param appName string
param subnetId string
param vnetId string
param privateDnsZoneId string
param secrets object  // { 'secret-name': 'secret-value' }

var kvName = '${appName}kv${uniqueString(subscription().subscriptionId)}'

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take(kvName, 24)
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: false
    publicNetworkAccess: 'Disabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
  }
}

resource kvSecrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for item in items(secrets): {
  parent: kv
  name: item.key
  properties: { value: item.value }
}]

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: '${appName}-kv-pe'
  location: location
  properties: {
    subnet: { id: subnetId }
    privateLinkServiceConnections: [
      {
        name: 'kv-connection'
        properties: {
          privateLinkServiceId: kv.id
          groupIds: ['vault']
        }
      }
    ]
  }
}

resource dnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: privateEndpoint
  name: 'kv-dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'keyvault'
        properties: { privateDnsZoneId: privateDnsZoneId }
      }
    ]
  }
}

output vaultUri string = kv.properties.vaultUri
output id string = kv.id
output name string = kv.name
