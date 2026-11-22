/** Radar chart with normalised axes and theme aware polygons. */

import type { ChartGeometry } from "../types";
import { ChartLegend } from "./ChartLegend";
import styles from "./chartStyles.module.css";

/** Props accepted by {@link RadarChart}. */
export interface RadarChartProps {
  geometry: ChartGeometry;
}

/** Render radar rings, spokes, polygons and axis labels. */
export function RadarChart({ geometry }: RadarChartProps) {
  const centerX = geometry.width / 2;
  const centerY = geometry.height / 2;
  const radius = Math.max(
    20,
    Math.min(geometry.width, geometry.height) / 2 - geometry.padding - 18,
  );

  if (geometry.radar_shapes.length === 0) {
    return <div className={styles.empty}>No radar data to display</div>;
  }

  return (
    <div className={styles.wrapper}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${geometry.width} ${geometry.height}`}
        role="img"
        aria-label={`Radar chart with ${geometry.radar_axes.length} axes`}
      >
        <title>Radar chart</title>
        {geometry.radar_rings.map((ring) => (
          <circle
            className={styles.radarRing}
            key={ring}
            cx={centerX}
            cy={centerY}
            r={ring * radius}
          />
        ))}
        {geometry.radar_axes.map((axis) => (
          <g key={axis.label}>
            <line
              className={styles.radarAxis}
              x1={centerX}
              y1={centerY}
              x2={centerX + (axis.x * radius) / 1.18}
              y2={centerY + (axis.y * radius) / 1.18}
            />
            <text
              className={styles.radarLabel}
              x={centerX + axis.x * radius}
              y={centerY + axis.y * radius}
              textAnchor={
                axis.x > 0.1 ? "start" : axis.x < -0.1 ? "end" : "middle"
              }
              dominantBaseline="middle"
            >
              {axis.label}
            </text>
          </g>
        ))}
        <g transform={`translate(${centerX} ${centerY}) scale(${radius})`}>
          {geometry.radar_shapes.map((shape) => (
            <path
              className={styles.radarPolygon}
              key={shape.name}
              d={shape.path}
              stroke={shape.color}
              fill={shape.color}
              vectorEffect="non-scaling-stroke"
            >
              <title>{`${shape.name} radar profile`}</title>
            </path>
          ))}
        </g>
      </svg>
      <ChartLegend items={geometry.legend} />
    </div>
  );
}
