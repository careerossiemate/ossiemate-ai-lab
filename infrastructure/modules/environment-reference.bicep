// Reference for a future approved environment; not applied by Package 13.
param environmentName string
param location string = resourceGroup().location
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'none'
    }
  }
}
output environmentId string = environment.id
