param location string
param appName string

var vnetName = '${appName}-vnet'

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: ['10.0.0.0/16'] }
    subnets: [
      {
        name: 'container-apps'
        properties: {
          addressPrefix: '10.0.0.0/23'
          delegations: [
            {
              name: 'app-env-delegation'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'postgres'
        properties: {
          addressPrefix: '10.0.2.0/24'
          delegations: [
            {
              name: 'postgres-delegation'
              properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' }
            }
          ]
        }
      }
      {
        name: 'private-endpoints'
        properties: { addressPrefix: '10.0.3.0/24' }
      }
    ]
  }
}

// ── Private DNS zones ──────────────────────────────────────────────────────

resource postgresDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.postgres.database.azure.com'
  location: 'global'
}

resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: postgresDnsZone
  name: '${vnetName}-postgres-link'
  location: 'global'
  properties: { virtualNetwork: { id: vnet.id }; registrationEnabled: false }
}

resource keyvaultDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
}

resource keyvaultDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: keyvaultDnsZone
  name: '${vnetName}-kv-link'
  location: 'global'
  properties: { virtualNetwork: { id: vnet.id }; registrationEnabled: false }
}

// ── Outputs ────────────────────────────────────────────────────────────────

output vnetId string = vnet.id
output containerAppsSubnetId string = vnet.properties.subnets[0].id
output postgresSubnetId string = vnet.properties.subnets[1].id
output privateEndpointSubnetId string = vnet.properties.subnets[2].id
output postgresDnsZoneId string = postgresDnsZone.id
output keyvaultDnsZoneId string = keyvaultDnsZone.id
