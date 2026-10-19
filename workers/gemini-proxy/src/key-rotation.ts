const MAX_ERROR_PREVIEW_BYTES = 64 * 1024;
const ALL_KEYS_EXHAUSTED = "The demo's API keys are all used up. Please try again later.";

export function apiKeys(multiple: string | undefined, legacy: string | undefined): string[] {
	const keys = (multiple ?? "").split(/[,\r\n]/).map((key) => key.trim()).filter(Boolean);
	return keys.length ? keys : [legacy?.trim() ?? ""].filter(Boolean);
}

export function keyStart(header: string | null, count: number): number {
	if (!header || !/^\d+$/.test(header)) return 0;
	const start = Number(header);
	return Number.isSafeInteger(start) && start < count ? start : 0;
}

export function isKeyFailure(status: number, body = ""): boolean {
	if ([401, 403, 429].includes(status)) return true;
	return status === 400 && /API[_ ]?KEY[_ ](?:INVALID|EXPIRED)|(?:invalid|expired) API[ _]key|API[ _]key (?:is )?(?:not valid|invalid|expired)/i.test(body);
}

export function error(status: number, reason: string, message: string, headers?: HeadersInit): Response {
	return Response.json({ error: { code: status, status: reason, message } }, { status, headers });
}

export function proxyLimit(message: string): Response {
	return error(429, "RESOURCE_EXHAUSTED", message, { "x-trpg-proxy-limit": "1" });
}

// Inspect only a bounded prefix of 400 errors, retaining the body for non-key errors.
async function errorPreview(response: Response): Promise<{ text: string; body: ReadableStream<Uint8Array> | null }> {
	if (!response.body) return { text: "", body: null };
	const reader = response.body.getReader();
	const chunks: Uint8Array[] = [];
	const decoder = new TextDecoder();
	let size = 0;
	let text = "";
	while (size < MAX_ERROR_PREVIEW_BYTES) {
		const { done, value } = await reader.read();
		if (done) break;
		chunks.push(value);
		text += decoder.decode(value.subarray(0, MAX_ERROR_PREVIEW_BYTES - size), { stream: true });
		size += value.byteLength;
	}
	text += decoder.decode();
	const body = new ReadableStream<Uint8Array>({
		start(controller) {
			for (const chunk of chunks) controller.enqueue(chunk);
		},
		async pull(controller) {
			const { done, value } = await reader.read();
			if (done) controller.close();
			else controller.enqueue(value);
		},
		cancel(reason) { return reader.cancel(reason); },
	});
	return { text, body };
}

function secretPattern(keys: string[]): { pattern: RegExp; tail: number } {
	const values = [...new Set(keys.filter(Boolean).flatMap((key) => [key, encodeURIComponent(key)]))]
		.sort((a, b) => b.length - a.length);
	const escaped = values.map((key) => key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
	return { pattern: new RegExp(escaped.join("|") || "(?!)", "g"), tail: Math.max(1, ...values.map((key) => key.length)) - 1 };
}

// Keep a small tail so even a key split across upstream chunks is redacted.
function redactBody(body: ReadableStream<Uint8Array> | null, keys: string[]): ReadableStream<Uint8Array> | null {
	if (!body) return null;
	const { pattern, tail } = secretPattern(keys);
	const decoder = new TextDecoder();
	const encoder = new TextEncoder();
	let pending = "";
	function emit(controller: TransformStreamDefaultController<Uint8Array>, flush = false): void {
		const cutoff = flush ? pending.length : Math.max(0, pending.length - tail);
		let cursor = 0;
		let output = "";
		for (const match of pending.matchAll(pattern)) {
			if (match.index >= cutoff) break;
			output += pending.slice(cursor, match.index) + "[REDACTED]";
			cursor = match.index + match[0].length;
		}
		const end = Math.max(cutoff, cursor);
		output += pending.slice(cursor, end);
		pending = pending.slice(end);
		if (output) controller.enqueue(encoder.encode(output));
	}
	const reader = body.pipeThrough(new TransformStream<Uint8Array, Uint8Array>({
		transform(chunk, controller) {
			pending += decoder.decode(chunk, { stream: true });
			emit(controller);
		},
		flush(controller) {
			pending += decoder.decode();
			emit(controller, true);
		},
	})).getReader();
	return new ReadableStream<Uint8Array>({
		async pull(controller) {
			try {
				const { done, value } = await reader.read();
				if (done) controller.close();
				else controller.enqueue(value);
			} catch {
				controller.error(new Error("Upstream response failed."));
			}
		},
		cancel() { return reader.cancel().catch(() => {}); },
	});
}

export async function forwardRequest(request: Request, env: Env, model: string,
	payload: Record<string, unknown>, kind: string): Promise<Response> {
	const day = new Date().toISOString().slice(0, 10);
	const budget = await env.BUDGET.getByName(`day-${day}`).consume(Number(env.DAILY_REQUEST_LIMIT));
	if (!budget.allowed) return proxyLimit("The demo's daily request budget is used up. Please try again tomorrow (UTC).");

	const keys = apiKeys(env.GEMINI_API_KEYS, env.GEMINI_API_KEY);
	const secrets = [...keys, env.GEMINI_API_KEY ?? "", env.DEMO_TOKEN];
	const { pattern } = secretPattern(secrets);
	const body = JSON.stringify(payload);
	let tries = 0;
	function finish(response: Response, slot: number): Response {
		response.headers.set("x-trpg-key-slot", String(slot));
		console.log(JSON.stringify({ event: "proxy", kind, model, status: response.status,
			used: budget.used, colo: request.cf?.colo, slot, tries }).replace(pattern, "[REDACTED]"));
		return response;
	}
	for (let slot = keyStart(request.headers.get("x-trpg-key-start"), keys.length); slot < keys.length; slot++) {
		tries++;
		try {
			const upstream = await fetch(`${env.UPSTREAM_BASE}/v1beta/models/${model}:generateContent`, {
				method: "POST",
				headers: { "content-type": "application/json", "x-goog-api-key": keys[slot] },
				body,
			});
			let responseBody = upstream.body;
			let preview = "";
			if (upstream.status === 400) {
				const inspected = await errorPreview(upstream);
				preview = inspected.text;
				responseBody = inspected.body;
			}
			if (isKeyFailure(upstream.status, preview)) {
				await responseBody?.cancel().catch(() => {});
				continue;
			}
			return finish(new Response(redactBody(responseBody, secrets), {
				status: upstream.status,
				headers: { "content-type": (upstream.headers.get("content-type") ?? "application/json").replace(pattern, "[REDACTED]") },
			}), slot);
		} catch {
			// Transport errors must not rotate keys or expose upstream exception text.
			return finish(error(502, "BAD_GATEWAY", "Upstream request failed."), slot);
		}
	}
	return finish(error(429, "RESOURCE_EXHAUSTED", ALL_KEYS_EXHAUSTED), keys.length);
}
