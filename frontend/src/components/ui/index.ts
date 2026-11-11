/**
 * Barrel export for the dashboard design system.
 */

export { Button, ButtonGroup, IconButton } from "./Button";
export type {
  ButtonGroupProps,
  ButtonProps,
  ButtonSize,
  ButtonVariant,
  IconButtonProps,
} from "./Button";

export {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Divider,
  StatCard,
} from "./Card";
export type {
  CardHeaderProps,
  CardProps,
  CardTitleProps,
  StatCardProps,
} from "./Card";

export { Avatar, AvatarGroup, Badge, Kbd, StatusDot, colorOf, initialsOf } from "./Display";
export type { AvatarGroupProps, AvatarProps, BadgeProps, BadgeTone } from "./Display";

export {
  Checkbox,
  Input,
  Select,
  Switch,
  Textarea,
} from "./Field";
export type {
  CheckboxProps,
  FieldBaseProps,
  InputProps,
  SelectOption,
  SelectProps,
  SwitchProps,
  TextareaProps,
} from "./Field";

export {
  EmptyState,
  ErrorState,
  Progress,
  ScoreRing,
  Skeleton,
  Spinner,
} from "./Feedback";
export type {
  EmptyStateProps,
  ErrorStateProps,
  ProgressProps,
  ScoreRingProps,
  SkeletonProps,
  SpinnerProps,
} from "./Feedback";

export {
  Drawer,
  Menu,
  MenuDivider,
  MenuItem,
  Modal,
  Popover,
  Tooltip,
} from "./Overlay";
export type {
  DrawerProps,
  MenuItemProps,
  MenuProps,
  ModalProps,
  PopoverProps,
  TooltipProps,
} from "./Overlay";

export {
  SegmentedControl,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useTabs,
} from "./Tabs";
export type {
  SegmentOption,
  SegmentedControlProps,
  TabsContentProps,
  TabsListProps,
  TabsProps,
  TabsTriggerProps,
} from "./Tabs";

export {
  SortableTable,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "./Table";
export type {
  SortableTableProps,
  TableBodyProps,
  TableCellProps,
  TableHeadProps,
  TableHeaderCellProps,
  TableProps,
  TableRowProps,
} from "./Table";

export { ThemeToggle } from "./ThemeToggle";
export type { ThemeToggleProps } from "./ThemeToggle";

export { useCountUp, useDebouncedValue, useHover, usePrefersReducedMotion } from "./motion";

export {
  useDebounced,
  useElementSize,
  useFactory,
  usePrevious,
  useStableCallback,
  useStableValue,
} from "./memoization";

export { VirtualTable } from "./VirtualTable";
export type { VirtualColumn, VirtualTableProps } from "./VirtualTable";

export { useVirtualList } from "./useVirtualList";
export type { UseVirtualListOptions, UseVirtualListResult } from "./useVirtualList";

export { ToastProvider, ToastViewport, useToast } from "./Toast";
export type { Toast, ToastOptions, ToastProviderProps, ToastTone } from "./Toast";
