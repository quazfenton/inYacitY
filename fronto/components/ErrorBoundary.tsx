import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends React.Component<{}, ErrorBoundaryState> {
  constructor(props: {}) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-void text-zinc-100 p-4">
          <div className="text-center">
            <h1 className="text-4xl font-black text-acid mb-4">SYSTEM ERROR</h1>
            <p className="text-zinc-400 mb-4">Something went wrong with this component.</p>
            <button 
              className="px-4 py-2 border border-zinc-700 hover:border-acid hover:bg-acid hover:text-void transition-colors"
              onClick={() => window.location.reload()}
            >
              REFRESH PAGE
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;