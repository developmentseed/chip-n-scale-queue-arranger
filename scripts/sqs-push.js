const fs = require('fs')
const { Transform, Writable } = require('stream')
const split = require('split')
const through2Batch = require('through2-batch')
const logUpdate = require('log-update')
const { SQS } = require('aws-sdk')
const uuidv4 = require('uuid/v4')

const promiseThreshold = process.env.PROMISE_THRESHOLD || 500
const highWaterMark = 10
const queue = process.argv[3]
let count = 0

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
    super({
      objectMode: true,
      highWaterMark
    })
    this.queueUrl = queue.url
    this.sqs = new SQS()
    this.activePromises = new Map()
    this.decrementActivePromises = this.decrementActivePromises.bind(this)
    this.paused = false
  }

  decrementActivePromises (id) {
    this.activePromises.delete(id)
    if (this.paused && this.activePromises.size < promiseThreshold / 2) {
      this.paused = false
      this.cb()
    }
  }

  _write (obj, enc, cb) {
    if (this.activePromises.size >= promiseThreshold) {
      this.paused = true
      this.cb = cb
    } else {
      try {
        const Entries = obj.map((object) => ({
          MessageBody: object,
          Id: uuidv4()
        }))
        const Id = uuidv4()
        const promise = this.sqs.sendMessageBatch({
          Entries,
          QueueUrl: this.queueUrl
        })
          .promise()
          .then(() => {
            this.decrementActivePromises(Id)
          })
          .catch((error) => {
            logUpdate(`Error: ${error}`)
            this.decrementActivePromises(Id)
          })
        this.activePromises.set(Id, promise)
        return cb()
      } catch (err) {
        logUpdate(`Error: ${err}`)
        return cb(err)
      }
    }
  }
}

function run () {
  const sqsStream = new SqsWriteStream({ url: queue })
  fs.createReadStream(process.argv[2])
    .pipe(split())
    .pipe(counter)
    .pipe(transform)
    .pipe(through2Batch.obj({batchSize: 10}))
    .pipe(sqsStream)
}

module.exports = {
  run
}
