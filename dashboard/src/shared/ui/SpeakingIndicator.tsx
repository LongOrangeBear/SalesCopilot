/**
 * Индикатор говорящего (анимированные полоски).
 */
export function SpeakingIndicator({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="flex items-center gap-[2px] h-4">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="speaking-bar w-[3px] h-full bg-green-400 rounded-full origin-bottom"
        />
      ))}
    </div>
  );
}
