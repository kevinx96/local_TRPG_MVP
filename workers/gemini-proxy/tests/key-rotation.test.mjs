import assert from "node:assert/strict";
import { test } from "node:test";
import { apiKeys, error, forwardRequest, isKeyFailure, keyStart, proxyLimit } from "../src/key-rotation.ts";

const KEYS = ["fake-first-key-044", "fake-second-key-044", "fake-third-key-044"];
const PAYLOAD = { contents: [{ role: "user", parts: [{ text: "少し考えよう。" }] }] };
const SUCCESS = JSON.stringify({ candidates: [{ content: { parts: [{ text: "少し考えよう。" }] } }] });

function fixture(t, replies, { start, allowed = true, keys = KEYS } = {}) {
	const consume = t.mock.fn(async () => ({ allowed, used: 7 }));
	const env = {
		GEMINI_API_KEYS: keys.join(","), GEMINI_API_KEY: "fake-legacy-key-044", DEMO_TOKEN: "fake-demo-token-044",
		UPSTREAM_BASE: "https://fixture.invalid", DAILY_REQUEST_LIMIT: "2000",
		BUDGET: { getByName: t.mock.fn(() => ({ consume })) },
	};
	const fetch = t.mock.method(globalThis, "fetch", async () => {
		assert.ok(replies.length, "unexpected upstream request");
		const reply = replies.shift();
		if (reply instanceof Error) throw reply;
		return reply;
	});
	const log = t.mock.method(console, "log", () => {});
	const request = new Request("https://worker.invalid/v1beta/models/gemini-3.1-flash-lite:generateContent", {
		method: "POST", headers: start === undefined ? {} : { "x-trpg-key-start": String(start) },
	});
	return { env, consume, fetch, log,
		run: () => forwardRequest(request, env, "gemini-3.1-flash-lite", PAYLOAD, "plan"),
		keysUsed: () => fetch.mock.calls.map((call) => call.arguments[1].headers["x-goog-api-key"]),
	};
}

test("key lists accept commas, CRLF and whitespace, with legacy fallback", () => {
	assert.deepEqual(apiKeys(` ${KEYS[0]}, \r\n ${KEYS[1]}\n${KEYS[2]},`, "ignored"), KEYS);
	for (const value of [undefined, "", " , \n"]) assert.deepEqual(apiKeys(value, " legacy "), ["legacy"]);
	assert.deepEqual(apiKeys(undefined, undefined), []);
});

test("start is a nonnegative integer in range; invalid and exhausted starts reset to zero", () => {
	assert.equal(keyStart("2", 3), 2);
	for (const start of [null, "", "-1", "1.5", "1x", "1e0", "0x1", "3", "99", "9007199254740992"]) {
		assert.equal(keyStart(start, 3), 0, String(start));
	}
});

test("only quota, authentication and invalid-key 400 errors rotate", () => {
	for (const status of [401, 403, 429]) assert.equal(isKeyFailure(status), true);
	for (const body of ["API_KEY_INVALID", "API_KEY_EXPIRED", "API key not valid. Please pass a valid API key.", "invalid API key"]) {
		assert.equal(isKeyFailure(400, body), true);
	}
	for (const status of [200, 404, 500, 503]) assert.equal(isKeyFailure(status, "API_KEY_INVALID"), false);
	assert.equal(isKeyFailure(400, "Invalid schema"), false);
});

test("429 switches to the next key, resends the same body and consumes budget once", async (t) => {
	const f = fixture(t, [error(429, "RESOURCE_EXHAUSTED", KEYS[0]), new Response(SUCCESS)]);
	const response = await f.run();
	assert.equal(response.status, 200);
	assert.equal(response.headers.get("x-trpg-key-slot"), "1");
	assert.equal(await response.text(), SUCCESS);
	assert.deepEqual(f.keysUsed(), KEYS.slice(0, 2));
	assert.deepEqual(f.fetch.mock.calls.map((call) => call.arguments[1].body), [JSON.stringify(PAYLOAD), JSON.stringify(PAYLOAD)]);
	assert.equal(f.consume.mock.callCount(), 1);
	assert.deepEqual(f.consume.mock.calls[0].arguments, [2000]);
	assert.match(f.env.BUDGET.getByName.mock.calls[0].arguments[0], /^day-\d{4}-\d{2}-\d{2}$/);
	assert.equal(f.log.mock.callCount(), 1);
	assert.deepEqual(JSON.parse(f.log.mock.calls[0].arguments[0]), {
		event: "proxy", kind: "plan", model: "gemini-3.1-flash-lite", status: 200, used: 7, slot: 1, tries: 2,
	});
});

test("request start skips previous slots and never wraps", async (t) => {
	const f = fixture(t, [error(401, "UNAUTHENTICATED", "invalid"), new Response(SUCCESS)], { start: 1 });
	const response = await f.run();
	assert.equal(response.headers.get("x-trpg-key-slot"), "2");
	assert.equal(await response.text(), SUCCESS);
	assert.deepEqual(f.keysUsed(), KEYS.slice(1));
});

