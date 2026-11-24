import { afterEach, expect } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

expect.extend(matchers)
afterEach(() => cleanup())

// jsdom does not implement <dialog> methods.
if (typeof HTMLDialogElement !== 'undefined') {
  HTMLDialogElement.prototype.showModal ??= function showModal() {
    this.open = true
  }
  HTMLDialogElement.prototype.close ??= function close() {
    this.open = false
  }
}
