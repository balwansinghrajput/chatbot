export type Role = 'user' | 'assistant';

export type ThinkingLevel = 'low' | 'medium' | 'high';

export interface SearchSource {
  title: string;
  href: string;
  body: string;
  favicon: string; // URL to the favicon image
  domain: string;  // e.g. "example.com"
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  thinking?: string;
  sources?: SearchSource[];
  timestamp: Date;
  isStreaming?: boolean;
}

export interface Chat {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export interface ChatSettings {
  thinkingLevel: ThinkingLevel;
  webSearch: boolean;
  model: string;
}
