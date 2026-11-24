import assert from 'node:assert/strict';
import { matchesCompanyExperience as matches } from '../src/utils/companyExperience.ts';

assert.equal(matches('0-2 years', 0), true);
assert.equal(matches('0-2 years', 3), false);
assert.equal(matches('Minimum 3 years', 6), true);
assert.equal(matches('6-12 months', 1), true);
assert.equal(matches('6-12 months', 6), false);
assert.equal(matches('1.5-3 years', 1), false);
assert.equal(matches('1.5-3 years', 2), true);
assert.equal(matches('Fresher', 0), true);
assert.equal(matches(undefined, 0), false);
assert.equal(matches('Senior', 5), false);
console.log('Company experience eligibility checks passed.');
