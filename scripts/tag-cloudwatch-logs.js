const fs = require('fs')
const AWS = require('aws-sdk')
const yaml = require('js-yaml')

// get stackName, projectTag from our config file
const config = yaml.safeLoad(fs.readFileSync('config/config.yml').toString())
const stackName = config.default.stackName
const projectTag = config.default.projectTag

const cw = new AWS.CloudWatchLogs()

// helper
function tagWithProject (logGroup) {
  console.log(`tagging ${logGroup.logGroupName} with { Project: ${projectTag} }`)
  return cw.tagLogGroup({
    logGroupName: logGroup.logGroupName,
    tags: { Project: projectTag }
  }).promise()
}

// tag lambda cloudwatch logs
cw.describeLogGroups({ logGroupNamePrefix: `/aws/lambda/${stackName}` })
  .promise()
  .then(resp => {
    return Promise.all(resp.logGroups.map(tagWithProject))
  })

// tag ECS cloudwatch logs
cw.describeLogGroups({ logGroupNamePrefix: stackName })
  .promise()
  .then(resp => {
    return Promise.all(resp.logGroups.map(tagWithProject))
  })
