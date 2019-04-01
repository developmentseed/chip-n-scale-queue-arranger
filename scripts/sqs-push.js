const fs = require('fs')
const { Transform, Writable } = require('stream')
const split = require('split')
const through2Batch = require('through2-batch')
const logUpdate = require('log-update')
const { SQS } = require('aws-sdk')
const uuidv4 = require('uuid/v4')

let count = 0
const queue = process.argv[3]

const transform = new Transform({
  objectMode: true,
  transform: (data, _, done) => {
    if (!data.toString()) return done(null, null) // don't write empty lines
    const [ x, y, z ] = data.toString().split('-').map(d => Number(d))
    done(null, JSON.stringify({ x, y, z }))
  }
})

const counter = new Transform({
  objectMode: true,
  transform: (data, _, done) => {
    logUpdate(`Sending ${++count} messages to queue: ${queue}`)
    done(null, data)
  }
})

// simplified from https://github.com/danielyaa5/sqs-write-stream
class SqsWriteStream extends Writable {
  /**
   * Must provide a url property
   * @param {Object} queue - An object with a url property
   */
  constructor (queue, options) {
    super({ objectMode: true })
    this.queueUrl = queue.url
    this.sqs = new SQS()
  }

  async _write (obj, enc, cb) {
    try {
      const Entries = obj.map(o => ({ MessageBody: o, Id: uuidv4() }))
      // TODO: add backpressure, handle memory bloat
      this.sqs.sendMessageBatch({ Entries, QueueUrl: this.queueUrl }).promise()
      return cb()
    } catch (err) {
      return cb(err)
    }
  }
}

const sqsStream = new SqsWriteStream({ url: queue })

fs.createReadStream(process.argv[2])
  .pipe(split())
  .pipe(transform)
  .pipe(counter)
  .pipe(through2Batch.obj())
  .pipe(sqsStream)
