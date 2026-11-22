import { SegmentedControl as UISegmentedControl } from "../../../components/ui";

interface Option<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
}

export function SegmentedControl<T extends string>({
  label,
  value,
  options,
  onChange,
}: Props<T>) {
  return (
    <div>
      <UISegmentedControl
        label={label}
        value={value}
        options={options}
        onValueChange={onChange}
      />
    </div>
  );
}
