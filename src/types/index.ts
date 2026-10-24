export type Role = 'user' | 'assistant';

export type ThinkingLevel = 'low' | 'medium' | 'high';

export interface MediaAttachment {
  id: string;
  name: string;
  mediaType: 'image' | 'audio' | 'video';
  mimeType: string;
  dataUrl: string;
}

export interface SearchSource {
  title: string;
  href: string;
  body: string;
  favicon?: string;
  domain: string;
}

export interface ImageResult {
  url: string;
  thumbnail: string;
  title: string;
  source: string;
  width: number;
  height: number;
}

export interface UrlContext {
  url: string;
  title: string;
  content: string;
  page_type: string;
}

export interface LinkedInProfile {
  name: string;
  headline: string;
  location: string;
  company: string;
  profile_url: string;
  photo_url: string;
  snippet: string;
}

export interface MapRoute {
  origin: string;
  destination: string;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  thinking?: string;
  sources?: SearchSource[];
  images?: ImageResult[];
  linkedinProfile?: LinkedInProfile;
  mapRoute?: MapRoute;
  attachments?: MediaAttachment[];
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
  model: string;
}
