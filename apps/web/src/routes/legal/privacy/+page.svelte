<script lang="ts">
	import { IconChevronDown, IconChevronLeft, IconDownload } from '@tabler/icons-svelte';
	import privacyText from '$lib/legal/privacy-collection.txt?raw';

	function parseBlocks(text: string) {
		return text
			.trim()
			.split(/\n\s*\n/)
			.map((block) => {
				const lines = block.split('\n');
				return { header: lines[0], body: lines.slice(1) };
			});
	}

	const blocks = parseBlocks(privacyText);
	const effectiveDate = '2026.05.11';

	function downloadFile() {
		const blob = new Blob([privacyText.trim()], { type: 'text/plain;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = '모아오더_개인정보_수집_및_이용_안내.txt';
		a.click();
		URL.revokeObjectURL(url);
	}

	function goBack() {
		if (window.history.length > 1) history.back();
		else window.location.href = '/';
	}
</script>

<svelte:head>
	<title>개인정보 처리방침 - 모아오더</title>
</svelte:head>

<div class="min-h-screen bg-background">
	<header class="flex items-center justify-between px-4 py-3 sm:px-6 sm:py-4">
		<button
			type="button"
			onclick={goBack}
			aria-label="이전으로"
			class="-ml-2 flex size-10 items-center justify-center text-foreground transition-colors hover:text-primary"
		>
			<IconChevronLeft size={26} stroke={2} />
		</button>
		<button
			type="button"
			onclick={downloadFile}
			class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:text-sm"
		>
			<IconDownload class="size-4" />
			다운로드
		</button>
	</header>

	<main class="px-6 pb-16 pt-6 sm:px-8 sm:pt-8">
		<div class="mx-auto w-full max-w-2xl">
			<h1 class="text-[28px] font-bold leading-tight tracking-[-0.01em] text-foreground sm:text-[34px]">
				모아오더 개인정보 처리방침
			</h1>

			<button
				type="button"
				class="mt-5 inline-flex items-center gap-1 rounded-md bg-muted px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/70 sm:text-sm"
			>
				{effectiveDate}
				<IconChevronDown class="size-4 text-muted-foreground" />
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
