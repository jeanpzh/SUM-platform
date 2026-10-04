import { registerHooks } from 'node:module'
import { existsSync } from 'node:fs'

// Run the project's TypeScript with Node 24's native type stripping.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier.startsWith('#/')) {
      return {
        url: new URL('../../src/' + specifier.slice(2) + '.ts', import.meta.url)
          .href,
        shortCircuit: true,
      }
    }
    if (specifier.startsWith('.') && context.parentURL) {
      const source = new URL(specifier + '.ts', context.parentURL)
      if (existsSync(source)) return { url: source.href, shortCircuit: true }
    }
    return nextResolve(specifier, context)
  },
})
