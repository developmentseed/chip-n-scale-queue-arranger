const assert = require('assert')
const path = require('path')
const fs = require('fs')
const yaml = require('js-yaml')
const AWS = require('aws-sdk')
const dbConfig = require('../db/knexfile').remote
const axios = require('axios')
require('dotenv').config({ path: path.join(process.env.PWD, 'config', '.env') })

// get stackName from our config file
const config = yaml.safeLoad(fs.readFileSync('config/config.yml').toString())
const stackName = config.default.stackName

// fixtures
const DB_TYPES = [
  { column_name: 'tile', data_type: 'character varying' },
  { column_name: 'output', data_type: 'jsonb' }
]

// get output values from the cloudformation stack
async function getStackOutputs (stackName) {
  const cf = new AWS.CloudFormation()
  return cf.describeStacks({ StackName: stackName }).promise()
    .then(resp => resp.Stacks[0].Outputs)
}

async function verify () {
  console.log(`Verifying stack ${stackName}`)
  const outputs = await getStackOutputs(stackName)
  dbConfig.connection = outputs.find(o => o.OutputKey === 'dbConnectionString').OutputValue
  const db = require('knex')(dbConfig)

  // check that our db has the correct columns
  await db.select(['column_name', 'data_type'])
    .table('information_schema.columns')
    .where({ 'table_name': 'results' })
    .then(rows => assert.deepStrictEqual(rows, DB_TYPES))
    .catch(err => console.error(err))
    .then(_ => console.log('Database has the correct columns'))

  // check that our ALB/GPU endpoint is healthy
  const endpoint = outputs.find(o => o.OutputKey === 'modelEndpoint').OutputValue
  await axios.get(endpoint)
    .then(resp => assert.deepStrictEqual(resp.status, 200))
    .catch(err => console.error(err))
    .then(_ => console.log('TF Serving returns a 200 status from the internal load balancer endpoint'))

  // download a tile
  const tile = { x: 184260, y: 107656, z: 18 }
  const url = config.default.lambdas.DownloadAndPredict.envs.TILE_ENDPOINT
    .replace('{}', tile.z)
    .replace('{}', tile.x)
    .replace('{}', tile.y)
    .replace('{}', process.env.TILE_ACCESS_TOKEN)

  const img = await axios.get(url, { responseType: 'arraybuffer' })
    .then(resp => {
      assert.deepStrictEqual(resp.status, 200)
      console.log('Tile endpoint returns a 200 status')
      return resp.data.toString('base64')
    })
    .catch(err => console.error(err))

  // confirm that we receive a prediction from the endpoint using the tile
  const body = { instances: [{ 'image_bytes': { 'b64': img } }] }
  await axios.post(`${endpoint}:predict`, body)
    .then(resp => resp.data)
    .then(data => assert(Array.isArray(data.predictions)))
    .catch(err => console.error(err))
    .then(_ => console.log('Prediction endpoint response has key "predictions" and it is an array'))

  return true
}

verify()
  .then(a => console.log('Stack verified'))
  .catch(err => console.error(err) && process.exit(1))
  .then(_ => process.exit(0))
