param location string
param appName string
param subnetId string
param privateDnsZoneId string

@secure()
param adminPassword string = uniqueString(resourceGroup().id, appName, 'pg')

var serverName = '${appName}-pg'
var adminUser = 'pgadmin'

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: serverName
  location: location
  sku: { name: 'Standard_B1ms'; tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: adminUser
    administratorLoginPassword: adminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7; geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    network: {
      delegatedSubnetResourceId: subnetId
      privateDnsZoneArmResourceId: privateDnsZoneId
    }
    authConfig: { passwordAuth: 'Enabled'; activeDirectoryAuth: 'Disabled' }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: server
  name: 'parking'
  properties: { charset: 'UTF8'; collation: 'en_US.utf8' }
}

output fqdn string = server.properties.fullyQualifiedDomainName
output serverName string = serverName
output adminUser string = adminUser
output adminPassword string = adminPassword
