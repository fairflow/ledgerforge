<script lang="ts">
	import { base } from '$app/paths';

	const tools = [
		{
			href: `${base}/accounts/`, title: 'Accounts & balances', tag: 'ledger', cls: 'g',
			one: 'Every account and its final balance — the book, in the browser.',
			help:
				'A read-only view rendered straight from the book: the full chart of accounts with each ' +
				"account's closing balance, a per-currency net-worth summary, the P&L, and the accounting " +
				'equation with a true double-entry check. Recomputed in the browser from the exported book.'
		},
		{
			href: `${base}/rules/`, title: 'Edit rules', tag: 'categoriser', cls: 'b',
			one: 'The rules editor — tune how payees map to accounts.',
			help:
				'Account-grouped view of every categorisation rule. Edit / move / delete / add the ' +
				'match-tokens, rename or delete an account, and tick <b>done</b> to collapse the ones ' +
				"you've checked. When you finish, click <b>Generate</b> and download the delta."
		},
		{
			href: `${base}/unspecified/`, title: 'Assign unspecified', tag: 'categoriser', cls: 'b',
			one: 'Clear the pile of payees no rule has caught yet.',
			help:
				'Each row is a payee currently landing in <span class="mono">Unspecified</span>. Give it ' +
				'a token and a destination account (or clear to skip), then download the result. An ' +
				'over-broad-token guard stops a short token grabbing unrelated transactions.'
		}
	];

	const steps: [string, string][] = [
		['Download', 'Export a statement (OFX) — here they are fictional.'],
		['Register', 'Add the account to the builder so it knows the currency, type and file.'],
		['Build', 'The engine parses everything, categorises by the rules, and reconciles every account to its closing balance.'],
		['Review', 'Use the two categoriser pages to catch anything in <b>Unspecified</b> or a wrong rule.'],
		['Rebuild', 'Re-run the builder — balances always reconcile by construction, so you only ever improve the <i>classification</i>, never break the books.']
	];

	const commands: [string, string, string][] = [
		['Build the book', 'python demo/build_demo.py', 'Parse the fictional statements, categorise by rules, build the multi-currency GnuCash book.'],
		['Export for the web', 'python demo/web/scripts/export_data.py', 'Dump the book, rules and unspecified payees to JSON for this Svelte app.'],
		['Run this site', 'npm run dev', 'Serve the toolkit locally with hot reload (needs Node 20+).'],
		['Build static', 'npm run build', 'Produce the static site deployed to GitHub Pages.']
	];
</script>

<svelte:head><title>ledgerforge demo toolkit</title></svelte:head>

<div class="page">
	<div class="wrap">
		<h1>ledgerforge demo toolkit</h1>
		<p class="sub">
			A live demo of the <a href="https://github.com/fairflow/ledgerforge">ledgerforge</a> engine's
			review toolkit — <b>everything here is fictional data.</b>
		</p>

		<h2>Tools</h2>
		<div class="cards">
			{#each tools as t}
				<a class="card" href={t.href}>
					<div class="t">{t.title} <span class="tag {t.cls}">{t.tag}</span></div>
					<div class="d">{t.one}</div>
					<div class="help">{@html t.help}</div>
				</a>
			{/each}
			<div class="card">
				<div class="t">The book <span class="tag g">GnuCash</span></div>
				<div class="d">The book of record — download and open in GnuCash desktop:</div>
				<div class="help">
					<a class="mono" href="{base}/demo.gnucash" download>↓ demo.gnucash</a>
					· <a href="https://www.gnucash.org/">get GnuCash →</a>
				</div>
			</div>
		</div>

		<h2>How it fits together</h2>
		<ol class="steps">
			{#each steps as [t, d]}
				<li><b>{t}.</b> {@html d}</li>
			{/each}
		</ol>

		<h2>Commands</h2>
		<table>
			{#each commands as [n, c, d]}
				<tr><td class="cn">{n}</td><td><code>{c}</code></td><td class="cd">{d}</td></tr>
			{/each}
		</table>

		<h2>Trust &amp; limits</h2>
		<div class="note">
			<b>Balances</b> reconcile to the statements by construction — high confidence.
			<b>Categorisation</b> depends on the rules — that's what the two categoriser pages are for.
			Cross-currency totals are valued at a fixed reporting rate. GnuCash stays the source of
			truth; this is a demonstration of the
			<a href="https://github.com/fairflow/ledgerforge">ledgerforge</a> engine with entirely
			fictional data.
		</div>

		<p class="foot">
			Rendered by SvelteKit from data the real engine exported. Source:
			<span class="mono">ledgerforge/demo/web</span>.
		</p>
	</div>
</div>

<style>
	.page { background: var(--bg); min-height: 100vh; }
	.wrap { max-width: 760px; margin: 0 auto; padding: 40px 20px 70px; }
	h1 { font-size: 25px; font-weight: 650; margin: 0 0 4px; }
	h2 { font-size: 15px; font-weight: 650; margin: 34px 0 12px; color: #333; text-transform: uppercase; letter-spacing: 0.04em; }
	.sub { color: var(--muted); font-size: 14px; margin: 0 0 6px; }
	.cards { display: grid; gap: 14px; }
	.card {
		display: block; text-decoration: none; color: inherit; background: #fff;
		border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px;
		transition: border-color 0.12s, box-shadow 0.12s;
	}
	.card:hover { border-color: var(--blue); box-shadow: 0 1px 8px rgba(37, 99, 235, 0.13); }
	.t { font-size: 16px; font-weight: 650; display: flex; align-items: center; gap: 8px; }
	.tag { font-size: 11px; font-weight: 500; color: var(--blue); background: #eaf1fe; border-radius: 5px; padding: 2px 7px; }
	.tag.g { color: var(--green); background: #e1f5ee; }
	.d { color: #555; font-size: 13px; margin-top: 5px; }
	.help { color: var(--muted); font-size: 12.5px; margin-top: 8px; border-top: 1px solid #f0f0f0; padding-top: 8px; }
	ol.steps { margin: 0; padding-left: 18px; color: #444; font-size: 13.5px; }
	ol.steps li { margin: 7px 0; }
	table { border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
	td { padding: 9px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
	tr:last-child td { border-bottom: none; }
	.cn { font-weight: 600; white-space: nowrap; width: 1%; }
	.cd { color: #777; }
	.note { background: #fff; border: 1px solid var(--line); border-left: 3px solid var(--blue); border-radius: 8px; padding: 12px 14px; font-size: 13px; color: #444; }
	.foot { margin-top: 30px; color: #999; font-size: 12px; line-height: 1.6; }
</style>
