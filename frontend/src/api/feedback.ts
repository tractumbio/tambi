const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000/api/v1";

export async function submitFeedback(text: string): Promise<{ id: number }> {
  const res = await fetch(`${API_BASE_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`Failed to submit: ${res.status}`);
  return res.json();
}
