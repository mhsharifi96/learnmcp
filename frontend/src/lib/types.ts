export type User = { username: string; display_name: string; is_superuser: boolean };
export type Lesson = { id: number; order: number; title: string; brief: string; objectives: string; content: string; teaching_notes: string };
export type QuizSummary = {
  id: number;
  title: string;
  lesson_id: number | null;
  lesson: string | null;
  mode: "manual" | "ai";
  prompt: string;
  ai_question_count: number;
  question_count: number;
};
export type Question = {
  id: number;
  order: number;
  type: "mcq" | "short";
  prompt: string;
  options: string[];
  correct_answer: string;
  accepted_answers: string[];
  explanation: string;
  concept: string;
};
export type QuizDetail = QuizSummary & { course_id: number; questions: Question[]; lessons: { id: number; title: string }[] };
export type CourseSummary = {
  id: number;
  title: string;
  description: string;
  join_code: string;
  instructor: string;
  students: number | null;
  lessons: number | null;
};
export type CourseDetail = Omit<CourseSummary, "lessons"> & { lessons: Lesson[]; quizzes: QuizSummary[]; student_count: number };
export type Problem = {
  id: number;
  enrollment_id: number;
  student: string;
  category: string;
  severity: "low" | "medium" | "high" | string;
  concept: string;
  note: string;
  lesson: string | null;
  quiz: string | null;
  attempt_id: number | null;
  created_at: string;
  resolved_at: string | null;
  instructor_note: string;
};
