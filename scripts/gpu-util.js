const fs = require('fs')
const yaml = require('js-yaml')
const AWS = require('aws-sdk')
const NodeSSH = require('node-ssh')
const flatten = require('lodash.flatten')
const Table = require('cli-table')
const logUpdate = require('log-update')

// setup
const ssh = new NodeSSH()
const GPU_UTIL_QUERY = 'nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader'
const getConnectParams = host => {
  return {
    host, username: 'ec2-user', privateKey: process.argv[2]
  }
}
const tableParams = {
  head: ['IP Address', 'Instance Type', 'GPU Utilization'],
  colWidths: [24, 24, 24]
}

// get stackName from our config file
const config = yaml.safeLoad(fs.readFileSync('config/config.yml').toString())
const stackName = config.default.stackName

// find all our project EC2s and get their IP
const ec2 = new AWS.EC2()
ec2.describeInstances({ Filters: [{ Name: 'tag:Project', Values: [`${stackName}`] }] })
  .promise()
  .then(resp => flatten(resp.Reservations.map(r => r.Instances)))
  .then(instances => {
    setInterval(() => {
      // run our promises in serial so we don't mix up our ssh connection
      // from: https://decembersoft.com/posts/promises-in-serial-with-array-reduce/
      instances.reduce((promiseChain, instance) => {
        return promiseChain.then(chainResults => {
          return ssh.connect(getConnectParams(instance.PublicIpAddress)).then(() => {
            return ssh.execCommand(GPU_UTIL_QUERY).then(result => {
              ssh.dispose()
              return [ ...chainResults, [
                instance.PublicIpAddress,
                instance.InstanceType,
                result.stdout
              ]
              ]
            })
          })
        })
      }, Promise.resolve([])).then(results => {
        let table = new Table(tableParams)
        results.forEach(r => table.push(r))
        logUpdate(table.toString())
      })
    }, 5000)
  })
