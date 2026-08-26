// Compute the balance sheet, P&L and accounting equation from an exported book,
// mirroring demo/make_accounts.py exactly. This is what makes the accounts page a
// genuine in-browser GnuCash book viewer: feed it a book.json and it re-derives every
// figure — net worth, P&L, the accounting equation with FX translation reserve, and the
// true double-entry residual check — in the browser.

export interface Account {
	fullname: string;
	name: string;
	code: string;
	type: string;
	top: string;
	depth: number;
	balance: number;
	currency: string;
}

export interface Book {
	base: string;
	order: string[];
	fx: Record<string, number>;
	bs_date: string | null;
	pl_start: string | null;
	accounts: Account[];
}

const ASSET_TYPES = new Set(['ASSET', 'BANK', 'CASH', 'STOCK', 'MUTUAL']);
const LIAB_TYPES = new Set(['LIABILITY', 'CREDIT']);
const LIQUID_TYPES = new Set(['BANK', 'CASH']); // spendable now: bank + cash

export interface Row {
	code: string;
	name: string;
	depth: number;
	balance: number;
	currency: string;
	fullname: string;
	isParent: boolean;
	subtreeGbp: number;
}

export interface NetWorthCard {
	kind: 'liquid' | 'total' | 'currency';
	label: string;
	currency?: string;
	asset?: number;
	liab?: number;
	net: number;
	rateNote?: string;
}

export interface Computed {
	nAccounts: number;
	bsDate: string | null;
	plStart: string | null;
	cards: NetWorthCard[];
	pnl: { income: number; expenses: number; net: number; positive: boolean };
	equation: {
		A: number; L: number; Eqp: number; Ret: number; Fx: number; Etot: number;
		LplusE: number; residual: number; balances: boolean;
	};
	sections: { top: string; rows: Row[] }[];
	rate: Record<string, number>;
}

const rateFor = (fx: Record<string, number>, cur: string) => fx[cur] ?? 1;

export function compute(book: Book): Computed {
	const rate = { GBP: 1, ...book.fx };
	const nw: Record<string, { asset: number; liab: number }> = {};
	const eqv: Record<string, number> = {};
	const incv: Record<string, number> = {};
	const expv: Record<string, number> = {};
	const liq: Record<string, number> = {};
	const bump = (m: Record<string, number>, c: string, v: number) => (m[c] = (m[c] ?? 0) + v);

	const rowsByTop: Record<string, Row[]> = {};
	let nAccounts = 0;

	const sorted = [...book.accounts].sort((a, b) => a.fullname.localeCompare(b.fullname));
	for (const a of sorted) {
		if (a.type === 'ROOT') continue;
		nAccounts++;
		(rowsByTop[a.top] ||= []).push({
			code: a.code, name: a.name, depth: a.depth, balance: a.balance,
			currency: a.currency, fullname: a.fullname, isParent: false, subtreeGbp: 0
		});
		if (ASSET_TYPES.has(a.type)) {
			(nw[a.currency] ||= { asset: 0, liab: 0 }).asset += a.balance;
			if (LIQUID_TYPES.has(a.type)) bump(liq, a.currency, a.balance);
		} else if (LIAB_TYPES.has(a.type)) {
			(nw[a.currency] ||= { asset: 0, liab: 0 }).liab += a.balance;
		} else if (a.type === 'EQUITY') bump(eqv, a.currency, a.balance);
		else if (a.type === 'INCOME') bump(incv, a.currency, a.balance);
		else if (a.type === 'EXPENSE') bump(expv, a.currency, a.balance);
	}

	const allc = new Set([...Object.keys(nw), ...Object.keys(eqv), ...Object.keys(incv), ...Object.keys(expv)]);
	const sumOver = (f: (c: string) => number) => [...allc].reduce((s, c) => s + f(c), 0);

	// ---- net-worth cards, per currency ----
	const cards: NetWorthCard[] = [];
	for (const cur of Object.keys(nw).sort()) {
		const { asset, liab } = nw[cur];
		cards.push({ kind: 'currency', label: cur, currency: cur, asset, liab, net: asset - liab });
	}
	const combined = Object.keys(nw).reduce((s, c) => s + (nw[c].asset - nw[c].liab) * rateFor(rate, c), 0);
	const rateNote = Object.keys(rate).filter((c) => c !== 'GBP').sort()
		.map((c) => `${c} ${rate[c].toFixed(3)}`).join(', ') || 'no FX set';
	cards.unshift({ kind: 'total', label: 'TOTAL ≈ GBP', net: combined, rateNote });
	const liqGbp = Object.keys(liq).reduce((s, c) => s + liq[c] * rateFor(rate, c), 0);
	cards.unshift({ kind: 'liquid', label: 'LIQUID ≈ GBP', net: liqGbp });

	// ---- P&L (income statement), GBP at market FX ----
	const incGbp = sumOver((c) => (incv[c] ?? 0) * rateFor(rate, c));
	const expGbp = sumOver((c) => (expv[c] ?? 0) * rateFor(rate, c));
	const netGbp = incGbp - expGbp;

	// ---- accounting equation: GBP reporting, foreign at market FX, FX translation reserve ----
	const A = sumOver((c) => (nw[c]?.asset ?? 0) * rateFor(rate, c));
	const L = sumOver((c) => (nw[c]?.liab ?? 0) * rateFor(rate, c));
	const Eqp = sumOver((c) => (eqv[c] ?? 0) * rateFor(rate, c));
	const Ret = netGbp;
	const Fx = A - L - Eqp - Ret;
	const Etot = Eqp + Ret + Fx;
	// Genuine double-entry integrity check at recorded par (no FX plug): residual must be exactly 0.
	const residual = sumOver((c) => (nw[c]?.asset ?? 0) - (nw[c]?.liab ?? 0) - (eqv[c] ?? 0) - (incv[c] ?? 0) + (expv[c] ?? 0));

	// ---- collapsible tree: parents carry the GBP subtree total ----
	const ownGbp: Record<string, number> = {};
	const allFn: string[] = [];
	for (const top of book.order) {
		for (const r of rowsByTop[top] ?? []) {
			ownGbp[r.fullname] = r.balance * rateFor(rate, r.currency);
			allFn.push(r.fullname);
		}
	}
	const fnset = new Set(allFn);
	const isParent = (fn: string) => [...fnset].some((x) => x.startsWith(fn + ':'));
	const subtree = (fn: string) =>
		(ownGbp[fn] ?? 0) + allFn.filter((x) => x.startsWith(fn + ':')).reduce((s, x) => s + ownGbp[x], 0);

	const sections = book.order
		.filter((top) => rowsByTop[top]?.length)
		.map((top) => ({
			top,
			rows: rowsByTop[top].map((r) => {
				const parent = isParent(r.fullname);
				return { ...r, isParent: parent, subtreeGbp: parent ? subtree(r.fullname) : 0 };
			})
		}));

	return {
		nAccounts,
		bsDate: book.bs_date,
		plStart: book.pl_start,
		cards,
		pnl: { income: incGbp, expenses: expGbp, net: netGbp, positive: netGbp >= 0 },
		equation: { A, L, Eqp, Ret, Fx, Etot, LplusE: L + Etot, residual, balances: Math.abs(residual) < 0.01 },
		sections,
		rate
	};
}

export function fmtDate(iso: string | null): string {
	if (!iso) return '';
	const [y, m, d] = iso.split('-').map(Number);
	const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	return `${d.toString().padStart(2, '0')} ${months[m - 1]} ${y}`;
}
