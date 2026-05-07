<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { user, authLoading, fetchMe } from '$lib/stores/auth';
	import { unreadCount, startNotificationPolling } from '$lib/stores/notifications';
	import {
		Sheet,
		SheetContent,
		SheetTrigger
	} from '$lib/components/ui/sheet';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
	let mobileNavOpen = $state(false);

	const navItems = [
		{ href: '/owner', label: '대시보드', exact: true },
		{ href: '/owner/groups', label: '공구관리', exact: false },
		{ href: '/owner/notifications', label: '알림', exact: false, badgeKey: 'unread' },
		{ href: '/owner/my', label: '내 정보', exact: false }
	];

	function isActive(item: { href: string; exact: boolean }): boolean {
		if (item.exact) return page.url.pathname === item.href;
		return page.url.pathname.startsWith(item.href);
	}

	onMount(async () => {
		const currentUser = await fetchMe();
		if (!currentUser) {
			goto('/auth/login');
			return;
		}
		if (currentUser.role !== 'owner') {
			goto('/');
			return;
		}
		return startNotificationPolling();
	});
</script>

{#if $authLoading}
	<div class="min-h-screen bg-background flex items-center justify-center">
		<div class="flex flex-col items-center gap-3">
			<div class="h-10 w-10 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
			<p class="text-sm text-muted-foreground">잠시만요...</p>
		</div>
	</div>
{:else if $user && $user.is_owner}
	<div class="min-h-screen bg-muted/30 flex">
		<!-- Desktop sidebar -->
		<aside class="hidden md:flex md:flex-col md:w-60 md:fixed md:inset-y-0 bg-background border-r border-border z-40">
			<!-- Logo -->
			<div class="flex h-16 items-center px-6 border-b border-border shrink-0">
				<a href="/owner" class="flex items-center gap-2.5">
					<span class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">모</span>
					<span class="text-base font-bold text-foreground">모아오더</span>
				</a>
			</div>

			<!-- Store name -->
			<div class="px-6 py-4 border-b border-border">
				<p class="text-xs text-muted-foreground">매장</p>
				<p class="text-sm font-semibold text-foreground truncate">{$user.nickname ?? '내 매장'}</p>
			</div>

			<!-- Nav links -->
			<nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
				{#each navItems as item}
					{@const active = isActive(item)}
					<a
						href={item.href}
						class="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors {active ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
					>
						<span>{item.label}</span>
						{#if item.badgeKey === 'unread' && $unreadCount > 0}
							<span class="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground">
								{$unreadCount > 99 ? '99+' : $unreadCount}
							</span>
						{/if}
					</a>
				{/each}
			</nav>

			<!-- New group CTA -->
			<div class="px-3 pb-6">
				<a
					href="/owner/groups/create"
					class="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
				>
					<svg class="size-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
					</svg>
					새 공구 만들기
				</a>
			</div>
		</aside>

		<!-- Main content area — offset by sidebar on desktop -->
		<div class="flex-1 md:ml-60 flex flex-col min-h-screen">
			<!-- Mobile top bar -->
			<header class="flex md:hidden items-center gap-3 h-14 px-4 border-b border-border bg-background sticky top-0 z-30">
				<Sheet bind:open={mobileNavOpen}>
					<SheetTrigger>
						<button
							class="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted transition-colors"
							aria-label="메뉴 열기"
						>
							<svg class="size-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
							</svg>
						</button>
					</SheetTrigger>
					<SheetContent side="left" class="w-72 p-0">
						<!-- Sheet logo -->
						<div class="flex h-16 items-center px-6 border-b border-border">
							<a href="/owner" class="flex items-center gap-2.5" onclick={() => { mobileNavOpen = false; }}>
								<span class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">모</span>
								<span class="text-base font-bold text-foreground">모아오더</span>
							</a>
						</div>
						<!-- Sheet store -->
						<div class="px-6 py-4 border-b border-border">
							<p class="text-xs text-muted-foreground">매장</p>
							<p class="text-sm font-semibold text-foreground">{$user.nickname ?? '내 매장'}</p>
						</div>
						<!-- Sheet nav -->
						<nav class="px-3 py-4 space-y-1">
							{#each navItems as item}
								{@const active = isActive(item)}
								<a
									href={item.href}
									onclick={() => { mobileNavOpen = false; }}
									class="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors {active ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
								>
									<span>{item.label}</span>
									{#if item.badgeKey === 'unread' && $unreadCount > 0}
										<span class="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground">
											{$unreadCount > 99 ? '99+' : $unreadCount}
										</span>
									{/if}
								</a>
							{/each}
						</nav>
						<div class="px-3 pt-2">
							<a
								href="/owner/groups/create"
								onclick={() => { mobileNavOpen = false; }}
								class="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
							>
								<svg class="size-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
								</svg>
								새 공구 만들기
							</a>
						</div>
					</SheetContent>
				</Sheet>

				<a href="/owner" class="flex items-center gap-2">
					<span class="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground text-xs font-bold">모</span>
					<span class="text-base font-semibold text-foreground">모아오더</span>
				</a>

				{#if $unreadCount > 0}
					<a href="/owner/notifications" class="ml-auto relative">
						<svg class="size-5 text-muted-foreground" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
						</svg>
						<span class="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[9px] font-bold text-primary-foreground">
							{$unreadCount > 99 ? '99+' : $unreadCount}
						</span>
					</a>
				{/if}
			</header>

			<!-- Page content -->
			<main class="flex-1">
				{@render children()}
			</main>
		</div>
	</div>
{/if}
