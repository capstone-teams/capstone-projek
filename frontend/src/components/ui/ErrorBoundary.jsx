import React from 'react';
import { Card } from './Card';
import { Alert } from './Alert';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <Card title="Terjadi Kesalahan">
          <Alert tone="danger">
            {this.state.error?.message || 'Terjadi kesalahan yang tidak terduga pada halaman ini.'}
          </Alert>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
            >
              Muat ulang halaman
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Coba lagi
            </button>
          </div>
        </Card>
      );
    }
    return this.props.children;
  }
}
