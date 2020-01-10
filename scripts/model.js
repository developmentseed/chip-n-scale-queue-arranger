#! /usr/bin/env node

const Q = require('d3-queue').queue;
const mkdir = require('mkdirp').sync;
const pipeline = require('stream').pipeline;
const fs = require('fs');
const os = require('os');
const CP = require('child_process');
const tmp = os.tmpdir() + '/' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
const path = require('path');
const argv = require('minimist')(process.argv, {
    boolean: ['help']
});

function help() {
    console.error();
    console.error('  Build TFServing docker images for Chip-N-Scale given a GS model location');
    console.error();
    console.error('Usage:');
    console.error();
    console.error('  .yarn model <gs:// folder containing .pb model');
    console.error();
}

let model = argv._[2];

if (!model || argv.help) {
    return help();
}

model = new URL(model);

if (model.protocol === 's3:') {
    console.error('s3: models will be supported in the future');
    process.exit();
} else if (model.protocol !== 'gs:') {
    console.error('Only gs:// protocols are supported');
    process.exit();
}

mkdir(tmp + '/001');
console.error(`ok - tmp dir: ${tmp}`);

if (model.protocol === 'gs:') {
    return gs_get(model, docker);
}

/**
 * Given a Google Storage Folder containing a model,
 * fetch and save it to disk
 */
function gs_get(model, cb) {
    const gs = new (require('@google-cloud/storage').Storage)();
    const bucket = gs.bucket(model.host);

    if (!process.env.GOOGLE_APPLICATION_CREDENTIALS) {
        console.error('GOOGLE_APPLICATION_CREDENTIALS environment var must be set');
        console.error('See: https://cloud.google.com/docs/authentication/getting-started');
        process.exit();
    }

    const model_path = model.pathname.replace(/^\//, '');

    bucket.getFiles({
        prefix: model_path
    }, (err, files) => {
        if (err) return cb(err);

        const q = new Q(1);

        for (let file of files) {
            if (file.name[file.name.length - 1] === '/') continue;

            const name = path.parse(file.name.replace(model_path, ''));

            if (name.dir) {
                mkdir(path.resolve(tmp + '/001', name.dir));
            }

            q.defer((file, name, done) => {
                console.error(`ok - fetching ${name.dir + '/' +  name.base}`);
                pipeline(
                    file.createReadStream(),
                    fs.createWriteStream(path.resolve(tmp + '/001', name.dir, name.base)),
                    done
                );
            }, file, name);
        }

        q.awaitAll(cb);
    });
}

function docker(err, res) {
    if (err) throw err;

    console.error('ok - pulling tensorflow/serving docker image');
    CP.execSync(`
        docker pull tensorflow/serving
    `);

    // Ignore errors, these are to ensure the next commands don't err
    try {
        CP.execSync(`
            docker kill serving_base
        `);
    } catch(err) {
        console.error('ok - no old task to stop');
    }

    try {
        CP.execSync(`
            docker rm serving_base
        `);
    } catch(err) {
        console.error('ok - no old image to remove');
    }

    CP.execSync(`
        docker run -d --name serving_base tensorflow/serving
    `);

    CP.execSync(`
        docker cp ${tmp}/ serving_base:/models/default/ \
    `);

    CP.execSync(`
        docker commit --change "ENV MODEL_NAME default" serving_base developmentseed/default:v1
    `);

    CP.execSync(`
        docker kill serving_base
    `);
}
