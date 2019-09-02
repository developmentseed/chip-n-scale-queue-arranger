const test = require('tape')
const sinon = require('sinon')
const proxyquire = require('proxyquire').noCallThru()
const MemoryStream = require('memorystream')
const fs = require('fs')

test('sqs-push', (t) => {
  const error = 'error'
  const sendMessageBatch = sinon.stub()
  sendMessageBatch.onFirstCall().returns({ promise: () => (Promise.reject(error)) })
  const SQS = function () {
    return {
      sendMessageBatch
    }
  }
  const aws = { SQS }

  const memStream = new MemoryStream()
  const stubFsCreateReadStream = sinon.stub(fs, 'createReadStream')
  stubFsCreateReadStream.returns(memStream)
  const logUpdate = sinon.stub()

  process.argv = [
    'command',
    'empty',
    'file',
    'queueurl'
  ]

  const sqsPush = proxyquire(
    '../scripts/sqs-push.js',
    {
      'aws-sdk': aws,
      'log-update': logUpdate,
      'fs': fs
    }
  )
  sqsPush.run()
  memStream.write('9-162-307\n9-161-307\n9-163-307')
  memStream.end('')
  setTimeout(() => {
    t.equal(logUpdate.getCall(3).args[0], 'Error: error',
      'Logs error when sqs message promise rejects')
    t.end()
  }, 1)
})
