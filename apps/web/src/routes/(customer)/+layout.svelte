<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { user, authLoading, fetchMe } from '$lib/stores/auth';
	import { unreadCount, startNotificationPolling } from '$lib/stores/notifications';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
	let verificationBannerDismissed = $state(false);

	async function resendVerification() {
		try {
			await api.post('/auth/email/resend-verification');
			toast.success('인증 이메일을 다시 보냈습니다. 받은 편지함을 확인해주세요.');
		} catch {
			toast.error('이메일 전송에 실패했습니다. 잠시 후 다시 시도해주세요.');
		}
	}

	const navItems = [
		{ href: '/', label: '홈', icon: HomeIcon },
		{ href: '/orders', label: '주문내역', icon: ClipboardIcon },
		{ href: '/notifications', label: '알림', icon: BellIcon, badgeKey: 'unread' },
		{ href: '/my', label: '마이', icon: UserIcon }
	];

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}

	onMount(async () => {
		const currentUser = await fetchMe();
		if (!currentUser) {
			goto('/auth/login');
			return;
		}
		// Owner-and-customer dual mode: do not redirect store owners away.
		// They land on the unified home; owner-only sections appear when
		// currentUser.is_owner is true.
		return startNotificationPolling();
	});
</script>

<!-- SVG icon snippets -->
{#snippet HomeIcon(active: boolean)}
	<svg class="size-5" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2">
		<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
	</svg>
{/snippet}

{#snippet ClipboardIcon(active: boolean)}
	<svg class="size-5" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2">
		<path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
	</svg>
{/snippet}

{#snippet BellIcon(active: boolean)}
	<svg class="size-5" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2">
		<path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
	</svg>
{/snippet}

{#snippet UserIcon(active: boolean)}
	<svg class="size-5" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2">
		<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
	</svg>
{/snippet}

{#if $authLoading}
	<!-- Loading skeleton -->
	<div class="min-h-screen bg-gray-50 flex items-center justify-center">
		<div class="flex flex-col items-center gap-3">
			<div class="h-10 w-10 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
			<p class="text-sm text-muted-foreground">잠시만요...</p>
		</div>
	</div>
{:else if $user && $user.role === 'customer'}
	<div class="min-h-screen bg-background">
		<!-- Email verification banner -->
		{#if $user && $user.email && !$user.email_verified && !verificationBannerDismissed}
			<div class="flex items-center gap-2 bg-amber-50 px-4 py-2.5 text-xs text-amber-800 border-b border-amber-200">
				<svg class="size-4 shrink-0 text-amber-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
				</svg>
				<span class="flex-1">이메일 인증을 완료해주세요.</span>
				<button
					onclick={resendVerification}
					class="font-semibold underline underline-offset-2 hover:text-amber-900"
				>
					인증 링크 다시 받기
				</button>
				<button
					onclick={() => { verificationBannerDismissed = true; }}
					class="ml-1 rounded p-0.5 hover:bg-amber-100"
					aria-label="닫기"
				>
					<svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
					</svg>
				</button>
			</div>
		{/if}

		<!-- Desktop top nav (hidden on mobile) -->
		<header class="sticky top-0 z-40 hidden border-b border-border bg-background/95 backdrop-blur-sm md:block">
			<div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
				<a href="/" class="text-[24px] font-black tracking-[-0.05em] text-foreground">
					moaorder
				</a>
				<nav class="flex items-center gap-1">
					{#each navItems as item}
						{@const active = isActive(item.href)}
						<a
							href={item.href}
							class="relative rounded-md px-3 py-2 text-sm font-medium transition-colors {active ? 'text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
						>
							{item.label}
							{#if item.icon === BellIcon && $unreadCount > 0}
								<span class="absolute -right-1 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground">
									{$unreadCount > 99 ? '99+' : $unreadCount}
								</span>
							{/if}
						</a>
					{/each}
				</nav>
			</div>
		</header>

		<!-- Content area: full width on mobile (with bottom nav padding), centered on desktop -->
		<main class="mx-auto w-full max-w-6xl pb-20 md:pb-8 md:px-6 md:pt-6">
			{@render children()}
		</main>

		<!-- Mobile bottom navigation (hidden on desktop) -->
		<nav class="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-background/95 backdrop-blur-sm pb-[env(safe-area-inset-bottom)] md:hidden">
			<div class="flex">
				{#each navItems as item}
					{@const active = isActive(item.href)}
					<a
						href={item.href}
						class="flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium transition-colors {active ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}"
					>
						<span class="relative">
							{#if item.icon === HomeIcon}
								{@render HomeIcon(active)}
							{:else if item.icon === ClipboardIcon}
								{@render ClipboardIcon(active)}
							{:else if item.icon === BellIcon}
								{@render BellIcon(active)}
								{#if $unreadCount > 0}
									<span class="absolute -right-1.5 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-0.5 text-[9px] font-bold text-primary-foreground">
										{$unreadCount > 99 ? '99+' : $unreadCount}
									</span>
								{/if}
							{:else if item.icon === UserIcon}
								{@render UserIcon(active)}
							{/if}
						</span>
						<span>{item.label}</span>
					</a>
				{/each}
			</div>
		</nav>
	</div>
{/if}
