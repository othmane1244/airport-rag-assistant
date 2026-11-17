export default function GlassCard({ children, className = "", onClick, id, ...props }) {
  return (
    <div
      className={`glass-card ${className}`}
      onClick={onClick}
      id={id}
      {...props}
    >
      {children}
    </div>
  );
}
