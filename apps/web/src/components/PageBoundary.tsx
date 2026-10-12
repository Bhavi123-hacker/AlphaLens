import { Component, type ReactNode } from 'react'

// Never render raw exceptions, request details or private data in a crash fallback.
export class PageBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    return this.state.failed ? <section className="empty-state" role="alert">
      <h1>Page could not be loaded</h1>
      <p>A required application module did not load or render. Reload to retry. If this persists, check the local service and available system memory.</p>
      <button className="button" onClick={() => window.location.reload()}>Reload local page</button>
    </section> : this.props.children
  }
}
