export function parkAward(count) {
  if (count >= 20) return "🏆";
  if (count >= 15) return "💎";
  if (count >= 10) return "🌟";
  if (count >= 5) return "⭐";
  if (count >= 4) return "🍀";
  if (count >= 3) return "📐";
  if (count >= 2) return "✌️";
  if (count >= 1) return "✅";
  return "";
}
