import { Network } from "lucide-react";
import { motion } from "motion/react";
import { memo } from "react";
import { StatusBadge } from "@/components/ui/badge";
import { MemoryBadge } from "@/features/memory/MemoryCard";
import { cn } from "@/lib/cn";
import { money, patternLabel, paymentFormat, shortDate, timeOnly } from "@/lib/format";
import { TX_STATUS } from "@/lib/status";
import type { TxRow } from "@/types/api";

const STANDS_OUT = new Set(["flagged", "needs_analyst"]);

interface Props {
  row: TxRow;
  isNetwork: boolean;
  related: boolean;
  fresh: boolean;
  reduced: boolean;
  onSelect: (id: string) => void;
}

/** One stream row. Status changes animate in place (EX-16.1); flags stand out and flash once (LS-4). */
export const StreamRow = memo(function StreamRow({ row, isNetwork, related, fresh, reduced, onSelect }: Props) {
  const meta = TX_STATUS[row.status];
  const standsOut = STANDS_OUT.has(row.status);
  return (
    <motion.tr
      initial={fresh && !reduced ? { opacity: 0, y: -8 } : false}
      animate={{ opacity: 1, y: 0 }}
      onClick={() => onSelect(row.transaction_id)}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(row.transaction_id)}
      tabIndex={0}
      aria-label={`${row.transaction_id}, ${row.customer_name}, ${money(row.amount)}, ${meta.label}`}
      className={cn(
        "cursor-pointer border-b border-border text-sm transition-colors hover:bg-surface-2 focus-visible:bg-surface-2",
        row.status === "flagged" && "bg-flagged-soft/60",
        row.status === "needs_analyst" && "bg-review-soft/60",
        related && "outline-2 -outline-offset-2 outline-memory",
      )}
    >
      <td className={cn("w-1 p-0", standsOut && (row.status === "flagged" ? "bg-flagged" : "bg-review"))} aria-hidden />
      <td className="px-2 py-1.5 whitespace-nowrap text-muted tabular-nums">
        <span className="hidden xl:inline">{shortDate(row.timestamp).split(",")[0]} </span>
        {timeOnly(row.timestamp)}
      </td>
      <td className="max-w-44 truncate px-2 py-1.5" title={`${row.sender.name} ${row.sender.account ?? ""}`}>
        {row.sender.name}
        {row.sender.account && <span className="ml-1 font-mono text-[10px] text-muted">{row.sender.account}</span>}
      </td>
      <td className="max-w-44 truncate px-2 py-1.5" title={`${row.receiver.name} ${row.receiver.account ?? ""}`}>
        {row.receiver.name}
        {row.receiver.account && <span className="ml-1 font-mono text-[10px] text-muted">{row.receiver.account}</span>}
      </td>
      <td className="px-2 py-1.5 text-right font-medium whitespace-nowrap tabular-nums">{money(row.amount, row.currency)}</td>
      <td className="hidden px-2 py-1.5 whitespace-nowrap text-muted lg:table-cell">{paymentFormat(row.txn_type)}</td>
      <td className="px-2 py-1.5">
        <div className="flex flex-wrap items-center gap-1">
          <motion.span key={row.status} initial={reduced ? false : { scale: 0.85, opacity: 0.4 }} animate={{ scale: 1, opacity: 1 }}>
            <StatusBadge meta={meta} />
          </motion.span>
          {standsOut && row.pattern && row.pattern !== "none" && (
            <span className="text-xs font-medium">{patternLabel(row.pattern)}</span>
          )}
          <MemoryBadge cards={row.memory} />
          {row.replayed && <span className="text-[10px] text-memory" title="Agent result replayed from the recorded live run">replay</span>}
        </div>
      </td>
      <td className="px-2 py-1.5 whitespace-nowrap">
        {row.case_id && isNetwork && (
          <span className={cn("inline-flex items-center gap-1 rounded-full border px-1.5 py-px text-[11px]", standsOut ? "border-flagged text-flagged" : "border-memory/60 text-memory")}>
            <Network className="size-3" aria-hidden /> {standsOut ? row.case_id.replace("CASE-", "") : "related"}
          </span>
        )}
      </td>
    </motion.tr>
  );
});
