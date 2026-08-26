<script lang="ts">
	import { base } from '$app/paths';
	import unspecData from '$lib/data/unspec.json';
	import { download, copyText } from '$lib/download';
	import { money } from '$lib/fmt';

	interface Txn { d: string; a: number; s: string; aid: string }
	interface Raw { d: string; c: number; t: number; tok: string; acct: string; src: string[]; txns: Txn[] }
	interface Row extends Raw { token: string; account: string; routed: boolean; routeEligible: boolean }

	const ACCTS: string[] = unspecData.accts;
	const ALLDESC: Record<string, number> = unspecData.alldesc;

	let rows = $state<Row[]>(
		(unspecData.rows as Raw[]).map((r) => ({
			...r, token: r.tok, account: r.acct, routed: false,
			routeEligible: r.c === 1 && r.txns.length === 1 && !!r.txns[0]?.aid
		}))
	);
	let routes = $state<any[]>([]);
	let filter = $state('');
	let outText = $state('');
	let showOut = $state(false);
	let saved = $state('');
	let copyLabel = $state('Copy');

	const assigned = $derived(rows.filter((r) => r.account.trim() && r.token.trim()).length);
	const blank = $derived(rows.length - assigned);

	function shown(r: Row): boolean {
		const q = filter.toUpperCase();
		return r.d.includes(q) || r.tok.toUpperCase().includes(q);
	}

	function matchCount(tok: string): number {
		const u = (tok || '').toUpperCase();
		if (!u) return 0;
		let n = 0;
		for (const k in ALLDESC) if (k.includes(u)) n += ALLDESC[k];
		return n;
	}
	function guardOK(): boolean {
		const bad: string[] = [];
		for (const r of rows) {
			const t = r.token.trim(), a = r.account.trim();
			if (!t || !a) continue;
			const mc = matchCount(t);
			if (mc > r.c + 5) bad.push(`"${t}" matches ${mc} transactions, but this payee has only ${r.c}`);
		}
		if (bad.length) {
			alert(
				'Some tokens are too broad — they would grab unrelated transactions:\n\n' +
				bad.join('\n') +
				'\n\nNarrow each to a distinctive chunk (a surname, shop name, or reference), or clear it to skip — then try again.'
			);
			return false;
		}
		return true;
	}

	function grouped() {
		const map: Record<string, { a: string; t: string }> = {};
		for (const r of rows) {
			const t = r.token.trim(), a = r.account.trim();
			if (!t || !a) continue;
			const k = a + '||' + t.toUpperCase();
			if (!map[k]) map[k] = { a, t };
		}
		const byA: Record<string, string[]> = {};
		for (const k of Object.keys(map)) { const m = map[k]; (byA[m.a] ||= []).push(m.t); }
		return byA;
	}

	function buildText(): string {
		const byA = grouped();
		const lines = Object.keys(byA).sort().map((a) => `  - ${a}  <-  ${byA[a].map((x) => `"${x}"`).join(', ')}`);
		const skipped = rows.filter((r) => !(r.account.trim() && r.token.trim())).length;
		return (
			'Unspecified assignments (add these match tokens to demo/data/rules.json, merging into each account\'s rule):\n\n' +
			(lines.length ? lines.join('\n') : '  (none)') +
			`\n\nLeft unassigned: ${skipped} payees.\nAfter applying, re-run demo/build_demo.py.`
		);
	}
	function buildJSON() {
		const byA = grouped();
		return {
			assignments: Object.keys(byA).sort().map((a) => ({ account: a, tokens: byA[a] })),
			skipped: rows.filter((r) => !(r.account.trim() && r.token.trim())).length
		};
	}

	function generate() { if (!guardOK()) return; outText = buildText(); showOut = true; }
	async function copy() {
		if (!guardOK()) return;
		if (!outText) outText = buildText();
		showOut = true;
		await copyText(outText);
		copyLabel = 'Copied';
		setTimeout(() => (copyLabel = 'Copy'), 1200);
	}
	function save() {
		if (!guardOK()) return;
		const payload: any = buildJSON();
		if (routes.length) payload.routes = routes;
		const n = payload.assignments.reduce((acc: number, a: any) => acc + a.tokens.length, 0);
		const ok = download('assignments.json', JSON.stringify(payload, null, 2));
		saved = ok ? `downloaded ✓ ${n} assignment${n === 1 ? '' : 's'}` : 'download blocked — use Generate text → Copy';
	}
	function routeExact(r: Row) {
		const acct = r.account.trim();
		if (!acct) { alert('Set an account first'); return; }
		const txn = r.txns[0];
		routes.push({ acct: txn.aid, date: txn.d, amount: txn.a.toFixed(2), to: acct });
		r.routed = true;
	}
