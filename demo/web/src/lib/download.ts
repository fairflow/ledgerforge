// Client-side "save" — the static demo has no backend, so the toolkit's Save buttons
// hand the identical JSON to the browser as a download (mirrors demo/_demo_mode.py).
export function download(name: string, text: string): boolean {
	try {
		const b = new Blob([text], { type: 'application/json;charset=utf-8' });
		const u = URL.createObjectURL(b);
		const a = document.createElement('a');
		a.href = u;
		a.download = name;
		a.style.display = 'none';
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		setTimeout(() => URL.revokeObjectURL(u), 1500);
		return true;
	} catch {
		return false;
	}
}

export async function copyText(text: string): Promise<void> {
	try {
		await navigator.clipboard.writeText(text);
	} catch {
		const tmp = document.createElement('textarea');
		tmp.value = text;
		tmp.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
		document.body.appendChild(tmp);
		tmp.focus();
		tmp.select();
		document.execCommand('copy');
		document.body.removeChild(tmp);
	}
}
