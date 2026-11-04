/** Illustrative landing-page data only; never used as a successful API result. */
import type { Citation, ContentUnit, GraphNode, QuizQuestion } from "./api";
export interface ConceptNode {
  concept_id: string; name: string; topic: string; prerequisites: string[]; evidence_units: string[];
  mastery: number; masteryKnown?: boolean; status: "mastered" | "learning" | "weak" | "unvisited";
  evidenceCount?: number; description?: string; keyTakeaways?: string[];
  evidence_details?: GraphNode["evidence_details"];
}
export interface Question extends QuizQuestion {
  answer: string; explanation: string;
}
export interface AttachedFile {
  id: string; name: string; type: "pdf" | "video" | "image" | "file";
  extension?: string; previewUrl?: string; size?: string; previewHeading?: string; previewLines?: string[];
}
export interface ChatMessage {
  id: string; sender: "student" | "tutor"; text: string; timestamp: string;
  citations?: Citation[]; attachments?: AttachedFile[]; attachment?: AttachedFile; hindiTranslation?: string; isRefusal?: boolean;
}
export const MOCK_CONCEPTS: ConceptNode[] = [
  {concept_id: "derivatives", name: "Derivatives", topic: "Calculus", prerequisites: [], evidence_units: [], mastery: 0.7, status: "mastered"},
  {concept_id: "chain_rule", name: "Chain Rule", topic: "Calculus", prerequisites: ["derivatives"], evidence_units: [], mastery: 0.45, status: "weak"},
];
export const MOCK_QUESTIONS: Question[] = [{
  q_id: "preview_chain_rule", concept_id: "chain_rule", topic: "Chain Rule", source_location: {},
  difficulty: 2, type: "numeric", stem: "For y = 3(2x+1)^2, find dy/dx at x=1.",
  options: [], answer: "36", explanation: "dy/dx = 12(2x+1), so the derivative at x=1 is 36.",
  verified: false, verifier_agreement: 0,
}];
export const MOCK_CONTENT_UNITS: ContentUnit[] = [];
export const INITIAL_CHAT_MESSAGES: ChatMessage[] = [];
