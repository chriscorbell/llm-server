export type RetryOptions = {
  attempts: number;
  /** Milliseconds to wait after attempt n, 1-indexed. */
  backoffMs?: (attempt: number) => number;
};

export class RetryError extends Error {
  attempts: number;
  reason: unknown;

  constructor(message: string, attempts: number, reason: unknown) {
    super(message);
    this.name = "RetryError";
    this.attempts = attempts;
    this.reason = reason;
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function retry<T>(
  operation: () => Promise<T>,
  options: RetryOptions,
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 1; attempt < options.attempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (options.backoffMs) await sleep(options.backoffMs(attempt));
    }
  }
  throw new RetryError(
    `operation failed after ${options.attempts} attempts`,
    options.attempts,
    lastError,
  );
}
