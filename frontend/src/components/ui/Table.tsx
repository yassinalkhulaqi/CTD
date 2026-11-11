/**
 * Data table primitives with sortable headers and sticky toolbars.
 */

import { useMemo, useState, type HTMLAttributes, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { cn } from "../../lib/utils";
import styles from "./Table.module.css";

/** Props accepted by {@link Table}. */
export interface TableProps extends HTMLAttributes<HTMLTableElement> {
  /** Render the table with a sticky header. */
  sticky?: boolean;
  /** Render the table inside a horizontally scrollable container. */
  scroll?: boolean;
}

/**
 * Render a data table.
 *
 * @param props - The component props.
 * @returns The table element.
 */
export function Table({ sticky = false, scroll = true, className, children, ...rest }: TableProps) {
  const table = (
    <table className={cn(styles.table, sticky && styles.tableSticky, className)} {...rest}>
      {children}
    </table>
  );

  if (!scroll) return table;

  return (
    <div className={styles.scroll} role="region" aria-label="Data table" tabIndex={0}>
      {table}
    </div>
  );
}

/** Props accepted by {@link TableHead}. */
export type TableHeadProps = HTMLAttributes<HTMLTableSectionElement>;

/**
 * Render the header section of a table.
 *
 * @param props - The component props.
 * @returns The section element.
 */
export function TableHead({ className, children, ...rest }: TableHeadProps) {
  return (
    <thead className={cn(styles.head, className)} {...rest}>
      {children}
    </thead>
  );
}

/** Props accepted by {@link TableBody}. */
export type TableBodyProps = HTMLAttributes<HTMLTableSectionElement>;

/**
 * Render the body section of a table.
 *
 * @param props - The component props.
 * @returns The section element.
 */
export function TableBody({ className, children, ...rest }: TableBodyProps) {
  return (
    <tbody className={cn(styles.body, className)} {...rest}>
      {children}
    </tbody>
  );
}

/** Props accepted by {@link TableRow}. */
export interface TableRowProps extends HTMLAttributes<HTMLTableRowElement> {
  /** Whether the row is selected. */
  selected?: boolean;
  /** Called when the row is activated by a click. */
  onActivate?: () => void;
}

/**
 * Render a table row.
 *
 * @param props - The component props.
 * @returns The row element.
 */
export function TableRow({
  selected = false,
  onActivate,
  className,
  children,
  ...rest
}: TableRowProps) {
  return (
    <tr
      className={cn(styles.row, selected && styles.rowSelected, onActivate && styles.rowInteractive, className)}
      onClick={onActivate}
      {...rest}
    >
      {children}
    </tr>
  );
}

/** Props accepted by {@link TableHeaderCell}. */
export interface TableHeaderCellProps extends HTMLAttributes<HTMLTableCellElement> {
  /** The column key used for sorting. */
  sortKey?: string;
  /** The current sort direction of the column. */
  sortDirection?: "asc" | "desc" | null;
  /** Called when the header is activated. */
  onSort?: (key: string) => void;
  /** Right align the cell content. */
  align?: "left" | "right" | "center";
}

/**
 * Render a table header cell with an optional sort control.
 *
 * @param props - The component props.
 * @returns The cell element.
 */
export function TableHeaderCell({
  sortKey,
  sortDirection = null,
  onSort,
  align = "left",
  className,
  children,
  ...rest
}: TableHeaderCellProps) {
  const sortable = Boolean(sortKey && onSort);
  const icon =
    sortDirection === "asc" ? (
      <ArrowUp size={13} aria-hidden="true" />
    ) : sortDirection === "desc" ? (
      <ArrowDown size={13} aria-hidden="true" />
    ) : (
      <ChevronsUpDown size={13} className={styles.sortIdle} aria-hidden="true" />
    );

  return (
    <th
      className={cn(styles.headerCell, styles[`align-${align}`], className)}
      aria-sort={sortDirection === "asc" ? "ascending" : sortDirection === "desc" ? "descending" : undefined}
      scope="col"
      {...rest}
    >
      {sortable ? (
        <button type="button" className={styles.sortButton} onClick={() => onSort?.(sortKey!)}>
          {children}
          {icon}
        </button>
      ) : (
        children
      )}
    </th>
  );
}

/** Props accepted by {@link TableCell}. */
export interface TableCellProps extends HTMLAttributes<HTMLTableCellElement> {
  /** Right align the cell content. */
  align?: "left" | "right" | "center";
}

/**
 * Render a table cell.
 *
 * @param props - The component props.
 * @returns The cell element.
 */
export function TableCell({ align = "left", className, children, ...rest }: TableCellProps) {
  return (
    <td className={cn(styles.cell, styles[`align-${align}`], className)} {...rest}>
      {children}
    </td>
  );
}

/** A sortable table with a controlled sort state. */
export interface SortableTableProps<T> {
  /** The rows of the table. */
  rows: T[];
  /** Derive a unique key for a row. */
  rowKey: (row: T) => string;
  /** The column definitions. */
  columns: Array<{
    key: string;
    header: ReactNode;
    align?: "left" | "right" | "center";
    render: (row: T) => ReactNode;
    sortValue?: (row: T) => string | number;
  }>;
  /** The initial sort key. */
  defaultSortKey?: string;
  /** Rendered when no rows are available. */
  emptyState?: ReactNode;
}

/**
 * Render a table with client side sorting.
 *
 * @param props - The component props.
 * @returns The table element.
 */
export function SortableTable<T>({
  rows,
  rowKey,
  columns,
  defaultSortKey,
  emptyState,
}: SortableTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(defaultSortKey ?? null);
  const [direction, setDirection] = useState<"asc" | "desc">("asc");

  const sorted = useMemo(() => {
    if (!sortKey) return rows;
    const column = columns.find((item) => item.key === sortKey);
    if (!column?.sortValue) return rows;

    const factor = direction === "asc" ? 1 : -1;
    return [...rows].sort((left, right) => {
      const a = column.sortValue!(left);
      const b = column.sortValue!(right);
      if (typeof a === "number" && typeof b === "number") return (a - b) * factor;
      return String(a).localeCompare(String(b)) * factor;
    });
  }, [rows, sortKey, direction, columns]);

  function handleSort(key: string) {
    if (key === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setDirection("asc");
  }

  if (rows.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  return (
    <Table>
      <TableHead>
        <TableRow>
          {columns.map((column) => (
            <TableHeaderCell
              key={column.key}
              sortKey={column.sortValue ? column.key : undefined}
              sortDirection={sortKey === column.key ? direction : null}
              onSort={handleSort}
              align={column.align}
            >
              {column.header}
            </TableHeaderCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {sorted.map((row) => (
          <TableRow key={rowKey(row)}>
            {columns.map((column) => (
              <TableCell key={column.key} align={column.align}>
                {column.render(row)}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
