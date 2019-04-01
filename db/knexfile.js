var path = require('path')
module.exports = {
  remote: {
    client: 'pg',
    debug: process.env.KNEX_DEBUG || false,
    connection: process.env.DATABASE_URL,
    migrations: {
      directory: path.join(__dirname, 'migrations')
    }
  }
}
