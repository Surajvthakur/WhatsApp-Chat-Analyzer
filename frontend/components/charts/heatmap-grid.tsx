"use client";

import { cn } from "@/lib/utils";
import type { HeatmapResponse } from "@/lib/api";

const DAY_ORDER = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

interface HeatmapGridProps {
  data: HeatmapResponse;
}

export function HeatmapGrid({ data }: HeatmapGridProps) {
  const maxVal = Math.max(...data.values.flat(), 1);
  const orderedDays = DAY_ORDER.filter((d) => data.days.includes(d));
  const extraDays = data.days.filter((d) => !DAY_ORDER.includes(d));
  const rows = [...orderedDays, ...extraDays];

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[600px] border-collapse text-xs">
        <thead>
          <tr>
            <th className="p-2 text-left font-medium text-[var(--muted-foreground)]">
              Day
            </th>
            {data.periods.map((p) => (
              <th
                key={p}
                className="p-1 text-center font-medium text-[var(--muted-foreground)]"
              >
                {p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((day, rowIdx) => {
            const dayIndex = data.days.indexOf(day);
            if (dayIndex === -1) return null;
            return (
              <tr key={day}>
                <td className="p-2 font-medium">{day}</td>
                {data.values[dayIndex]?.map((val, colIdx) => {
                  const intensity = val / maxVal;
                  return (
                    <td key={colIdx} className="p-1">
                      <div
                        className={cn(
                          "flex h-8 min-w-[2rem] items-center justify-center rounded text-[10px] font-medium",
                          intensity > 0.6
                            ? "text-white"
                            : "text-[var(--foreground)]",
                        )}
                        style={{
                          backgroundColor: `rgba(37, 211, 102, ${0.15 + intensity * 0.85})`,
                        }}
                        title={`${val} messages`}
                      >
                        {val > 0 ? Math.round(val) : ""}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
