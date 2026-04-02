interface ScoreBadgeProps {
  score: number;
  riskLevel: string; // "Good" | "Moderate" | "Poor"
  size?: "sm" | "md" | "lg";
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-success";
  if (score >= 40) return "text-warning";
  return "text-danger";
}

function strokeColor(score: number): string {
  if (score >= 70) return "stroke-success";
  if (score >= 40) return "stroke-warning";
  return "stroke-danger";
}

function riskBg(level: string): string {
  switch (level.toLowerCase()) {
    case "good":
      return "bg-green-100 text-green-800";
    case "moderate":
      return "bg-yellow-100 text-yellow-800";
    case "poor":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

const sizes = {
  sm: { box: 64, r: 26, font: "text-base", label: "text-[10px]" },
  md: { box: 96, r: 38, font: "text-2xl", label: "text-xs" },
  lg: { box: 128, r: 52, font: "text-4xl", label: "text-sm" },
} as const;

export default function ScoreBadge({
  score,
  riskLevel,
  size = "md",
}: ScoreBadgeProps) {
  const s = sizes[size];
  const circumference = 2 * Math.PI * s.r;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        width={s.box}
        height={s.box}
        viewBox={`0 0 ${s.box} ${s.box}`}
        className="transform -rotate-90"
      >
        <circle
          cx={s.box / 2}
          cy={s.box / 2}
          r={s.r}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={size === "sm" ? 4 : 6}
        />
        <circle
          cx={s.box / 2}
          cy={s.box / 2}
          r={s.r}
          fill="none"
          className={strokeColor(score)}
          strokeWidth={size === "sm" ? 4 : 6}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 1.2s ease-out" }}
        />
        <text
          x={s.box / 2}
          y={s.box / 2}
          textAnchor="middle"
          dominantBaseline="central"
          className={`${s.font} font-bold ${scoreColor(score)} fill-current`}
          transform={`rotate(90, ${s.box / 2}, ${s.box / 2})`}
        >
          {score}
        </text>
      </svg>
      <span
        className={`${s.label} font-semibold px-2 py-0.5 rounded-full ${riskBg(riskLevel)}`}
      >
        {riskLevel}
      </span>
    </div>
  );
}
