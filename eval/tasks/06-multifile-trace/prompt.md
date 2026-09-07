Running `node --experimental-strip-types src/main.ts` prints the wrong port. It should
print the port from `config.json`, which is 8080, but it prints 3000.

Find the root cause and fix it. There is one bug, and it is not in `config.json`.
Then run `node --test --experimental-strip-types` and make sure the suite passes.
Do not change the tests.
