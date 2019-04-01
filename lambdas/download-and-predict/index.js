/* global Buffer */
const axios = require('axios')

/**
 * Convert a url to a UTF-8 encoded string of base64 bytes.
 * endpoint, saves the result to a database
 *
 * Use this if you need to download tiles from a tile server and send them to
 * a prediction server. This will convert them into a string representing
 * base64 format which is more efficient than many other options.
 *
 * @param {string} url image url
 * @returns {string} UTF-8 encoded string of base64 bytes.
 */
async function getB64Image (url) {
  return axios
    .get(url, { responseType: 'arraybuffer' })
    .then(response => response.data.toString('base64').toString('utf8'))
}

/**
 * Lambda function called by SQS Trigger; downloads imagery, sends to prediction
 * endpoint, saves the result to a database
 *
 * @param {object} event SQS event
 * @param {object} context AWS context object
 * @param {function} cb AWS lambda callback
 */
// initialize our database connection variable outside the handler for possible reuse
let db
async function handler (event, context) {
  if (!db) {
    db = require('knex')({
      client: 'pg',
      connection: process.env.DATABASE_URL
    })
  }

  const tiles = event.Records.map(record => JSON.parse(record.body))
  const imagePromises = tiles.map(tile => {
    const url = process.env.TILE_ENDPOINT
      .replace('{}', tile.z)
      .replace('{}', tile.x)
      .replace('{}', tile.y)
      .replace('{}', process.env.TILE_ACCESS_TOKEN)
    return getB64Image(url).then(b64 => ({'image_bytes': { b64 }}))
  })
  const instances = await Promise.all(imagePromises)
  const payload = JSON.stringify({instances})

  // Send prediction request
  const pred = await axios.post(process.env.PREDICTION_ENDPOINT, payload)
    .then(resp => resp.data)
    .catch(err => console.error(err))

  // save prediction request to db
  return db('results').insert(tiles.map((tile, i) => {
    return {
      tile: Object.values(tile).join('-'),
      output: JSON.stringify(pred.predictions[i])
    }
  }))
}

module.exports.handler = handler
