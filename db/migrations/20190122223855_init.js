exports.up = async function (knex) {
  try {
    return knex.schema.createTable('results', t => {
      t.string('tile').primary()
      t.jsonb('output')
    })
  } catch (e) {
    console.error(e)
  }
}

exports.down = async function (knex) {
  return knex.schema.dropTable('results')
}
