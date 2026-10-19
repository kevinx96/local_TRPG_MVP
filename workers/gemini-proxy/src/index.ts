// Keeps the Gemini key off players' machines: the game sends its requests here with a demo token,
// and only this game's request shape and prompts are forwarded, within per-IP and per-day limits.
import { DurableObject } from "cloudflare:workers";
import { FINGERPRINTS } from "./fingerprints";
import { error, forwardRequest, proxyLimit } from "./key-rotation";

const ALLOWED_MODELS = new Set(["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.6-flash"]);
const ALLOWED_FIELDS = new Set(["contents", "systemInstruction", "generationConfig", "safetySettings"]);
const PATH = /^\/v1beta\/models\/([a-z0-9.-]+):generateContent$/;
const MAX_BODY_BYTES = 64 * 1024;
const MAX_OUTPUT_TOKENS = 2048;

/** Counts requests for one UTC day; one instance per day keeps the counter exact. */
export class DailyBudget extends DurableObject<Env> {
	constructor(ctx: DurableObjectState, env: Env) {
		super(ctx, env);
		ctx.blockConcurrencyWhile(async () => {
			this.ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS usage (k TEXT PRIMARY KEY, n INTEGER NOT NULL)");
		});
	}

	async consume(limit: number): Promise<{ allowed: boolean; used: number }> {
		const row = this.ctx.storage.sql
			.exec<{ n: number }>("INSERT INTO usage (k, n) VALUES ('requests', 1) ON CONFLICT(k) DO UPDATE SET n = n + 1 RETURNING n")
			.one();
		return { allowed: row.n <= limit, used: row.n };
	}
}

async function tokenMatches(given: string, expected: string): Promise<boolean> {
	const encoder = new TextEncoder();
	const [a, b] = await Promise.all([
		crypto.subtle.digest("SHA-256", encoder.encode(given)),
		crypto.subtle.digest("SHA-256", encoder.encode(expected)),
	]);
	return crypto.subtle.timingSafeEqual(a, b);
}

function sanitize(body: unknown): Record<string, unknown> | null {
	if (typeof body !== "object" || body === null || Array.isArray(body)) return null;
	const payload: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(body)) {
		if (!ALLOWED_FIELDS.has(key)) return null;
		payload[key] = value;
	}
	const config = (typeof payload.generationConfig === "object" && payload.generationConfig !== null
		? payload.generationConfig
		: {}) as Record<string, unknown>;
	const requested = Number(config.maxOutputTokens ?? MAX_OUTPUT_TOKENS);
	payload.generationConfig = { ...config, maxOutputTokens: Math.min(Number.isFinite(requested) ? requested : MAX_OUTPUT_TOKENS, MAX_OUTPUT_TOKENS) };
	return payload;
}

/** Which of the game's prompts this request carries, or null when it is not one of ours. */
function promptKind(payload: Record<string, unknown>): string | null {
	const instruction = payload.systemInstruction as { parts?: Array<{ text?: unknown }> } | undefined;
	const first = instruction?.parts?.[0]?.text;
	if (typeof first !== "string") return null;
	const kind = Object.keys(FINGERPRINTS).find((name) => first.startsWith(FINGERPRINTS[name]));
	if (!kind) return null;
	const config = payload.generationConfig as Record<string, unknown>;
	if (kind === "plan" && (typeof config.responseJsonSchema !== "object" || config.responseJsonSchema === null)) return null;
	return kind;
}

export default {
	async fetch(request, env, ctx): Promise<Response> {
		const url = new URL(request.url);
		if (request.method !== "POST") return error(405, "METHOD_NOT_ALLOWED", "Only POST is supported.");
		const match = PATH.exec(url.pathname);
		if (!match) return error(404, "NOT_FOUND", "Unknown endpoint.");
		const model = match[1];
		if (!ALLOWED_MODELS.has(model)) return error(403, "PERMISSION_DENIED", `Model ${model} is not available on this endpoint.`);

		if (!(await tokenMatches(request.headers.get("x-goog-api-key") ?? "", env.DEMO_TOKEN))) {
			return error(401, "UNAUTHENTICATED", "Invalid demo token.");
		}

		const ip = request.headers.get("CF-Connecting-IP") ?? "unknown";
		const { success } = await env.PER_IP_LIMITER.limit({ key: ip });
		if (!success) return proxyLimit("Too many requests from this address. Please wait a minute.");

		const declared = Number(request.headers.get("content-length") ?? "0");
		if (declared > MAX_BODY_BYTES) return error(413, "INVALID_ARGUMENT", "Request body is too large.");
		const raw = await request.arrayBuffer();
		if (raw.byteLength > MAX_BODY_BYTES) return error(413, "INVALID_ARGUMENT", "Request body is too large.");
		let parsed: unknown;
		try {
			parsed = JSON.parse(new TextDecoder().decode(raw));
		} catch {
			return error(400, "INVALID_ARGUMENT", "Body must be JSON.");
		}
		const payload = sanitize(parsed);
		if (!payload) return error(400, "INVALID_ARGUMENT", "Unsupported request fields.");
		const kind = promptKind(payload);
		if (!kind) return error(403, "PERMISSION_DENIED", "This endpoint only serves the game client.");

		return forwardRequest(request, env, model, payload, kind);
	},
} satisfies ExportedHandler<Env>;
