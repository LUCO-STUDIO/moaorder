<script lang="ts">
	import { goto } from '$app/navigation';
	import { user, logout, fetchMe } from '$lib/stores/auth';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { IconChevronRight } from '@tabler/icons-svelte';
	import { REGIONS } from '$lib/regions';

	let regionPickerOpen = $state(false);
	let regionSearch = $state('');
	let savingRegion = $state(false);

	const filteredRegions = $derived(
		regionSearch.trim() ? REGIONS.filter((r) => r.includes(regionSearch.trim())) : REGIONS
	);

	async function selectRegion(region: string) {
		savingRegion = true;
		try {
			await api.patch('/users/me', { region });
			await fetchMe();
			regionPickerOpen = false;
			regionSearch = '';
			toast.success(`${region}으로 변경했어요`);
		} catch {
			toast.error('변경에 실패했어요');
		} finally {
			savingRegion = false;
		}
	}

	async function handleLogout() {
		await logout();
		goto('/auth/login');
	}
</script>

<svelte:head>
	<title>마이 - 모아오더</title>
</svelte:head>

<div class="px-4 pt-6 pb-4 md:px-0 md:pt-10">
	<h1 class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[32px]">
		마이
	</h1>
</div>

<div class="space-y-3 px-4 pb-8 md:px-0">
	<!-- Profile card -->
	<section class="rounded-2xl bg-card p-5 ring-1 ring-border">
		<div class="flex items-center gap-4">
			<div class="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-2xl">
				👤
			</div>
			<div class="min-w-0 flex-1">
				<p class="truncate text-[17px] font-bold text-foreground">
					{$user?.nickname ?? '사용자'}
				</p>
				<p class="truncate text-[13px] text-muted-foreground">
					{#if $user?.email}
						{$user.email}
					{:else if $user?.kakao_id}
						카카오 계정
					{/if}
				</p>
			</div>
		</div>
		{#if $user?.is_owner}
			<a
				href="/owner"
				class="mt-4 flex items-center justify-between rounded-xl bg-primary/5 px-4 py-3 text-[14px] font-semibold text-primary transition-colors hover:bg-primary/10"
			>
				<span>사장님 페이지로 가기</span>
				<IconChevronRight size={16} stroke={2.5} />
			</a>
		{:else}
			<a
				href="/onboarding/owner"
				class="mt-4 flex items-center justify-between rounded-xl bg-muted/50 px-4 py-3 text-[14px] font-semibold text-foreground transition-colors hover:bg-muted"
			>
				<span>매장을 운영하시나요?</span>
				<IconChevronRight size={16} stroke={2.5} class="text-muted-foreground" />
			</a>
		{/if}
	</section>

	<!-- 설정 -->
	<section class="overflow-hidden rounded-2xl bg-card ring-1 ring-border">
		<p class="px-5 pt-5 pb-2 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
			설정
		</p>
		<ul class="divide-y divide-border">
			<li>
				<button
					type="button"
					onclick={() => (regionPickerOpen = true)}
					class="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left transition-colors hover:bg-muted/50"
				>
					<span class="text-[14px] font-medium text-foreground">내 동네</span>
					<span class="flex items-center gap-1 text-[13px] text-muted-foreground">
						{$user?.region ?? '미설정'}
						<IconChevronRight size={14} stroke={2.5} />
					</span>
				</button>
			</li>
			<li>
				<a
					href="/my/subscriptions"
					class="flex items-center justify-between gap-3 px-5 py-3.5 transition-colors hover:bg-muted/50"
				>
					<span class="text-[14px] font-medium text-foreground">매장 구독 관리</span>
					<IconChevronRight size={14} stroke={2.5} class="text-muted-foreground" />
				</a>
			</li>
		</ul>
	</section>

	<!-- 약관 / 정책 -->
	<section class="overflow-hidden rounded-2xl bg-card ring-1 ring-border">
		<p class="px-5 pt-5 pb-2 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
			약관 / 정책
		</p>
		<ul class="divide-y divide-border">
			<li>
				<a
					href="/legal/terms"
					class="flex items-center justify-between gap-3 px-5 py-3.5 transition-colors hover:bg-muted/50"
				>
					<span class="text-[14px] font-medium text-foreground">이용약관</span>
					<IconChevronRight size={14} stroke={2.5} class="text-muted-foreground" />
				</a>
			</li>
			<li>
				<a
					href="/legal/privacy"
					class="flex items-center justify-between gap-3 px-5 py-3.5 transition-colors hover:bg-muted/50"
				>
					<span class="text-[14px] font-medium text-foreground">개인정보 처리방침</span>
					<IconChevronRight size={14} stroke={2.5} class="text-muted-foreground" />
				</a>
			</li>
			<li>
				<a
					href="mailto:hello@moaorder.com"
					class="flex items-center justify-between gap-3 px-5 py-3.5 transition-colors hover:bg-muted/50"
				>
					<span class="text-[14px] font-medium text-foreground">고객 문의</span>
					<IconChevronRight size={14} stroke={2.5} class="text-muted-foreground" />
				</a>
			</li>
		</ul>
	</section>

	<button
		type="button"
		onclick={handleLogout}
		class="mt-3 w-full rounded-xl py-3 text-[14px] font-semibold text-muted-foreground transition-colors hover:bg-muted/50"
	>
		로그아웃
	</button>
</div>

{#if regionPickerOpen}
	<div
		class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
		onclick={(e) => {
			if (e.target === e.currentTarget) regionPickerOpen = false;
		}}
		onkeydown={(e) => {
			if (e.key === 'Escape') regionPickerOpen = false;
		}}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
	>
		<div class="w-full max-w-md rounded-t-2xl bg-background p-5 sm:rounded-2xl">
			<div class="mb-3 flex items-center justify-between">
				<h3 class="text-base font-bold text-foreground">동네 선택</h3>
				<button
					type="button"
					onclick={() => (regionPickerOpen = false)}
					class="text-xs text-muted-foreground hover:text-foreground"
				>
					닫기
				</button>
			</div>
			<input
				type="search"
				bind:value={regionSearch}
				placeholder="동네 검색 (예: 강남, 성남)"
				class="mb-3 h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
			/>
			<ul class="max-h-[60vh] space-y-1 overflow-y-auto">
				{#if filteredRegions.length === 0}
					<li class="px-3 py-4 text-center text-xs text-muted-foreground">검색 결과가 없습니다.</li>
				{/if}
				{#each filteredRegions as r}
					<li>
						<button
							type="button"
							disabled={savingRegion}
							onclick={() => selectRegion(r)}
							class="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted disabled:opacity-50 {r === $user?.region ? 'bg-primary/10 text-primary font-medium' : 'text-foreground'}"
						>
							{r}
							{#if r === $user?.region}
								<span class="text-xs">선택됨</span>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		</div>
	</div>
{/if}
