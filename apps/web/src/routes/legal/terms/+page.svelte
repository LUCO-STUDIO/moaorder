<script lang="ts">
	import { IconChevronDown } from '@tabler/icons-svelte';
	import termsText from '$lib/legal/terms.txt?raw';

	function parseBlocks(text: string) {
		return text
			.trim()
			.split(/\n\s*\n/)
			.map((block) => {
				const lines = block.split('\n');
				return { header: lines[0], body: lines.slice(1) };
			});
	}

	const blocks = parseBlocks(termsText);
	const effectiveDate = '2026.05.11';
</script>

<svelte:head>
	<title>이용약관 - 모아오더</title>
</svelte:head>

<div class="min-h-screen bg-background">
	<main class="px-6 pb-16 pt-10 sm:px-8 sm:pt-16">
		<div class="mx-auto w-full max-w-2xl">
			<h1 class="text-[28px] font-bold leading-tight tracking-[-0.01em] text-foreground sm:text-[34px]">
				모아오더 이용약관
			</h1>

			<button
				type="button"
				class="mt-5 inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3.5 py-2 text-lg font-medium text-foreground transition-colors hover:border-foreground"
			>
				{effectiveDate}
				<IconChevronDown class="size-5 text-muted-foreground" />
			</button>

			<hr class="my-8 border-border" />

			<div class="space-y-7 text-[14px] leading-relaxed text-foreground sm:text-[15px]">
				{#each blocks as block}
					<section class="space-y-2.5">
						{#if block.body.length > 0}
							<h2 class="text-[15px] font-bold text-foreground sm:text-[16px]">{block.header}</h2>
							{#each block.body as line}
								{#if line.startsWith('- ')}
									<p class="pl-3 text-muted-foreground">{line}</p>
								{:else}
									<p class="text-muted-foreground">{line}</p>
								{/if}
							{/each}
						{:else}
							<p class="text-muted-foreground">{block.header}</p>
						{/if}
					</section>
				{/each}
			</div>
		</div>
	</main>
</div>
