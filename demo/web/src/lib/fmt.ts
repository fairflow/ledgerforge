// Number formatting shared across the toolkit pages, matching the Python generators:
//   fmt()   → "{:,.2f}"  (thousands sep, 2 dp)   used on the accounts page
//   money() → signed "£1,234.56"                 used on the unspecified page

export function fmt(v: number): string {
	// Snap sub-cent magnitudes to +0 so a float residual never prints as "-0.00".
	const n = Math.abs(v) < 0.005 ? 0 : v;
	return n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function money(n: number): string {
	return (n < 0 ? '-' : '') + '£' + Math.abs(n).toLocaleString('en-GB', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2
	});
}

export const SYM: Record<string, string> = { GBP: '£', EUR: '€', USD: '$' };
