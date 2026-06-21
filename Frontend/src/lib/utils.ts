import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const INCOME_CATEGORIES = new Set([
  "income",
  "salary",
  "freelancing",
  "refund",
  "interest",
  "bonus",
  "other income"
]);

export function isIncome(category: string | undefined | null): boolean {
  if (!category) return false;
  return INCOME_CATEGORIES.has(category.trim().toLowerCase());
}

