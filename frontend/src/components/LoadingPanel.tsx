export function LoadingPanel({ label = "Loading analysis" }: { label?: string }) {
  return <div className="loading-panel" role="status"><span className="loading-mark" /><p>{label}</p></div>;
}

export function ErrorPanel({ message }: { message: string }) {
  return <div className="error-panel" role="alert"><strong>We could not load this view.</strong><p>{message}</p></div>;
}
