using '../main.bicep'

param appName = 'parking'
param location = 'germanywestcentral'

// Set via CI/CD secrets — do not hardcode here
param containerImage = 'parkingcr.azurecr.io/parking:latest'
param azureTenantId = '<your-tenant-id>'
param emailFrom = 'parking@yourdomain.com'
param reservationHorizonDays = 31

// These must be supplied as --parameters overrides from CI/CD (stored in GitHub secrets)
// param azureClientId = ''
// param azureClientSecret = ''
// param sessionSecret = ''
// param adminUsername = ''
// param adminPasswordHash = ''
// param acsConnectionString = ''
