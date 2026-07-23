/**
 * TELEMETRY STAGE LABEL MAPPER (src/utils/stageLabels.ts)
 * Translates raw backend pipeline progress logs and telemetry pings into
 * human-readable status labels displayed during AI stream generation.
 */

// --- SECTION 1: Telemetry Stage Label Dictionary ---
// Defines mapping of backend pipeline stage strings to polished UI status strings.
const stageLabelMap: Record<string, string> = {
  'Initializing Account Planning Agent...': 'Initializing Account Planning Agent...',
  'Resuming session checkpoint...': 'Resuming session checkpoint...',
  'Processing query for role: AM': 'Processing query (Account Manager perspective)...',
  'Processing query for role: VP': 'Processing query (VP Sales perspective)...',
  'Processing query for role: EXEC': 'Processing query (Executive perspective)...',
  'Layer 1: Intent classified': 'Classifying search intent...',
  'Layer 2: Data retrieved + Reasoning running...': 'Retrieving CRM accounts evidence...',
  'Stage 1/6: Decision Framing Complete': 'Framing strategic decision options...',
  'Stage 2/6: Strategic Narrative Built': 'Building narrative structures...',
  'Stage 3/6: CRM Evidence Selected': 'Selecting relevant CRM activity evidence...',
  'Stage 4/6: Intelligence Brief Compiled': 'Compiling intelligence brief...',
  'Stage 5/6: Reasoning Plan Generated': 'Generating multi-perspective reasoning plan...',
  'Stage 6/6: Expert Crucible Formed': 'Synthesizing final executive crucible recommendations...',
  'Layer 3: Generating response...': 'Formatting final recommendations contract...',
}

/**
 * Normalizes raw backend status lines into clean, user-facing telemetry strings.
 */
export function getFriendlyStageLabel(rawStatus: string): string {
  // Strip common prefix logging wrappers
  let cleaned = rawStatus
    .replace(/^sys_meta_log\|/, '')
    .replace(/^\[SYS_LOG\]\s*/, '')
    .replace(/^⚙️\s*/, '')
    .replace(/\s*✓$/, '')
    .trim()

  // Find exact map match
  if (stageLabelMap[cleaned]) {
    return stageLabelMap[cleaned]
  }

  // Regex fallback: Strip "Stage X/6:" or "Layer X:" and strip trailing checkmarks
  const stageRegex = /^Stage \d\/\d:\s*(.*)/
  const layerRegex = /^Layer \d:\s*(.*)/

  if (stageRegex.test(cleaned)) {
    cleaned = cleaned.replace(stageRegex, '$1')
  } else if (layerRegex.test(cleaned)) {
    cleaned = cleaned.replace(layerRegex, '$1')
  }

  // Final sanitization: title case fallback
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
}

/**
 * Fallback rotating reassurance phrases when the model is thinking in a long stage.
 */
export const idleReassurancePhrases = [
  'Still analyzing, building narrative context...',
  'Synthesizing account perspectives...',
  'This one is detailed, crafting intelligence briefs...',
  'Almost ready, executing final crucible synthesis...',
  'Evaluating CRM history data...',
]
