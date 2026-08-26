<script lang="ts">
	import { base } from '$app/paths';
	import rulesData from '$lib/data/rules.json';
	import { download, copyText } from '$lib/download';

	const ACCTS: string[] = rulesData.accts;
	const dd = (t: string, g: boolean) => (g ? `/${t}/` : t);

	interface Tok {
		t: string; g: boolean; key: string;
		del: boolean; showEdit: boolean; showMove: boolean;
		editText: string; editRegex: boolean; moveText: string;
	}
	interface Grp {
		a: string; ren: string; del: boolean; done: boolean;
		showRename: boolean; showAdd: boolean; addText: string; addRegex: boolean;
		toks: Tok[]; adds: { t: string; g: boolean }[];
	}

	const mkTok = (t: string, g: boolean, key: string): Tok => ({
		t, g, key, del: false, showEdit: false, showMove: false, editText: t, editRegex: g, moveText: ''
	});

	let groups = $state<Grp[]>(
		rulesData.groups.map((g, gi) => ({
			a: g.a, ren: '', del: false, done: false,
			showRename: false, showAdd: false, addText: '', addRegex: false,
			toks: [
				...g.m.map((t, j) => mkTok(t, false, `${gi}m${j}`)),
				...g.r.map((t, j) => mkTok(t, true, `${gi}r${j}`))
			],
			adds: []
		}))
	);

	let filter = $state('');
	let hideDone = $state(false);
	let outText = $state('');
	let showOut = $state(false);
	let saved = $state('');
	let copyLabel = $state('Copy');

	const eff = (g: Grp) => (g.ren.trim() ? g.ren.trim() : g.a);
	const tokEdited = (t: Tok) => t.editText.trim() !== '' && (t.editText.trim() !== t.t || t.editRegex !== t.g);
	const tokEffT = (t: Tok) => (tokEdited(t) ? t.editText.trim() : t.t);
	const tokEffG = (t: Tok) => (tokEdited(t) ? t.editRegex : t.g);
	const tokMov = (g: Grp, t: Tok) => {
		const v = t.moveText.trim();
		return v && v !== eff(g) ? v : '';
	};

	const changes = $derived(
		groups.reduce((ch, g) => {
			if (g.del) return ch + 1;
			if (g.ren.trim()) ch++;
			for (const t of g.toks) {
				if (t.del) ch++;
				else if (tokMov(g, t)) ch++;
				else if (tokEdited(t)) ch++;
			}
			return ch + g.adds.length;
		}, 0)
	);
	const doneCount = $derived(groups.filter((g) => g.done).length);

	function visible(g: Grp): boolean {
		const q = filter.toUpperCase();
		const accHit = eff(g).toUpperCase().includes(q);
		const tokHit = g.toks.some((t) => dd(tokEffT(t), tokEffG(t)).toUpperCase().includes(q));
		let show = q === '' || accHit || tokHit;
		if (hideDone && g.done) show = false;
		return show;
	}

	function toggleDel(g: Grp) { g.del = !g.del; }
	function addToken(g: Grp) {
		const v = g.addText.trim();
		if (!v) return;
		g.adds.push({ t: v, g: g.addRegex });
		g.addText = '';
		g.addRegex = false;
	}
	function removeAdd(g: Grp, i: number) { g.adds.splice(i, 1); }

	function buildText(): string {
		const dT: string[] = [], mT: string[] = [], eT: string[] = [], adT: string[] = [], rA: string[] = [], dA: string[] = [];
		for (const g of groups) {
			const acct = eff(g);
			if (g.del) {
				const kept = g.toks.filter((t) => !tokMov(g, t)).map((t) => dd(t.t, t.g));
				dA.push(`  - ${acct}   [${kept.join(', ')}]`);
				for (const t of g.toks) if (tokMov(g, t)) mT.push(`  - "${dd(t.t, t.g)}"  ${acct}  ->  ${tokMov(g, t)}`);
				for (const it of g.adds) adT.push(`  - "${dd(it.t, it.g)}" (${it.g ? 'regex' : 'literal'})  to  ${acct}`);
				continue;
			}
			if (g.ren.trim()) rA.push(`  - ${g.a}  ->  ${g.ren.trim()}`);
			for (const t of g.toks) {
				if (t.del) dT.push(`  - "${dd(t.t, t.g)}"  from  ${acct}`);
				else if (tokMov(g, t)) mT.push(`  - "${dd(t.t, t.g)}"  ${acct}  ->  ${tokMov(g, t)}`);
				else if (tokEdited(t))
					eT.push(`  - "${dd(t.t, t.g)}" (${t.g ? 'regex' : 'literal'})  ->  "${dd(tokEffT(t), tokEffG(t))}" (${tokEffG(t) ? 'regex' : 'literal'})  in  ${acct}`);
			}
			for (const it of g.adds) adT.push(`  - "${dd(it.t, it.g)}" (${it.g ? 'regex' : 'literal'})  to  ${acct}`);
		}
		const none = (a: string[]) => (a.length ? a.join('\n') : '  (none)');
		let s = 'Mapping review (account-grouped, token-level):\n\n';
		s += `DELETE TOKENS:\n${none(dT)}\n\n`;
		s += `MOVE TOKENS:\n${none(mT)}\n\n`;
		s += `EDIT TOKENS (text and/or literal<->regex):\n${none(eT)}\n\n`;
		s += `ADD TOKENS:\n${none(adT)}\n\n`;
		s += `RENAME ACCOUNTS:\n${none(rA)}\n\n`;
		s += `DELETE ACCOUNTS:\n${none(dA)}\n\n`;
		s += `(${doneCount} accounts marked done.) Apply to demo/data/rules.json, then re-run demo/build_demo.py.`;
		return s;
	}

	function buildJSON() {
		const moves: any[] = [], deletes: any[] = [], adds: any[] = [], edits: any[] = [], renames: any[] = [], deleteAccounts: string[] = [];
		for (const g of groups) {
			const acct = eff(g);
			if (g.del) {
				deleteAccounts.push(acct);
				for (const t of g.toks) if (tokMov(g, t)) moves.push({ token: dd(t.t, t.g), from: acct, to: tokMov(g, t) });
				for (const it of g.adds) adds.push({ token: dd(it.t, it.g), account: acct, regex: !!it.g });
				continue;
			}
			if (g.ren.trim()) renames.push({ from: g.a, to: g.ren.trim() });
			for (const t of g.toks) {
				if (t.del) deletes.push({ token: dd(t.t, t.g), account: acct });
				else if (tokMov(g, t)) moves.push({ token: dd(t.t, t.g), from: acct, to: tokMov(g, t) });
				else if (tokEdited(t)) edits.push({ token: dd(t.t, t.g), account: acct, to: dd(tokEffT(t), tokEffG(t)), regex: tokEffG(t) });
			}
			for (const it of g.adds) adds.push({ token: dd(it.t, it.g), account: acct, regex: !!it.g });
		}
		return { moves, deletes, adds, edits, renames, deleteAccounts };
	}

	function generate() { outText = buildText(); showOut = true; }
	async function copy() {
		if (!outText) outText = buildText();
		showOut = true;
		await copyText(outText);
		copyLabel = 'Copied';
		setTimeout(() => (copyLabel = 'Copy'), 1200);
	}
	function save() {
		const ok = download('rules-delta.json', JSON.stringify(buildJSON(), null, 2));
		saved = ok ? 'downloaded ✓ rules-delta.json' : 'download blocked — use Generate text → Copy';
	}
