<script lang="ts">
	import { base } from '$app/paths';
	import bookData from '$lib/data/book.json';
	import { compute, fmtDate, type Book } from '$lib/book';
	import { fmt, SYM } from '$lib/fmt';

	const book = bookData as Book;
	const c = compute(book);
	const bsDate = fmtDate(c.bsDate);
	const plStart = fmtDate(c.plStart);

	// Collapsible tree: a row is hidden when any collapsed ancestor path is its prefix.
	let collapsed = $state<Set<string>>(new Set());
	function toggle(fn: string) {
		const s = new Set(collapsed);
		s.has(fn) ? s.delete(fn) : s.add(fn);
		collapsed = s;
	}
	function hidden(fn: string): boolean {
		for (const p of collapsed) if (fn.startsWith(p + ':')) return true;
		return false;
	}
	const pad = (depth: number) => 4 + depth * 20;
</script>

<svelte:head><title>Accounts &amp; balances</title></svelte:head>

<div class="page">
	<div class="wrap">
		<a class="back" href="{base}/">← toolkit home</a>
		<h1>Accounts &amp; balances</h1>
		<p class="sub">
			{c.nAccounts} accounts · read-only snapshot · <b>balance sheet as at {bsDate}</b> · fictional demo data
		</p>

		<div class="nwrap">
			{#each c.cards as card}
				{#if card.kind === 'liquid'}
					<div class="nw" style="border-color:var(--liquid)">
						<div class="nwc" style="color:var(--liquid)">{card.label}</div>
						<div class="nwr tot" style="margin-top:26px">
							<span>Cash + savings</span><b style="color:var(--liquid)">{fmt(card.net)}</b>
						</div>
						<div class="nwr" style="font-size:11px;color:#999"><span></span><span>bank + cash accounts</span></div>
					</div>
				{:else if card.kind === 'total'}
					<div class="nw" style="border-color:var(--green)">
						<div class="nwc" style="color:var(--green)">{card.label}</div>
						<div class="nwr tot" style="margin-top:26px"><span>Net worth</span><b>{fmt(card.net)}</b></div>
						<div class="nwr" style="font-size:11px;color:#999"><span>at</span><span>{card.rateNote}</span></div>
					</div>
				{:else}
					<div class="nw">
						<div class="nwc">{card.currency}</div>
						<div class="nwr"><span>Assets</span><b>{fmt(card.asset ?? 0)}</b></div>
						<div class="nwr"><span>Liabilities</span><b>{fmt(card.liab ?? 0)}</b></div>
						<div class="nwr tot"><span>Net worth</span><b>{fmt(card.net)}</b></div>
					</div>
				{/if}
			{/each}
		</div>

		<h2>Income &amp; expenses (P&amp;L) <span class="per">{plStart} – {bsDate}</span></h2>
		<table class="fin">
			<tbody>
				<tr class="r"><td class="nm">Income</td><td class="bal">{fmt(c.pnl.income)}</td></tr>
				<tr class="r"><td class="nm">Expenses</td><td class="bal">{fmt(c.pnl.expenses)}</td></tr>
				<tr class="r">
					<td class="nm strong">Net {c.pnl.positive ? 'surplus' : 'deficit'}</td>
					<td class="bal strong" style="color:{c.pnl.positive ? 'var(--green)' : '#b00'}">{fmt(c.pnl.net)}</td>
				</tr>
			</tbody>
		</table>

		<h2>Accounting equation — Assets = Liabilities + Equity <span class="per">as at {bsDate}</span></h2>
		<p class="sub tight">Reporting currency GBP; foreign balances at market FX.</p>
		<table class="fin">
			<tbody>
				<tr class="r"><td class="nm">Assets</td><td class="bal">{fmt(c.equation.A)}</td></tr>
				<tr class="r"><td class="nm">Liabilities</td><td class="bal">{fmt(c.equation.L)}</td></tr>
				<tr class="r z"><td class="nm indent">posted equity</td><td class="bal">{fmt(c.equation.Eqp)}</td></tr>
				<tr class="r z"><td class="nm indent">retained earnings</td><td class="bal">{fmt(c.equation.Ret)}</td></tr>
				<tr class="r z"><td class="nm indent">FX translation reserve</td><td class="bal">{fmt(c.equation.Fx)}</td></tr>
				<tr class="r"><td class="nm">Total equity</td><td class="bal">{fmt(c.equation.Etot)}</td></tr>
				<tr class="r"><td class="nm strong">Liabilities + Equity</td><td class="bal strong">{fmt(c.equation.LplusE)}</td></tr>
				<tr class="r">
					<td class="nm" colspan="2" style="padding-top:6px">
						Double-entry check:
						{#if c.equation.balances}
							<span style="color:var(--green)">✓ residual £{fmt(0)} — books balance</span>
						{:else}
							<span style="color:#b00">residual {fmt(c.equation.residual)}</span>
						{/if}
					</td>
				</tr>
			</tbody>
		</table>

		{#each c.sections as section}
			<h2>{section.top}</h2>
			<table>
				<thead>
					<tr class="hd"><th>Account</th><th class="rt">Balance</th><th></th><th class="rt">Total GBP</th></tr>
				</thead>
				<tbody>
					{#each section.rows as r}
						<tr
							class="r"
							class:parent={r.isParent}
							class:z={!r.isParent && Math.abs(r.balance) < 0.005}
							style:display={hidden(r.fullname) ? 'none' : ''}
						>
							{#if r.isParent}
								<td class="nm click" style:padding-left="{pad(r.depth)}px" title={r.code ? `code ${r.code}` : ''}
									onclick={() => toggle(r.fullname)}>
									<span class="tog">{collapsed.has(r.fullname) ? '▸' : '▾'}</span>{r.name}
								</td>
								<td class="bal"></td><td class="cur"></td>
								<td class="tot2">{fmt(r.subtreeGbp)}</td>
							{:else}
								<td class="nm" style:padding-left="{pad(r.depth)}px" title={r.code ? `code ${r.code}` : ''}>{r.name}</td>
								<td class="bal">{fmt(r.balance)}</td>
								<td class="cur">{SYM[r.currency] ?? r.currency}</td>
								<td class="tot2"></td>
							{/if}
						</tr>
					{/each}
				</tbody>
			</table>
		{/each}

		<div class="note">
			Balances reconcile to the (fictional) statements by construction, and the double-entry check
			above is a true zero (recorded basis, no FX plug). Foreign balances are valued in GBP at a
			fixed reporting rate (EUR 0.855); the gap versus the recorded 1:1 par sits in the
			<b>FX translation reserve</b>. Hover an account name for its chart code; click a heading to collapse it.
		</div>
		<p class="foot">Recomputed in the browser from <span class="mono">book.json</span>, exported by the real engine.</p>
	</div>
</div>

<style>
	.page { background: var(--bg); min-height: 100vh; }
	.wrap { max-width: 820px; margin: 0 auto; padding: 20px 20px 70px; }
	a.back { font-size: 13px; color: var(--blue); text-decoration: none; }
	h1 { font-size: 24px; font-weight: 650; margin: 8px 0 4px; }
	.sub { color: var(--muted); font-size: 13px; margin: 0 0 20px; }
	.sub.tight { margin: -2px 0 8px; }
	h2 { font-size: 14px; font-weight: 650; margin: 30px 0 8px; color: #333; text-transform: uppercase; letter-spacing: 0.04em; }
	h2 .per { font-weight: 400; text-transform: none; letter-spacing: 0; font-size: 12px; color: #999; }
	.nwrap { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 6px 0; }
	.nw { background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
	.nwc { font-size: 12px; font-weight: 650; color: #888; letter-spacing: 0.05em; }
	.nwr { display: flex; justify-content: space-between; font-size: 13px; color: #555; margin-top: 5px; }
	.nwr b { font-family: var(--mono); color: #222; }
	.nwr.tot { border-top: 1px solid #eee; margin-top: 7px; padding-top: 6px; color: #111; font-weight: 600; }
	.nwr.tot b { color: var(--green); }
	table { border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
	table.fin { max-width: 480px; }
	th, td { padding: 6px 12px; border-bottom: 1px solid #f2f2f2; text-align: left; }
	th.rt { text-align: right; }
	tr.hd th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: #999; font-weight: 600; background: #fafafa; }
	td.bal { font-family: var(--mono); text-align: right; white-space: nowrap; }
	td.cur { color: #999; width: 1%; font-size: 12px; }
	.strong { font-weight: 500; }
	.indent { padding-left: 24px; }
	tr.z td.bal, tr.z td.nm { color: #bbb; }
	tr:last-child td { border-bottom: none; }
	.note { background: #fff; border: 1px solid var(--line); border-left: 3px solid var(--blue); border-radius: 8px; padding: 11px 14px; font-size: 12.5px; color: #555; margin-top: 22px; }
	.foot { margin-top: 22px; color: #999; font-size: 12px; }
	.tog { display: inline-block; width: 14px; color: #999; user-select: none; }
	tr.parent td.nm { font-weight: 500; }
	td.click { cursor: pointer; }
	td.tot2 { font-family: var(--mono); text-align: right; white-space: nowrap; color: var(--liquid); }
</style>
