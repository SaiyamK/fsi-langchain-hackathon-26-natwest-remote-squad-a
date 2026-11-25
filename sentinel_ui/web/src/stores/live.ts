import { create } from "zustand";
import type { ServerEvent, Snapshot } from "@/types/api";
import { applyEvent, emptyLive, fromSnapshot, type LiveState } from "./reducer";

type Connection = "connecting" | "open" | "lost";

interface LiveStore extends LiveState {
  connection: Connection;
  load: (snap: Snapshot) => void;
  apply: (events: ServerEvent[]) => void;
  setConnection: (c: Connection) => void;
}

export const useLive = create<LiveStore>((set) => ({
  ...emptyLive,
  connection: "connecting",
  load: (snap) => set((s) => ({ ...fromSnapshot(snap, s.epoch) })),
  apply: (events) =>
    set((s) => {
      let next: LiveState = s;
      for (const e of events) next = applyEvent(next, e);
      return next;
    }),
  setConnection: (connection) => set({ connection }),
}));

/** "Now" in the stream: the newest released transaction's timestamp. */
export const selectClock = (s: LiveState): string | null => {
  const last = s.txOrder[s.txOrder.length - 1];
  return (last && s.txById[last]?.timestamp) || s.session?.clock || null;
};
