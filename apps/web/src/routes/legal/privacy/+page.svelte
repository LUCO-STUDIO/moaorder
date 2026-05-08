<script lang="ts">
	import { IconChevronLeft } from '@tabler/icons-svelte';
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

<header
	class="sticky top-0 z-10 flex h-14 items-center justify-between bg-background px-4 sm:h-[52px] sm:shadow-[0_1px_1px_0_rgba(0,0,0,0.08)] sm:px-6"
>
	<button
		type="button"
		onclick={goBack}
		aria-label="이전으로"
		class="flex size-10 cursor-pointer items-center justify-center -ml-2 text-foreground transition-colors hover:text-primary"
	>
		<IconChevronLeft size={26} stroke={2} />
	</button>
	<button
		type="button"
		onclick={downloadFile}
		class="text-xs font-medium text-muted-foreground hover:text-foreground"
	>
		다운로드
	</button>
</header>

<main class="bg-background px-6 pt-6 pb-16 sm:px-8">
	<div class="mx-auto w-full max-w-2xl">
		<h1 class="text-[26px] font-bold leading-snug text-foreground sm:text-[32px]">개인정보 처리방침</h1>
		<div class="mt-8 space-y-6 text-[14px] leading-relaxed text-foreground">
			{#each blocks as block}
				<section class="space-y-2">
					{#if block.body.length > 0}
						<h2 class="text-[15px] font-bold text-foreground">{block.header}</h2>
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
