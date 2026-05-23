/**
 * Text similarity algorithms for AI mapping suggestions.
 * 
 * This module implements Jaro-Winkler similarity for matching
 * Discord channels with social media targets based on text similarity.
 */

/**
 * Calculate Jaro similarity between two strings.
 * 
 * The Jaro similarity is a measure of similarity between two strings.
 * The higher the Jaro similarity for two strings is, the more similar
 * the strings are. The score is normalized such that 0 means no similarity
 * and 1 is an exact match.
 * 
 * @param s1 - First string to compare
 * @param s2 - Second string to compare
 * @returns Jaro similarity score between 0 and 1
 */
function jaroSimilarity(s1: string, s2: string): number {
  // Handle edge cases
  if (s1 === s2) return 1.0;
  if (s1.length === 0 || s2.length === 0) return 0.0;

  // Calculate match window
  const matchWindow = Math.floor(Math.max(s1.length, s2.length) / 2) - 1;
  if (matchWindow < 0) return 0.0;

  // Initialize arrays to track matches
  const s1Matches = new Array(s1.length).fill(false);
  const s2Matches = new Array(s2.length).fill(false);

  let matches = 0;
  let transpositions = 0;

  // Find matches
  for (let i = 0; i < s1.length; i++) {
    const start = Math.max(0, i - matchWindow);
    const end = Math.min(i + matchWindow + 1, s2.length);

    for (let j = start; j < end; j++) {
      if (s2Matches[j] || s1[i] !== s2[j]) continue;
      s1Matches[i] = true;
      s2Matches[j] = true;
      matches++;
      break;
    }
  }

  if (matches === 0) return 0.0;

  // Find transpositions
  let k = 0;
  for (let i = 0; i < s1.length; i++) {
    if (!s1Matches[i]) continue;
    while (!s2Matches[k]) k++;
    if (s1[i] !== s2[k]) transpositions++;
    k++;
  }

  // Calculate Jaro similarity
  return (
    (matches / s1.length +
      matches / s2.length +
      (matches - transpositions / 2) / matches) /
    3.0
  );
}

/**
 * Calculate Jaro-Winkler similarity between two strings.
 * 
 * The Jaro-Winkler similarity is a variant of the Jaro similarity metric
 * that gives more favorable ratings to strings with common prefixes.
 * 
 * @param s1 - First string to compare
 * @param s2 - Second string to compare
 * @param prefixScale - Scaling factor for common prefix (default: 0.1)
 * @returns Jaro-Winkler similarity score between 0 and 1
 * 
 * @example
 * ```typescript
 * const score = jaroWinklerSimilarity("gaming", "games");
 * console.log(score); // ~0.85
 * ```
 */
export function jaroWinklerSimilarity(
  s1: string,
  s2: string,
  prefixScale: number = 0.1
): number {
  const jaroScore = jaroSimilarity(s1, s2);

  // Find common prefix length (up to 4 characters)
  let prefixLength = 0;
  const maxPrefix = Math.min(4, Math.min(s1.length, s2.length));

  for (let i = 0; i < maxPrefix; i++) {
    if (s1[i] === s2[i]) {
      prefixLength++;
    } else {
      break;
    }
  }

  // Calculate Jaro-Winkler similarity
  return jaroScore + prefixLength * prefixScale * (1 - jaroScore);
}

/**
 * Normalize text for comparison by removing special characters and converting to lowercase.
 * 
 * @param text - Text to normalize
 * @returns Normalized text
 * 
 * @example
 * ```typescript
 * normalizeText("@Gaming_Channel!"); // "gaming channel"
 * ```
 */
export function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .replace(/[@#_\-]/g, ' ') // Replace special chars with space
    .replace(/\s+/g, ' ') // Collapse multiple spaces
    .trim();
}

/**
 * Calculate similarity score between a Discord channel and social target.
 * 
 * This function compares channel names, descriptions, and tags with the
 * target's display name and description to compute an overall similarity score.
 * 
 * @param channelName - Discord channel name
 * @param channelDescription - Discord channel description (optional)
 * @param channelTags - Discord channel content tags (optional)
 * @param targetName - Social media target display name
 * @param targetDescription - Social media target description (optional)
 * @returns Similarity score as a percentage (0-100)
 * 
 * @example
 * ```typescript
 * const score = calculateMappingScore(
 *   "gaming-videos",
 *   "Gaming content channel",
 *   ["gaming", "esports"],
 *   "@GamingPro",
 *   "Professional gaming content"
 * );
 * console.log(score); // ~75
 * ```
 */
export function calculateMappingScore(
  channelName: string,
  channelDescription: string | null,
  channelTags: string[] | null,
  targetName: string,
  targetDescription: string | null
): number {
  // Normalize inputs
  const normChannelName = normalizeText(channelName);
  const normTargetName = normalizeText(targetName);

  // Calculate name similarity (weighted 50%)
  const nameSimilarity = jaroWinklerSimilarity(normChannelName, normTargetName);
  let totalScore = nameSimilarity * 50;

  // Calculate description similarity (weighted 30%)
  if (channelDescription && targetDescription) {
    const normChannelDesc = normalizeText(channelDescription);
    const normTargetDesc = normalizeText(targetDescription);
    const descSimilarity = jaroWinklerSimilarity(normChannelDesc, normTargetDesc);
    totalScore += descSimilarity * 30;
  }

  // Calculate tag similarity (weighted 20%)
  if (channelTags && channelTags.length > 0) {
    const normTags = channelTags.map(normalizeText);
    const normTargetName = normalizeText(targetName);
    const normTargetDesc = targetDescription ? normalizeText(targetDescription) : '';

    // Check if any tag matches target name or description
    let maxTagSimilarity = 0;
    for (const tag of normTags) {
      const tagNameSim = jaroWinklerSimilarity(tag, normTargetName);
      const tagDescSim = normTargetDesc
        ? jaroWinklerSimilarity(tag, normTargetDesc)
        : 0;
      maxTagSimilarity = Math.max(maxTagSimilarity, tagNameSim, tagDescSim);
    }
    totalScore += maxTagSimilarity * 20;
  }

  // Return score as percentage (0-100)
  return Math.round(totalScore);
}

/**
 * Find best matching Discord channels for a social target.
 * 
 * @param channels - Array of Discord channels
 * @param targetName - Social media target display name
 * @param targetDescription - Social media target description (optional)
 * @param minScore - Minimum score threshold (default: 60)
 * @returns Array of channel IDs with scores above threshold, sorted by score
 * 
 * @example
 * ```typescript
 * const matches = findBestMatches(
 *   channels,
 *   "@GamingPro",
 *   "Gaming content creator",
 *   60
 * );
 * // Returns: [{ channelId: "123", score: 85 }, { channelId: "456", score: 72 }]
 * ```
 */
export function findBestMatches(
  channels: Array<{
    id: string;
    channel_name: string;
    description: string | null;
    content_tags: string[] | null;
  }>,
  targetName: string,
  targetDescription: string | null,
  minScore: number = 60
): Array<{ channelId: string; score: number }> {
  const matches: Array<{ channelId: string; score: number }> = [];

  for (const channel of channels) {
    const score = calculateMappingScore(
      channel.channel_name,
      channel.description,
      channel.content_tags,
      targetName,
      targetDescription
    );

    if (score >= minScore) {
      matches.push({ channelId: channel.id, score });
    }
  }

  // Sort by score descending
  return matches.sort((a, b) => b.score - a.score);
}
