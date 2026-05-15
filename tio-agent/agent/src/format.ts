export function formatAgentAnswer(answer: string): string {
  try {
    const parsed = JSON.parse(answer);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return answer;
    return JSON.stringify(parsed, null, 2);
  } catch {
    return answer;
  }
}
