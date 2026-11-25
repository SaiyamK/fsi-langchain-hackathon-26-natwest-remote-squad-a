import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useLive } from "@/stores/live";

/** Case detail, refetched whenever the server reports the case changed (or the stream clock moves on). */
export function useCase(caseId: string) {
  const seq = useLive((s) => s.cases[caseId]?.updated_seq ?? 0);
  const exists = useLive((s) => caseId in s.cases);
  return useQuery({
    queryKey: ["case", caseId, seq],
    queryFn: () => api.case(caseId),
    enabled: exists,
    placeholderData: (prev) => prev,
    staleTime: 10_000,
  });
}
