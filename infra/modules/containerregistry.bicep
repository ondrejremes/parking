param location string
param appName string

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${replace(appName, '-', '')}acr'
  location: location
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

output loginServer string = acr.properties.loginServer
output id string = acr.id
output name string = acr.name
