param appName string
param originHostname string

var profileName = '${appName}-afd'
var endpointName = appName
var originGroupName = 'app-origin-group'
var originName = 'container-app-origin'
var routeName = 'default-route'
var wafPolicyName = '${replace(appName, '-', '')}waf'

// ── WAF Policy ─────────────────────────────────────────────────────────────

resource wafPolicy 'Microsoft.Network/FrontDoorWebApplicationFirewallPolicies@2022-05-01' = {
  name: wafPolicyName
  location: 'global'
  sku: { name: 'Standard_AzureFrontDoor' }
  properties: {
    policySettings: {
      enabledState: 'Enabled'
      mode: 'Prevention'
      requestBodyCheck: 'Enabled'
    }
    customRules: {
      rules: [
        {
          // Rate-limit: max 100 req / 1 min per IP
          name: 'RateLimitPerIp'
          priority: 10
          ruleType: 'RateLimitRule'
          rateLimitDurationInMinutes: 1
          rateLimitThreshold: 100
          matchConditions: [
            {
              matchVariable: 'RemoteAddr'
              operator: 'IPMatch'
              negateCondition: true
              matchValue: ['0.0.0.0/0']
            }
          ]
          action: 'Block'
        }
      ]
    }
  }
}

// ── Front Door Profile ──────────────────────────────────────────────────────

resource profile 'Microsoft.Cdn/profiles@2023-05-01' = {
  name: profileName
  location: 'global'
  sku: { name: 'Standard_AzureFrontDoor' }
}

resource endpoint 'Microsoft.Cdn/profiles/afdEndpoints@2023-05-01' = {
  parent: profile
  name: endpointName
  location: 'global'
  properties: { enabledState: 'Enabled' }
}

resource originGroup 'Microsoft.Cdn/profiles/originGroups@2023-05-01' = {
  parent: profile
  name: originGroupName
  properties: {
    loadBalancingSettings: { sampleSize: 4, successfulSamplesRequired: 3 }
    healthProbeSettings: {
      probePath: '/calendar'
      probeRequestType: 'HEAD'
      probeProtocol: 'Https'
      probeIntervalInSeconds: 60
    }
  }
}

resource origin 'Microsoft.Cdn/profiles/originGroups/origins@2023-05-01' = {
  parent: originGroup
  name: originName
  properties: {
    hostName: originHostname
    httpPort: 80
    httpsPort: 443
    originHostHeader: originHostname
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
  }
}

resource securityPolicy 'Microsoft.Cdn/profiles/securityPolicies@2023-05-01' = {
  parent: profile
  name: '${appName}-waf-policy'
  properties: {
    parameters: {
      type: 'WebApplicationFirewall'
      wafPolicy: { id: wafPolicy.id }
      associations: [
        {
          domains: [{ id: endpoint.id }]
          patternsToMatch: ['/*']
        }
      ]
    }
  }
}

resource route 'Microsoft.Cdn/profiles/afdEndpoints/routes@2023-05-01' = {
  parent: endpoint
  name: routeName
  properties: {
    originGroup: { id: originGroup.id }
    supportedProtocols: ['Http', 'Https']
    patternsToMatch: ['/*']
    forwardingProtocol: 'HttpsOnly'
    httpsRedirect: 'Enabled'
    linkToDefaultDomain: 'Enabled'
    enabledState: 'Enabled'
  }
  dependsOn: [origin]
}

output endpointHostname string = endpoint.properties.hostName
output frontDoorId string = profile.properties.frontDoorId
