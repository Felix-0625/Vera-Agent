import { defineConfig } from 'vitest/config'

// Unit tests are co-located with the code they cover (`src/**/*.test.ts`).
// They run in Node; tests that need browser APIs stub them explicitly.
export default defineConfig({
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'node',
  },
})
