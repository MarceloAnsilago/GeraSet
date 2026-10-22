const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({document: {addEventListener() {}}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/export.js'), 'utf8'), context);

function lines(overrides = {}) {
    const values = {
        setup_entry_start: '09:30', setup_entry_end: '17:00',
        'schedule-entry-start-start': '09:00', 'schedule-entry-start-end': '10:00',
        'schedule-entry-end-start': '16:00', 'schedule-entry-end-end': '18:00',
        ...overrides,
    };
    return Array.from(context.scheduleSetLines(Object.entries(values).map(([key, value]) => ({key, value}))));
}

test('schedule converts HH:MM and exports separate values and five-minute optimization ranges', () => {
    assert.deepEqual(lines(), ['InpEntryStart=570||540||5||600||Y', 'InpEntryEnd=1020||960||5||1080||Y']);
});

test('equal bounds disable optimization without replacing the fixed value', () => {
    assert.equal(lines({'schedule-entry-start-end': '09:00'})[0], 'InpEntryStart=570||540||5||540||N');
});

test('reversed optimization bounds are normalized but overnight trading values are preserved', () => {
    assert.deepEqual(lines({
        setup_entry_start: '22:00', setup_entry_end: '02:00',
        'schedule-entry-start-start': '23:55', 'schedule-entry-start-end': '22:00',
        'schedule-entry-end-start': '02:00', 'schedule-entry-end-end': '02:00',
    }), ['InpEntryStart=1320||1320||5||1435||Y', 'InpEntryEnd=120||120||5||120||N']);
});

test('malformed times and equal fixed entry times fail validation', () => {
    for (const value of ['', '24:00', '09:31', '9:30', '12:60', '570', null, '00:00\n']) {
        assert.throws(() => lines({setup_entry_start: value}), {name: 'ScheduleValidationError'});
        assert.throws(() => lines({'schedule-entry-end-end': value}), {name: 'ScheduleValidationError'});
    }
    assert.throws(() => lines({setup_entry_end: '09:30'}), {name: 'ScheduleValidationError'});
    assert.throws(() => context.scheduleSetLines([]), {name: 'ScheduleValidationError'});
});

test('valid fixed hours cannot hide an invalid equal-hour optimization pass', () => {
    assert.throws(() => lines({'schedule-entry-end-start': '10:00'}), {name: 'ScheduleValidationError'});
    assert.throws(() => lines({'schedule-entry-start-start': '23:55', 'schedule-entry-start-end': '00:00'}), {name: 'ScheduleValidationError'});
});

test('every five-minute option maps to the corresponding Uni minute value', () => {
    for (let minutes = 0; minutes <= 1435; minutes += 5) {
        const time = `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
        assert.equal(lines({setup_entry_start: time, setup_entry_end: minutes === 0 ? '00:05' : '00:00'})[0].split('||')[0], `InpEntryStart=${minutes}`);
    }
});
