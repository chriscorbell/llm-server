`src/handlers.ts` holds a few hundred generated request handlers. Exactly one of them
does not follow the convention that every other handler follows: it fails to check
authorisation before touching the store.

Find that handler, fix it so it matches the convention used by its neighbours, and
leave everything else alone. Then run `node --test --experimental-strip-types`.
