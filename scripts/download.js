const fs = require('fs')
const { promisify } = require('util')

const dbConfig = require('../db/knexfile').remote
const db = require('knex')(dbConfig)

const writeFile = promisify(fs.writeFile)
const outputFile = process.argv[2]

db('results').then(results => {
  const csv = ['tile,output'].concat(results.map(result => `${result.tile},${JSON.stringify(result.output)}`)).join('\n')
  return writeFile(outputFile, csv)
}).then(_ => process.exit(0))
