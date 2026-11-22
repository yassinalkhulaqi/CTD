/**
 * A windowed table rendering only the visible rows.
 */

import { useMemo, useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "./Table";
import { useVirtualList } from "./useVirtualList";
import styles from "./VirtualTable.module.css";

/** A column of the virtualised table. */
export interface VirtualColumn<T> {
  /** The identifier of the column. */
  key: string;
  /** The header of the column. */
  header: ReactNode;
  /** The content of the cell. */
  render: (row: T) => ReactNode;
  /** The width of the column. */
  width?: string;
  /** The alignment of the column. */
  align?: "left" | "right" | "center";
}

/** Props accepted by {@link VirtualTable}. */
export interface VirtualTableProps<T> {
  /** The rows of the table. */
  rows: T[];
  /** The columns of the table. */
  columns: Array<VirtualColumn<T>>;
  /** Derive a unique key for a row. */
  rowKey: (row: T) => string;
  /** The height of a row, in pixels. */
  rowHeight?: number;
  /** The height of the viewport, in pixels. */
  height?: number;
  /** Called when a row is activated. */
  onActivate?: (row: T) => void;
  /** Accessible label of the scroll region. */
  label?: string;
  /** Copy shown when there are no rows. */
  emptyMessage?: string;
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render a table windowing its rows for large datasets.
 *
 * @param props - The component props.
 * @returns The table element.
 */
export function VirtualTable<T>({
  rows,
  columns,
  rowKey,
  rowHeight = 44,
  height = 420,
  onActivate,
  label = "Scrollable data table",
  emptyMessage = "Nothing to show yet.",
  className,
}: VirtualTableProps<T>) {
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const { visible, totalHeight, offsetY, scrollRef, onScroll } = useVirtualList(
    {
      items: rows,
      itemHeight: rowHeight,
      viewportHeight: height,
    },
  );

  const body = useMemo(
    () =>
      visible.map((row) => {
        const key = rowKey(row);
        return (
          <TableRow
            key={key}
            selected={key === activeKey}
            onActivate={
              onActivate
                ? () => {
                    setActiveKey(key);
                    onActivate(row);
                  }
                : undefined
            }
            style={{ height: rowHeight }}
          >
            {columns.map((column) => (
              <TableCell
                key={column.key}
                align={column.align}
                style={{ width: column.width }}
              >
                {column.render(row)}
              </TableCell>
            ))}
          </TableRow>
        );
      }),
    [activeKey, columns, onActivate, rowHeight, rowKey, visible],
  );

  return (
    <div
      ref={scrollRef as React.RefObject<HTMLDivElement>}
      onScroll={onScroll}
      className={cn(styles.viewport, className)}
      style={{ height }}
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      <Table scroll={false}>
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableHeaderCell
                key={column.key}
                align={column.align}
                style={{ width: column.width }}
              >
                {column.header}
              </TableHeaderCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <tr>
              <td className={styles.empty} colSpan={columns.length}>
                {emptyMessage}
              </td>
            </tr>
          ) : null}
          <tr style={{ height: offsetY }} aria-hidden="true">
            <td
              colSpan={columns.length}
              style={{ padding: 0, border: "none" }}
            />
          </tr>
          {body}
          <tr
            style={{
              height: Math.max(
                0,
                totalHeight - offsetY - visible.length * rowHeight,
              ),
            }}
            aria-hidden="true"
          >
            <td
              colSpan={columns.length}
              style={{ padding: 0, border: "none" }}
            />
          </tr>
        </TableBody>
      </Table>
    </div>
  );
}
