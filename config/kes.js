const { Kes } = require('kes')

// Override the KES class to include useful post-deploy helpers
class UpdatedKes extends Kes {
  opsStack () {
    return super.opsStack()
      .then(() => this.describeCF())
      .then((r) => {
        let output = r.Stacks[0].Outputs
        let dbConnection = output.find(o => o.OutputKey === 'dbConnectionString')['OutputValue']
        let queueURL = output.find(o => o.OutputKey === 'queueURL')['OutputValue']
        return console.log(`
The stack ${r.Stacks[0].StackName} is deployed or updated.
- The database is available at: ${dbConnection}
- The queue is available at ${queueURL}

Is this the first time setting up this stack? Run the following command to set up the database:

  $ yarn setup ${dbConnection}
`
        )
      })
  }
}

module.exports = UpdatedKes
