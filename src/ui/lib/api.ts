/** Browser contracts for the unified FastAPI service (src/api/service.py). */
export interface Location {
  page?: number | null;
  slide?: number | null;
  timestamp?: string | null;
  seconds?: number | null;
  t_start?: number | null;
}
export interface ContentUnit {
  unit_id: string;
  source_id: string;
  source_type: string;
  location: Location;
  text: string;
  image_caption?: string | null;
  topic_ids?: string[];
}
export interface Citation {
  unit_id: string;
  source: string;
  label: string;
  open_url: string;
  location: Location;
  excerpt: string;
  diagram_caption?: string | null;
}
export interface ChatResponse {
  text: string;
  status: "grounded" | "partial" | "refused";
  confidence: number | null;
  citations: Citation[];
  claims: { text: string; supported: boolean; citations?: Citation[] }[];
  outside_knowledge: string[];
}
export interface ChatSession {
  id: string; student_id: string; title: string;
  created_at: string; updated_at: string; message_count: number;
}
export interface SessionMessage {
  id: string; role: "user" | "assistant"; content: string;
  citations: Citation[]; created_at: string;
}
export interface CompletedQuiz {
  id: string; student_id: string; topic: string; score: number; total: number; completed_at: string;
}
export interface GraphNode {
  id: string; name: string; topic: string; prerequisites: string[];
  evidence_count: number; evidence_units: string[];
  evidence_details?: Pick<ContentUnit, "unit_id" | "source_id" | "location" | "text">[];
  description: string; keyTakeaways: string[];
}
export interface QuizQuestion {
  q_id: string; concept_id: string; topic: string; source_location: Location;
  difficulty: number; type: "mcq" | "numeric" | "short"; stem: string; options?: string[] | null;
  verified: boolean; verifier_agreement: number; sympy_verified?: boolean;
}
export interface AnswerResult {
  correct: boolean; correct_answer: string; explanation: string; concept_id: string;
  new_mastery: number; next_concept: string | null; next_difficulty: number;
}
export interface UploadedMaterial {
  filename: string; size_bytes: number; file_type: string; modified_at: string;
  download_url: string; units_count: number;
  linked_concepts: { concept_id: string; name: string; topic: string }[];
  sample_units: Pick<ContentUnit, "unit_id" | "location" | "text" | "image_caption">[];
}
export interface UploadResult {
  status: string; files_processed: number; units_created: number; sample_units: ContentUnit[];
}
export interface AblationResult {
  evaluation_kind?: string; sessions: number[];
  learning_curves: { session: string; random: number; adaptive: number }[];
  final_random: string; final_adaptive: string; net_gain_percentage: string;
  p_value: string | number | null; sample_size: string;
}
export interface RagasResult {
  status: string;
  metrics: Record<string, number> | null;
  reason?: string;
}

export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
}

export function getMaterialUrl(path: string): string {
  return new URL(path, `${getApiBaseUrl()}/`).href;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, init);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch { /* Preserve the HTTP error when a proxy returns HTML. */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
const json = (body: unknown): RequestInit => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});
const id = encodeURIComponent;
export const listSessions = (student: string) => request<ChatSession[]>(`/sessions?student_id=${id(student)}`);
export const createSession = (student: string, title?: string) => request<ChatSession>("/sessions", json({ student_id: student, title }));
export const getSession = (session: string) => request<{session: ChatSession; messages: SessionMessage[]}>(`/sessions/${id(session)}`);
export const deleteSession = (session: string) => request(`/sessions/${id(session)}`, { method: "DELETE" });
export const sendSessionMessage = (session: string, question: string, outside: boolean, student: string) =>
  request<ChatResponse>(`/sessions/${id(session)}/chat`, json({ question, allow_outside_knowledge: outside, student_id: student }));
export const fetchCompletedQuizzes = (student: string) => request<CompletedQuiz[]>(`/completed-quizzes?student_id=${id(student)}`);
export const fetchKnowledgeGraph = () => request<{nodes: GraphNode[]; edges: {source: string; target: string}[]}>("/graph");
export const fetchStudentMastery = (student: string) => request<{board: {concept_id: string; mastery: number}[]}>(`/mastery/${id(student)}`);
export const fetchAdaptiveQuiz = (student: string, size: number, difficulty?: number, concept?: string) =>
  request<{questions: QuizQuestion[]}>("/quiz", json({student_id: student, size, difficulty, concept_id: concept}));
export const submitStudentAnswer = (student: string, question: string, answer: string) =>
  request<AnswerResult>("/answer", json({student_id: student, q_id: question, answer}));
export const triggerDiagnostic = (student: string) =>
  request<{masteries: Record<string, number>; questions: QuizQuestion[]; status: string}>(`/diagnostic?student_id=${id(student)}`, {method: "POST"});
export const fetchUploadedMaterials = async () => (await request<{materials: UploadedMaterial[]}>("/ingest/materials")).materials;
export async function uploadCourseFiles(files: File[]): Promise<UploadResult> {
  const body = new FormData();
  files.forEach(file => body.append("files", file));
  const result = await request<UploadResult>("/ingest/upload", {method: "POST", body});
  if (result.status !== "success" || result.units_created <= 0) {
    throw new Error("No searchable content was extracted. Check the files and try again.");
  }
  return result;
}
export const fetchAblationBenchmarks = () => request<AblationResult>("/eval/ablation");
export const fetchRagasMetrics = () => request<RagasResult>("/eval/ragas");
