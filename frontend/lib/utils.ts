import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(value: number | undefined | null, digits = 0) {
  if (value === undefined || value === null) {
    return "--";
  }
  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}
