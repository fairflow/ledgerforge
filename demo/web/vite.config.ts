import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// GitHub Pages serves a project site under /<repo>/. Set BASE_PATH at build time
// (e.g. BASE_PATH=/ledgerforge-demo) so all asset + link URLs resolve correctly.
// Empty by default for local dev and preview.
const base = process.env.BASE_PATH ?? '';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// Fully static output for GitHub Pages: every route is prerendered to HTML,
			// so no server runs. 404.html fallback lets Pages boot client-side routing for
			// any unknown path without clobbering the prerendered home page (index.html).
			adapter: adapter({ fallback: '404.html' }),
			paths: { base },
			prerender: { handleHttpError: 'warn' }
		})
	]
});
