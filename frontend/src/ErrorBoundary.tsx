// Shows a plain message instead of a blank page if any part of the board fails to draw.
import { Component, type ReactNode } from 'react'

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) { return { error } }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="notice" style={{ margin: 40 }}>
        The board hit an error while drawing: {this.state.error.message}.{' '}
        <button className="btn" onClick={() => location.reload()}>Reload</button>
      </div>
    )
  }
}
