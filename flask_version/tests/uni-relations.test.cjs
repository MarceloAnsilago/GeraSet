const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const c = vm.createContext({document: {addEventListener() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/export.js'), 'utf8'), c);
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, '../../mt5_bridge/tests/fixtures/uni_relations.json'), 'utf8'));
for (const example of cases) test(`export/Bridge contract: ${example.name}`, () => {
    const validate = () => c.validateUniInputRelations(Object.entries(example.inputs).map(([key, value]) => `${key}=${value}`));
    if (example.valid) assert.doesNotThrow(validate); else assert.throws(validate);
});