</script>

<svelte:head><title>Assign unspecified payees</title></svelte:head>

<datalist id="ua-list">{#each ACCTS as a}<option value={a}></option>{/each}</datalist>

<div class="bar">
	<strong>Assign unspecified payees</strong>
	<span class="count">{assigned} assigned · {blank} blank · {rows.length} total</span>
	<input bind:value={filter} placeholder="filter…" />
	<span style="flex:1"></span>
	<button onclick={save}>Download JSON</button>
	<button class="sec" onclick={generate}>Generate text</button>
	<button class="sec" onclick={copy}>{copyLabel}</button>
	<span class="ok">{saved}</span>
	<a class="home" href="{base}/">home</a>
</div>

<div class="note">
	Each row: the payee (times seen · signed total), the <b style="color:var(--green)">source account(s)</b>
	it came from, and the dated transactions — so you can place it. Set a <b>token</b> (what will match —
	pick a distinctive chunk, not 2–3 letters) and an <b>account</b>; clear the account to skip a payee.
	When done, <b>Download JSON</b>, or <b>Generate text → Copy</b>.
</div>

{#if showOut}<textarea readonly bind:value={outText}></textarea>{/if}

<div class="wrap">
	{#each rows as r, i (i)}
		<div class="ur" class:skip={!r.account.trim()} class:need={!r.account.trim()} style:display={shown(r) ? '' : 'none'}
			style:opacity={r.routed ? '0.4' : ''}>
			<div class="ud">
				<b>{r.c}× · {money(r.t)}&nbsp;&nbsp;</b>{r.d}
				<div class="usrc">from {r.src.join(', ')}</div>
				{#if r.txns.length}
					<div class="udet">
						{#each r.txns.slice(0, 8) as x}<span>{x.d}&nbsp;&nbsp;{money(x.a)}&nbsp;&nbsp;{x.s}</span><br />{/each}
						{#if r.txns.length > 8}…+{r.txns.length - 8} more{/if}
					</div>
				{/if}
			</div>
			<div class="uf">
				<input class="ut" bind:value={r.token} aria-label="token" />
				<input class="ua" list="ua-list" bind:value={r.account} placeholder="account…" aria-label="account" />
				{#if r.routeEligible}
					<button class="sec" disabled={r.routed} onclick={() => routeExact(r)}>{r.routed ? 'Queued ✓' : 'Route exact'}</button>
				{/if}
			</div>
		</div>
	{/each}
</div>

<style>
	.bar { position: sticky; top: 0; background: #fff; border-bottom: 1px solid #ddd; padding: 10px 16px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; z-index: 5; }
	.bar .count { color: #555; font-size: 13px; }
	.bar input { font-size: 13px; padding: 5px 8px; border: 1px solid #ccc; border-radius: 6px; }
	.bar .ok { font-size: 12px; color: var(--green); font-weight: bold; }
	.bar .home { font-size: 12px; }
	.note { padding: 10px 16px; color: #555; font-size: 12px; line-height: 1.6; }
	.note b { color: #111; }
	textarea { width: calc(100% - 32px); height: 200px; margin: 0 16px; font-family: var(--mono); font-size: 12px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 6px; padding: 8px; }
	.wrap { padding: 0 16px 60px; }
	.ur { padding: 7px 0; border-bottom: 1px solid #eee; }
	.ur.need .ud { color: #b45309; }
	.ud { font-size: 12px; color: #555; margin-bottom: 4px; word-break: break-word; }
	.ud b { color: #111; font-weight: 600; font-variant-numeric: tabular-nums; }
	.uf { display: flex; gap: 8px; flex-wrap: wrap; }
	.uf input { font-size: 12px; font-family: var(--mono); padding: 5px 7px; border: 1px solid #ccc; border-radius: 6px; }
	.ut { width: 240px; max-width: 100%; }
	.ua { width: 290px; max-width: 100%; }
	.usrc { font-size: 11px; color: var(--green); margin-top: 3px; }
	.udet { font-size: 11px; color: #999; margin-top: 2px; font-family: var(--mono); line-height: 1.5; }
</style>
