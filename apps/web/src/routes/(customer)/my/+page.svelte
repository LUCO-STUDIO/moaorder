<script lang="ts">
	import { goto } from '$app/navigation';
	import { user, logout } from '$lib/stores/auth';
	import { Button } from '$lib/components/ui/button';

	async function handleLogout() {
		await logout();
		goto('/auth/login');
	}
</script>

<svelte:head>
	<title>마이페이지 - 모아오더</title>
</svelte:head>

<div class="px-4 pt-5 pb-2">
	<h1 class="text-xl font-bold text-foreground">마이페이지</h1>
</div>

<div class="px-4 py-4 space-y-4">
	<!-- Profile -->
	<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 flex items-center gap-4">
		<div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-2xl">
			👤
		</div>
		<div>
			<p class="text-base font-bold text-foreground">{$user?.nickname ?? '사용자'}</p>
			<p class="text-sm text-muted-foreground">{$user?.region ?? '지역 미설정'}</p>
		</div>
	</div>

	<!-- Menu items -->
	<div class="rounded-xl bg-card ring-1 ring-border overflow-hidden divide-y divide-border">
		<a
			href="/my/subscriptions"
			class="flex items-center justify-between px-4 py-3.5 hover:bg-muted/50 transition-colors"
		>
			<span class="text-sm font-medium text-foreground">매장 구독 관리</span>
			<svg class="size-4 text-muted-foreground" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
			</svg>
		</a>
	</div>

	<Button variant="outline" class="w-full" onclick={handleLogout}>로그아웃</Button>
</div>
