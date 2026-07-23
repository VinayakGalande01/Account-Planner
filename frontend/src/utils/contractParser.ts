/**
 * STREAMING CONTRACT PARSER (src/utils/contractParser.ts)
 * Normalizes backend section tags (__SECTION_EXECUTIVE_SUMMARY__, __SECTION_TABLE__)
 * and converts raw LLM text streams into structured ResponseContract UI models.
 */

// --- SECTION 1: Dependencies & Empty Contract Factory ---
// Imports ResponseContract interface schemas and defines factory for empty contract states.
import type { ResponseContract, SectionName, ConfidenceData, TableData, RecommendedAction } from '../types/responseContract';

export function createEmptyContract(rawContent: string = ''): ResponseContract {
  return {
    queryType: '',
    headline: '',
    summary: '',
    tableData: null,
    tableMarkdown: null,
    signals: [],
    actions: [],
    crmWarnings: [],
    confidence: null,
    recommendedActions: [],
    rawContent,
    breakdown: null,
    isStructured: false,
    formattedJson: undefined,
  };
}

// --- SECTION 2: Section Tag Parsing & JSON Normalization ---
// Strips delimiter tags and parses embedded JSON/Markdown payloads into normalized UI objects.

/**
 * Parses a completed response string into a normalized ResponseContract.
 *
 * This is the canonical normalizer called AFTER stream completion.
 * The __SECTION_*__ tags are treated strictly as transport format —
 * this function strips them and produces clean application state.
 */
export function parseResponseContract(content: string): ResponseContract {
  const contract = createEmptyContract(content);

  // Filter out sys_meta_log lines to prevent payload corruption
  const cleanContent = content
    .split('\n')
    .filter((line) => !line.startsWith('sys_meta_log|'))
    .join('\n');

  if (!cleanContent.includes('__SECTION_')) {
    try {
      const parsed = JSON.parse(cleanContent);
      if (parsed.type === 'conversational' || parsed.type === 'clarification') {
        contract.isStructured = true;
        contract.type = parsed.type;
        contract.conversationalData = parsed;
        return contract;
      }
    } catch (e) {
      // not JSON, fallback to standard raw text
    }
    return contract;
  }

  contract.isStructured = true;

  // Split by section headers — regex captures group names between underscores
  // Result: [prefix, sectionName, sectionContent, sectionName, sectionContent, ...]
  const parts = cleanContent.split(/__SECTION_(\w+)__/);

  for (let i = 1; i < parts.length; i += 2) {
    const sectionName = parts[i] as SectionName;
    const sectionContent = (parts[i + 1] || '').trim();

    switch (sectionName) {
      case 'INTENT':
        contract.queryType = sectionContent;
        break;

      case 'HEADLINE':
        contract.headline = sectionContent;
        break;

      case 'DIRECT_ANSWER':
        contract.directAnswer = sectionContent;
        break;

      case 'EXECUTIVE_SUMMARY':
        contract.executiveSummary = sectionContent;
        break;

      case 'SUMMARY':
        contract.summary = sectionContent;
        break;

      case 'TABLE_DATA':
        try {
          contract.tableData = JSON.parse(sectionContent) as TableData;
        } catch {
          // If JSON parsing fails, treat as markdown fallback
          contract.tableMarkdown = sectionContent;
        }
        break;

      case 'TABLE':
        // Only use markdown table if structured data wasn't already parsed
        if (!contract.tableData) {
          contract.tableMarkdown = sectionContent;
        }
        break;

      case 'SIGNALS':
        contract.signals = parseBulletList(sectionContent);
        break;

      case 'WHY_THIS_MATTERS':
        contract.whyThisMatters = sectionContent;
        break;

      case 'ACTIONS':
        contract.actions = parseBulletList(sectionContent);
        break;

      case 'CRM_HYGIENE':
        contract.crmWarnings = sectionContent
          .split('\n')
          .filter((l) => l.trim())
          .map((l) => l.replace(/^[⚠️\s]+/, '').trim())
          .filter(Boolean);
        break;

      case 'CONFIDENCE':
        try {
          contract.confidence = JSON.parse(sectionContent) as ConfidenceData;
        } catch {
          contract.confidence = {
            score: sectionContent,
            status: sectionContent,
            sources: [],
          };
        }
        break;

      case 'RECOMMENDED_ACTIONS':
        try {
          contract.recommendedActions = JSON.parse(sectionContent) as RecommendedAction[];
        } catch {
          // If JSON parsing fails, ignore silently
          contract.recommendedActions = [];
        }
        break;

      case 'BREAKDOWN':
        try {
          contract.breakdown = JSON.parse(sectionContent);
        } catch {
          contract.breakdown = null;
        }
        break;

      case 'FORMATTED_JSON':
        try {
          contract.formattedJson = JSON.parse(sectionContent);
        } catch {
          contract.formattedJson = undefined;
        }
        break;

      case 'END':
        break;

      default:
        break;
    }
  }

  return contract;
}

