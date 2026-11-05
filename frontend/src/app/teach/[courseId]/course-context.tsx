"use client";

import { createContext, useContext } from "react";
import type { CourseDetail } from "@/lib/types";

export const CourseContext = createContext<{ course: CourseDetail; reload: () => Promise<void> } | null>(null);
export function useCourse() {
  const ctx = useContext(CourseContext);
  if (!ctx) throw new Error("useCourse outside course layout");
  return ctx;
}
