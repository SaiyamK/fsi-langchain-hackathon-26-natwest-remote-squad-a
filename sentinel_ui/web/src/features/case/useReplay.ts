import { useCallback, useEffect, useMemo, useState } from "react";
import type { Moment, TimelineItem } from "@/types/api";
import { frameAt } from "./replay";

const STEP_MS = 700;
const MOMENT_HOLD_MS = 1600;

/** Play / pause / step / scrub through a case's transfers (FR-6.2, EX-5). Key moments hold with a caption. */
export function useReplay(timeline: TimelineItem[], moments: Moment[], autoplay: boolean, reduced: boolean) {
  const last = timeline.length - 1;
  const [cursor, setCursor] = useState(autoplay && !reduced ? -1 : last);
  const [wantsPlay, setWantsPlay] = useState(autoplay && !reduced && timeline.length > 0);
  const [speed, setSpeed] = useState(1);

  const frame = useMemo(() => frameAt(timeline, moments, cursor), [timeline, moments, cursor]);
  const playing = wantsPlay && cursor < last;
  // A key moment reached on this step is captioned while the replay holds on it (EX-5.3)
  const caption = frame.newMoments.length ? frame.newMoments.map((m) => m.label).join(" → ") : null;

  useEffect(() => {
    if (!playing) return;
    const hold = caption ? MOMENT_HOLD_MS : 0;
    const t = setTimeout(() => setCursor((c) => c + 1), (STEP_MS + hold) / speed);
    return () => clearTimeout(t);
  }, [playing, cursor, speed, caption]);

  const play = useCallback(() => {
    setCursor((c) => (c >= last ? -1 : c));
    setWantsPlay(true);
  }, [last]);
  const pause = useCallback(() => setWantsPlay(false), []);
  const step = useCallback(
    (delta: number) => {
      setWantsPlay(false);
      setCursor((c) => Math.max(-1, Math.min(last, c + delta)));
    },
    [last],
  );
  const seek = useCallback(
    (i: number) => {
      setWantsPlay(false);
      setCursor(Math.max(-1, Math.min(last, i)));
    },
    [last],
  );

  return { cursor, frame, playing, speed, caption, play, pause, step, seek, setSpeed, replaying: cursor < last || playing };
}
