<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<div class="lfdemo">
	<b>Public demo — every figure here is fictional.</b>
	Nothing is saved to a server: use <b>Download</b>, or <b>Generate text</b> then <b>Copy</b>,
	to take your edits away.
	<a href="https://github.com/fairflow/ledgerforge">How it works →</a>
</div>

{@render children()}