</script>

<svelte:head><title>Edit categorisation rules</title></svelte:head>

<datalist id="ed-accts">{#each ACCTS as a}<option value={a}></option>{/each}</datalist>

<div class="bar">
	<strong>Edit rules</strong>
	<span class="count">{changes} changes · {doneCount} done · {groups.length} accounts</span>
	<input type="text" bind:value={filter} placeholder="filter…" />
	<label><input type="checkbox" bind:checked={hideDone} /> hide done</label>
	<span style="flex:1"></span>
	<button onclick={save}>Download JSON</button>
	<button class="sec" onclick={generate}>Generate text</button>
	<button class="sec" onclick={copy}>{copyLabel}</button>
	<span class="ok">{saved}</span>
	<a class="home" href="{base}/">home</a>
</div>

<div class="note">
	One token per line. <b>edit</b> a token (tick <b>regex</b> for a pattern), <b>move</b> it to another
	account, <b>×</b> delete it, <b>+ add</b> a new one. On the heading: <b>rename</b> / <b>delete account</b>,
	and tick <b>done</b> to collapse a reviewed account. When finished, <b>Generate text → Copy</b>, or
	<b>Download JSON</b>.
</div>

{#if showOut}<textarea readonly bind:value={outText}></textarea>{/if}

<div class="wrap">
	{#each groups as g (g.a)}
		<div class="grp" class:adel={g.del} class:done={g.done} style:display={visible(g) ? '' : 'none'}>
			<div class="gh">
				<input type="checkbox" bind:checked={g.done} title="mark reviewed (collapse)" />
				<span class="an" class:ren={g.ren.trim()}>{eff(g)}</span>
				<span class="cnt">{g.toks.length}</span>
				<span style="flex:1"></span>
				<button class="mini" onclick={() => (g.showRename = !g.showRename)}>rename</button>
				<button class="mini" class:on={g.del} onclick={() => toggleDel(g)}>{g.del ? 'account deleted' : 'delete account'}</button>
				<button class="mini" onclick={() => (g.showAdd = !g.showAdd)}>+ add</button>
			</div>

			{#if g.showRename}
				<input class="in ren-in" list="ed-accts" bind:value={g.ren} placeholder="rename account to…" />
			{/if}

			{#if !g.done}
				<div class="body">
					{#each g.toks as t (t.key)}
						<div class="tr" class:tdel={t.del}>
							<div class="tt" class:edt={tokEdited(t)}>
								{#if tokEffG(t)}<span class="rx">/{tokEffT(t)}/</span>{:else}{tokEffT(t)}{/if}
							</div>
							<span class="bd">{tokMov(g, t) ? '→ ' + tokMov(g, t) : ''}</span>
							<button class="tb" onclick={() => (t.showEdit = !t.showEdit)}>edit</button>
							<button class="tb" onclick={() => (t.showMove = !t.showMove)}>move</button>
							<button class="tb" class:on={t.del} onclick={() => (t.del = !t.del)}>×</button>
						</div>
						{#if t.showEdit}
							<div class="rev">
								<input class="in" bind:value={t.editText} style="width:240px" />
								<label class="rl"><input type="checkbox" bind:checked={t.editRegex} /> regex</label>
							</div>
						{/if}
						{#if t.showMove}
							<div class="rev">
								<input class="in" list="ed-accts" bind:value={t.moveText} placeholder="move to account…" style="width:280px" />
							</div>
						{/if}
					{/each}

					{#each g.adds as it, i}
						<div class="tr">
							<div class="tt addt">{#if it.g}<span class="rx">/{it.t}/</span>{:else}{it.t}{/if}</div>
							<button class="tb" onclick={() => removeAdd(g, i)}>×</button>
						</div>
					{/each}
				</div>

				{#if g.showAdd}
					<div class="rev addrow">
						<input class="in" bind:value={g.addText} placeholder="new token" style="width:240px"
							onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addToken(g); } }} />
						<label class="rl"><input type="checkbox" bind:checked={g.addRegex} /> regex</label>
						<button class="tb" onclick={() => addToken(g)}>add</button>
					</div>
				{/if}
			{/if}
		</div>
	{/each}
</div>

<style>
	.bar { position: sticky; top: 0; background: #fff; border-bottom: 1px solid #ddd; padding: 10px 16px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; z-index: 5; }
	.bar .count { color: #555; font-size: 13px; }
	.bar input[type='text'] { font-size: 13px; padding: 5px 8px; border: 1px solid #ccc; border-radius: 6px; }
	.bar label { font-size: 13px; color: #555; display: inline-flex; align-items: center; gap: 5px; }
	.bar .ok { font-size: 12px; color: var(--green); }
	.bar .home { font-size: 12px; }
	.note { padding: 10px 16px; color: #555; font-size: 12px; line-height: 1.6; }
	.note b { color: #111; }
	textarea { width: calc(100% - 32px); height: 200px; margin: 0 16px; font-family: var(--mono); font-size: 12px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 6px; padding: 8px; }
	.wrap { padding: 0 16px 60px; }
	.grp { border: 1px solid var(--line); border-radius: 10px; margin: 10px 0; padding: 8px 12px 6px; }
	.grp.adel { opacity: 0.45; }
	.grp.done { opacity: 0.6; background: #f6f8f6; }
	.gh { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; border-bottom: 1px solid #eee; padding-bottom: 6px; margin-bottom: 4px; }
	.an { font-size: 14px; font-weight: 600; font-family: var(--mono); }
	.an.ren { color: var(--liquid); }
	.cnt { font-size: 11px; color: #999; }
	.tr { display: flex; align-items: center; gap: 7px; padding: 3px 0 3px 2px; }
	.tr.tdel .tt { opacity: 0.4; text-decoration: line-through; }
	.tt { flex: 1; min-width: 0; font-size: 13px; word-break: break-word; }
	.tt.edt { color: var(--liquid); }
	.tt.addt { color: #1d9e75; }
	.tt .rx { color: #888; font-family: var(--mono); }
	.bd { font-size: 12px; color: var(--liquid); font-family: var(--mono); }
	.rev { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 2px 0 6px 4px; }
	.in { font-size: 12px; font-family: var(--mono); padding: 5px 7px; border: 1px solid #ccc; border-radius: 6px; }
	.ren-in { display: block; width: 320px; max-width: 100%; margin: 4px 0; }
	.rl { font-size: 12px; color: #555; display: inline-flex; align-items: center; gap: 5px; }
	.addrow { margin-top: 4px; }
</style>
