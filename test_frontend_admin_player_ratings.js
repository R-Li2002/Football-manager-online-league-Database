const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const admin = fs.readFileSync(path.join(__dirname, 'static/js/app.admin.js'), 'utf8');
const players = fs.readFileSync(path.join(__dirname, 'static/js/app.players.js'), 'utf8');
const css = fs.readFileSync(path.join(__dirname, 'static/app.css'), 'utf8');

assert.match(players, /updatePlayerField\(\$\{player\.uid\}, 'ca', this\.value\)/);
assert.match(players, /updatePlayerField\(\$\{player\.uid\}, 'pa', this\.value\)/);
assert.match(players, /player-rating-input/);
assert.match(admin, /\['age', 'ca', 'pa'\]\.includes\(field\)/);
assert.match(admin, /requestBody\[field\] = parsedValue/);
assert.match(css, /\.editable-input\.player-rating-input/);

console.log('admin player CA\/PA editing frontend checks passed');
