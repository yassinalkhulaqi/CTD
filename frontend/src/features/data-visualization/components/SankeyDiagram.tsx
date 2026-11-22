/** Sankey flow diagram rendered from normalised link geometry. */

import type { ChartGeometry } from "../types";
import styles from "./chartStyles.module.css";

/** Props accepted by {@link SankeyDiagram}. */
export interface SankeyDiagramProps {
  geometry: ChartGeometry;
}

/** Render Sankey ribbons and their labelled stage nodes. */
export function SankeyDiagram({ geometry }: SankeyDiagramProps) {
  if (geometry.sankey_flows.length === 0) {
    return <div className={styles.empty}>No flow data to display</div>;
  }

  return (
    <div className={styles.wrapper}>
      <svg
        className={styles.svg}
        viewBox={`0 0 ${geometry.width} ${geometry.height}`}
        role="img"
        aria-label={`Sankey diagram with ${geometry.sankey_flows.length} flows`}
      >
        <title>Sankey flow diagram</title>
        <g>
          {geometry.sankey_flows.map((flow, index) => (
            <path
              className={styles.flow}
              key={`${flow.source}-${flow.target}-${index}`}
              d={flow.path}
              stroke={flow.color}
              strokeWidth={flow.width}
              strokeLinecap="round"
              tabIndex={0}
              role="img"
              aria-label={`${flow.source} to ${flow.target}: ${flow.value}`}
            >
              <title>{`${flow.source} → ${flow.target}: ${flow.value}`}</title>
            </path>
          ))}
        </g>
        <g>
          {geometry.sankey_nodes.map((node) => {
            const nearRight = node.x > geometry.width * 0.7;
            return (
              <g key={node.id}>
                <rect
                  className={styles.node}
                  x={node.x}
                  y={node.y}
                  width={node.width}
                  height={node.height}
                  rx={3}
                  fill={node.color}
                >
                  <title>{`${node.label}: ${node.value}`}</title>
                </rect>
                <text
                  className={styles.nodeLabel}
                  x={nearRight ? node.x - 6 : node.x + node.width + 6}
                  y={node.y + Math.max(6, node.height / 2)}
                  textAnchor={nearRight ? "end" : "start"}
                  dominantBaseline="middle"
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
