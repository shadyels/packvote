import "@testing-library/jest-dom";

// Node.js v25 exposes a native `localStorage` global that replaces jsdom's
// Storage implementation in the vitest worker environment.  The native version
// is just `{}` (no getItem/setItem/removeItem methods) because no
// --localstorage-file flag was provided.  Replace it with a proper in-memory
// implementation so that tests can call getItem/setItem/removeItem normally.

const _buildStorage = (): Storage => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string): string | null => (key in store ? store[key] : null),
    setItem: (key: string, value: string): void => {
      store[key] = value;
    },
    removeItem: (key: string): void => {
      Reflect.deleteProperty(store, key);
    },
    clear: (): void => {
      store = {};
    },
    key: (index: number): string | null =>
      Object.keys(store)[index] ?? null,
    get length(): number {
      return Object.keys(store).length;
    },
  } as Storage;
};

const _storageMock = _buildStorage();

Object.defineProperty(globalThis, "localStorage", {
  value: _storageMock,
  writable: true,
});
