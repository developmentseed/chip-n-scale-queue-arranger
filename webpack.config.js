const path = require('path')
const glob = require('glob')
const webpack = require('webpack')
const pckg = require('./package.json')

function getEntries () {
  const output = glob.sync('./lambdas/*')
    .map((filename) => {
      const entry = {}
      entry[path.basename(filename)] = filename
      return entry
    })
    .reduce((finalObject, entry) => Object.assign(finalObject, entry), {})

  return output
}

module.exports = {
  entry: getEntries(),
  output: {
    path: path.join(__dirname, 'dist'),
    library: '[name]',
    libraryTarget: 'commonjs2',
    filename: '[name]/index.js'
  },
  target: 'node',
  externals: [
    'aws-sdk'
  ],
  node: {
    __dirname: false,
    __filename: false
  },
  // devtool: '#inline-source-map',
  resolve: {
    symlinks: false,
    alias: {
      'aws-sdk': 'aws-sdk/dist/aws-sdk',
      // the below lines are needed because of https://github.com/elastic-coders/serverless-webpack/issues/78
      'pg-native': path.join(__dirname, 'lib/null.js'),
      'pg.js/lib/utils.js': path.join(__dirname, 'lib/null.js'),
      'pg.js/lib/result.js': path.join(__dirname, 'lib/null.js')
    }
  },

  plugins: [
    new webpack.IgnorePlugin(/mariasql/, /\/knex\//),
    new webpack.IgnorePlugin(/mssql/, /\/knex\//),
    new webpack.IgnorePlugin(/mysql/, /\/knex\//),
    new webpack.IgnorePlugin(/mysql2/, /\/knex\//),
    new webpack.IgnorePlugin(/oracle/, /\/knex\//),
    new webpack.IgnorePlugin(/oracledb/, /\/knex\//),
    new webpack.IgnorePlugin(/pg-query-stream/, /\/knex\//),
    new webpack.IgnorePlugin(/sqlite3/, /\/knex\//),
    new webpack.IgnorePlugin(/strong-oracle/, /\/knex\//),
    new webpack.IgnorePlugin(/pg-native/, /\/pg\//)
  ],

  module: {
    rules: [
      {
        include: glob.sync('./lambdas/*/index.js', { realpath: true })
          .map(filename => path.resolve(__dirname, filename)),
        exclude: /node_modules/,
        loader: 'prepend-loader',
        query: {
          data: "if (!global._babelPolyfill) require('babel-polyfill');"
        }
      },
      {
        test: /\.js$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        options: pckg.babel
      },
      {
        test: /\.json$/,
        loader: 'json-loader'
      }
    ]
  }
}