test("all remaining keys fail with a safe exhaustion response and count sentinel", async (t) => {
	const f = fixture(t, [error(403, "PERMISSION_DENIED", KEYS[1]), error(400, "INVALID_ARGUMENT", `API_KEY_INVALID ${KEYS[2]}`)], { start: 1 });
	const response = await f.run();
	assert.equal(response.status, 429);
	assert.equal(response.headers.get("x-trpg-key-slot"), "3");
	assert.equal(response.headers.get("x-trpg-proxy-limit"), null);
	assert.deepEqual(await response.json(), { error: { code: 429, status: "RESOURCE_EXHAUSTED",
		message: "The demo's API keys are all used up. Please try again later." } });
	assert.deepEqual(f.keysUsed(), KEYS.slice(1));
	assert.equal(f.consume.mock.callCount(), 1);
	const log = JSON.parse(f.log.mock.calls[0].arguments[0]);
	assert.equal(log.slot, 3);
	assert.equal(log.tries, 2);
	for (const key of KEYS) assert.ok(!JSON.stringify(log).includes(key));
});

for (const status of [400, 404, 500, 503]) {
	test(`${status} unrelated to keys passes through without rotation`, async (t) => {
		const body = JSON.stringify({ error: { message: "Invalid schema or unavailable model" } });
		const f = fixture(t, [new Response(body, { status, headers: { "content-type": "application/json" } })], { start: 1 });
		const response = await f.run();
		assert.equal(response.status, status);
		assert.equal(response.headers.get("x-trpg-key-slot"), "1");
		assert.equal(await response.text(), body);
		assert.deepEqual(f.keysUsed(), [KEYS[1]]);
	});
}

test("legacy secret works as one slot", async (t) => {
	const f = fixture(t, [new Response(SUCCESS)]);
	delete f.env.GEMINI_API_KEYS;
	const response = await f.run();
	assert.equal(response.headers.get("x-trpg-key-slot"), "0");
	assert.equal(await response.text(), SUCCESS);
	assert.deepEqual(f.keysUsed(), [f.env.GEMINI_API_KEY]);
});

test("daily and per-IP limits carry the proxy marker without spending any key", async (t) => {
	const f = fixture(t, [], { allowed: false });
	for (const response of [await f.run(), proxyLimit("Too many requests from this address. Please wait a minute.")]) {
		assert.equal(response.status, 429);
		assert.equal(response.headers.get("x-trpg-proxy-limit"), "1");
		assert.equal(response.headers.get("x-trpg-key-slot"), null);
	}
	assert.equal(f.fetch.mock.callCount(), 0);
	assert.equal(f.consume.mock.callCount(), 1);
});

test("response body, headers and logs redact keys, including cross-chunk matches", async (t) => {
	const content = `少し考えよう。 ${KEYS.join(" ")} fake-legacy-key-044 fake-demo-token-044`;
	const bytes = new TextEncoder().encode(content);
	const body = new ReadableStream({ start(controller) {
		for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
		controller.close();
	} });
	const f = fixture(t, [new Response(body, { headers: { "content-type": `text/plain; key=${KEYS[0]}` } })]);
	const response = await f.run();
	const text = await response.text();
	assert.equal(text, "少し考えよう。 [REDACTED] [REDACTED] [REDACTED] [REDACTED] [REDACTED]");
	const output = text + JSON.stringify([...response.headers]) + JSON.stringify(f.log.mock.calls);
	for (const key of [...KEYS, f.env.GEMINI_API_KEY, f.env.DEMO_TOKEN]) assert.ok(!output.includes(key));
});

test("transport errors never log or return the upstream exception or rotate keys", async (t) => {
	const f = fixture(t, [new Error(KEYS.join(" "))], { start: 1 });
	const response = await f.run();
	assert.equal(response.status, 502);
	assert.equal(response.headers.get("x-trpg-key-slot"), "1");
	assert.deepEqual(f.keysUsed(), [KEYS[1]]);
	const output = await response.text() + JSON.stringify(f.log.mock.calls);
	for (const key of KEYS) assert.ok(!output.includes(key));
});

test("large non-key 400 bodies are preserved after bounded inspection", async (t) => {
	const body = "x".repeat(128 * 1024);
	const f = fixture(t, [new Response(body, { status: 400 })]);
	const response = await f.run();
	assert.equal(response.status, 400);
	assert.equal(await response.text(), body);
	assert.equal(f.fetch.mock.callCount(), 1);
});

test("failed response cleanup cannot stop key rotation", async (t) => {
	const body = new ReadableStream({ cancel() { throw new Error(KEYS[0]); } });
	const f = fixture(t, [new Response(body, { status: 429 }), new Response(SUCCESS)]);
	const response = await f.run();
	assert.equal(response.status, 200);
	assert.equal(await response.text(), SUCCESS);
	assert.deepEqual(f.keysUsed(), KEYS.slice(0, 2));
	assert.ok(!JSON.stringify(f.log.mock.calls).includes(KEYS[0]));
});

test("upstream body errors expose only a safe stream error", async (t) => {
	const body = new ReadableStream({ pull(controller) { controller.error(new Error(KEYS[0])); } });
	const f = fixture(t, [new Response(body)]);
	const response = await f.run();
	await assert.rejects(response.text(), { message: "Upstream response failed." });
	assert.equal(f.fetch.mock.callCount(), 1);
	assert.ok(!JSON.stringify(f.log.mock.calls).includes(KEYS[0]));
});

test("non-key error responses redact raw and URL-encoded secrets", async (t) => {
	const key = "fake-key-044/with+symbols";
	const f = fixture(t, [new Response(`${key} ${encodeURIComponent(key)}`, { status: 500 })], { keys: [key] });
	const response = await f.run();
	assert.equal(response.status, 500);
	assert.equal(await response.text(), "[REDACTED] [REDACTED]");
	assert.equal(f.fetch.mock.callCount(), 1);
	assert.ok(!JSON.stringify(f.log.mock.calls).includes(key));
});