// ── Progressive Streaming Parser ────────────────────────────

export interface StreamParseResult {
  /** Sections that have been fully received (next header has arrived) */
  completedSections: Map<SectionName, string>;
  /** The section currently being streamed (last in buffer, no closing header yet) */
  activeSection: SectionName | null;
  /** Partially received content for the active section */
  activeSectionContent: string;
  /** Whether the content contains structured __SECTION_*__ tags */
  hasStructuredContent: boolean;
  /** Extracted system meta log lines */
  metaLogs: string[];
}

/**
 * Progressive streaming parser. Distinguishes between completed and
 * actively-streaming sections for progressive widget hydration.
 *
 * Streaming Choreography:
 * 1. Meta logs appear first (before any __SECTION_*)
 * 2. Completed sections render through their registered widgets
 * 3. Active section renders with a streaming cursor
 * 4. Table shows skeleton until headline+summary are complete, then atomically hydrates
 */
export function parseStreamingSections(content: string): StreamParseResult {
  const metaLogs: string[] = [];

  // Extract meta logs (always before section tags)
  const lines = content.split('\n');
  for (const line of lines) {
    if (line.startsWith('sys_meta_log|')) {
      metaLogs.push(line.replace('sys_meta_log|', ''));
    }
  }

  // Filter out sys_meta_log lines to prevent payload corruption
  const cleanContent = content
    .split('\n')
    .filter((line) => !line.startsWith('sys_meta_log|'))
    .join('\n');

  if (!cleanContent.includes('__SECTION_')) {
    return {
      completedSections: new Map(),
      activeSection: null,
      activeSectionContent: '',
      hasStructuredContent: false,
      metaLogs,
    };
  }

  const parts = cleanContent.split(/__SECTION_(\w+)__/);
  const completedSections = new Map<SectionName, string>();
  let activeSection: SectionName | null = null;
  let activeSectionContent = '';

  for (let i = 1; i < parts.length; i += 2) {
    const sectionName = parts[i] as SectionName;
    const sectionContent = parts[i + 1] || '';

    // If there's a next section header after this one, this section is complete
    if (i + 2 < parts.length) {
      completedSections.set(sectionName, sectionContent.trim());
    } else {
      // Last section in buffer — might still be streaming
      if (sectionName === 'END') {
        completedSections.set(sectionName, '');
      } else {
        activeSection = sectionName;
        activeSectionContent = sectionContent;
      }
    }
  }

  return {
    completedSections,
    activeSection,
    activeSectionContent,
    hasStructuredContent: true,
    metaLogs,
  };
}

// ── Helpers ─────────────────────────────────────────────────

/**
 * Parses bullet-pointed text into a clean string array.
 * Handles: •, -, *, numbered (1., 2.) prefixes.
 */
function parseBulletList(text: string): string[] {
  return text
    .split('\n')
    .filter((l) => l.trim())
    .map((l) => l.replace(/^[•\-*\d.)+\s]+/, '').trim())
    .filter(Boolean);
}
