/** A number on a card: label, value, optional icon and a small line underneath. */
export default function StatCard({ label, value, sub, icon: Icon }) {
  return (
    <div className="vmt-card vmt-stat">
      <div className="vmt-stat-top">
        <span className="vmt-stat-label">{label}</span>
        {Icon && (
          <span className="vmt-stat-icon" aria-hidden="true">
            <Icon className="vmt-icon" />
          </span>
        )}
      </div>
      <span className="vmt-stat-value">{value}</span>
      {sub && <span className="vmt-stat-sub">{sub}</span>}
    </div>
  );
}
