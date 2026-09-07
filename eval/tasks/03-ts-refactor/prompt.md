`src/create-user.ts` and `src/update-user.ts` contain the same email and age
validation logic, copied. Extract it into a single shared module and use it from
both, without changing any behaviour.

The existing tests must still pass. Run them with
`node --test --experimental-strip-types`. Do not change the tests.
