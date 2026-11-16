import { euro } from "../format";

export function BarChart({
  title,
  subtitle,
  points,
}: {
  title: string;
  subtitle: string;
  points: Array<{ label: string; value: number; detail?: string }>;
}) {
  const max = Math.max(...points.map((point) => point.value), 1);
  return (
    <section className="card chart">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      {points.length ? (
        <div className="bar-chart">
          {points.map((point) => (
            <div className="bar-row" key={point.label}>
              <span>{point.label}</span>
              <div>
                <i style={{ width: `${(point.value / max) * 100}%` }} />
                <b>
                  {point.value.toLocaleString("es-ES", {
                    maximumFractionDigits: 2,
                  })}
                </b>
              </div>
              {point.detail && <small>{point.detail}</small>}
            </div>
          ))}
        </div>
      ) : (
        <p className="empty">Todavía no hay datos para esta gráfica.</p>
      )}
    </section>
  );
}

export function LineChart({
  title,
  subtitle,
  points,
}: {
  title: string;
  subtitle: string;
  points: Array<{ label: string; value: number }>;
}) {
  if (!points.length)
    return (
      <section className="card chart">
        <h2>{title}</h2>
        <p>{subtitle}</p>
        <p className="empty">Todavía no hay datos para esta gráfica.</p>
      </section>
    );
  const width = 600;
  const height = 210;
  const padding = 28;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const position = (index: number, value: number) => ({
    x:
      padding +
      (index * (width - padding * 2)) / Math.max(points.length - 1, 1),
    y: height - padding - ((value - min) * (height - padding * 2)) / range,
  });
  const path = points
    .map((point, index) => {
      const { x, y } = position(index, point.value);
      return `${index ? "L" : "M"} ${x} ${y}`;
    })
    .join(" ");
  const labelEvery = Math.ceil(points.length / 6);
  return (
    <section className="card chart line-chart">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
        />
        <path d={path} />
        {points.map((point, index) => {
          const { x, y } = position(index, point.value);
          const showLabel =
            index % labelEvery === 0 || index === points.length - 1;
          return (
            <g key={`${point.label}-${point.value}`}>
              <title>{`${point.label}: ${euro.format(point.value)}`}</title>
              <circle cx={x} cy={y} r="5" />
              {points.length <= 6 && (
                <text x={x} y={y - 10}>
                  {euro.format(point.value)}
                </text>
              )}
              {showLabel && (
                <text x={x} y={height - 8}>
                  {point.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <details className="chart-data">
        <summary>Ver datos de la gráfica</summary>
        <ul>
          {points.map((point, index) => (
            <li key={`${point.label}-${index}`}>
              {point.label}: {euro.format(point.value)}
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
