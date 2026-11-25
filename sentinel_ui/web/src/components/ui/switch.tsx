import * as RS from "@radix-ui/react-switch";

export function Switch({
  checked,
  onCheckedChange,
  label,
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-muted">
      <RS.Root
        checked={checked}
        onCheckedChange={onCheckedChange}
        className="relative h-4 w-7 rounded-full bg-border transition-colors data-[state=checked]:bg-accent"
      >
        <RS.Thumb className="block size-3 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-3.5" />
      </RS.Root>
      {label}
    </label>
  );
}
