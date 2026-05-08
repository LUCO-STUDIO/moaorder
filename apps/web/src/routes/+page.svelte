<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fetchMe } from '$lib/stores/auth';
	import { IconChevronRight } from '@tabler/icons-svelte';

	let checkingAuth = $state(true);

	onMount(async () => {
		const currentUser = await fetchMe();
		if (currentUser) {
			goto('/home');
			return;
		}
		checkingAuth = false;
	});
</script>

<svelte:head>
	<title>모아오더 — 우리 동네 공동구매</title>
	<meta
		name="description"
		content="우리 동네 가게의 공동구매를 한곳에서. 마감 임박 알림, 픽업 안내, 결제까지 한 번에."
	/>
</svelte:head>

{#if checkingAuth}
	<div class="flex min-h-screen items-center justify-center bg-background">
		<div class="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
	</div>
{:else}
	<!-- Header -->
	<header class="sticky top-0 z-40 bg-background/90 backdrop-blur-sm">
		<div
			class="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:h-[68px] sm:px-8"
		>
			<a
				href="/"
				class="text-[24px] font-black tracking-[-0.05em] text-foreground sm:text-[26px]"
			>
				moaorder
			</a>
			<div class="flex items-center gap-2">
				<a
					href="/auth/email/login"
					class="hidden h-10 items-center px-3 text-sm font-medium text-muted-foreground hover:text-foreground sm:inline-flex"
				>
					로그인
				</a>
				<a
					href="/auth/login"
					class="inline-flex h-10 items-center rounded-full bg-foreground px-4 text-sm font-bold text-background hover:bg-foreground/90"
				>
					시작하기
				</a>
			</div>
		</div>
	</header>

	<main class="bg-background">
		<!-- Hero -->
		<section
			class="mx-auto max-w-6xl px-5 pt-16 pb-20 sm:px-8 sm:pt-24 sm:pb-32 lg:pt-32 lg:pb-40"
		>
			<div class="grid gap-12 lg:grid-cols-2 lg:items-center lg:gap-16">
				<div class="space-y-6 sm:space-y-8">
					<span
						class="inline-flex items-center rounded-full bg-primary/10 px-3 py-1.5 text-xs font-bold text-primary sm:text-sm"
					>
						우리 동네 공동구매 플랫폼
					</span>
					<h1
						class="text-[40px] font-bold leading-[1.15] tracking-[-0.04em] text-foreground sm:text-[56px] lg:text-[64px]"
					>
						가까운 가게,<br />
						모아서<br />
						<span class="text-primary">더 좋은 가격</span>으로
					</h1>
					<p
						class="max-w-md text-[16px] leading-relaxed text-muted-foreground sm:text-[18px]"
					>
						우리 동네 정육점, 마트, 베이커리의 공동구매를 한곳에서 만나요.
						마감 임박 알림과 픽업 안내, 결제까지 한 번에.
					</p>
					<div class="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center">
						<a
							href="/auth/login"
							class="inline-flex h-14 items-center justify-center gap-1 rounded-full bg-primary px-7 text-[17px] font-bold text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99]"
						>
							지금 시작하기
							<IconChevronRight size={20} stroke={2.5} />
						</a>
						<a
							href="#features"
							class="inline-flex h-14 items-center justify-center px-3 text-[17px] font-medium text-muted-foreground hover:text-foreground"
						>
							더 알아보기
						</a>
					</div>
				</div>

				<!-- Hero illustration: card stack -->
				<div class="relative mx-auto h-[360px] w-full max-w-[440px] sm:h-[440px]">
					<div
						class="absolute top-4 left-8 h-[88%] w-[78%] rotate-[-4deg] rounded-3xl bg-amber-100 shadow-xl"
						aria-hidden="true"
					></div>
					<div
						class="absolute top-2 right-8 h-[88%] w-[78%] rotate-[3deg] rounded-3xl bg-rose-100 shadow-xl"
						aria-hidden="true"
					></div>
					<div
						class="absolute inset-x-0 inset-y-2 mx-auto flex max-w-[88%] flex-col gap-4 rounded-3xl bg-card p-6 shadow-2xl ring-1 ring-border"
					>
						<div class="flex items-center justify-between">
							<span
								class="rounded-full bg-destructive/10 px-2.5 py-1 text-[11px] font-bold text-destructive"
							>
								마감 임박
							</span>
							<span class="text-xs text-muted-foreground">대구 동구</span>
						</div>
						<div class="flex h-32 items-center justify-center rounded-2xl bg-muted text-5xl">
							🥩
						</div>
						<div class="space-y-1">
							<p class="text-xs text-muted-foreground">동화천 정육점</p>
							<p class="text-base font-bold text-foreground">한우 등심 200g · 12,900원</p>
							<p class="text-xs text-primary">잔여 8개 · 2시간 30분 후 마감</p>
						</div>
						<div class="grid grid-cols-3 gap-1.5 pt-1">
							<div class="size-8 rounded-full bg-amber-200/80 ring-2 ring-card"></div>
							<div class="size-8 rounded-full bg-rose-200/80 ring-2 ring-card"></div>
							<div class="size-8 rounded-full bg-emerald-200/80 ring-2 ring-card"></div>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Features -->
		<section
			id="features"
			class="mx-auto max-w-6xl px-5 pt-16 pb-20 sm:px-8 sm:pt-20 sm:pb-28"
		>
			<div class="mx-auto max-w-3xl text-center">
				<h2
					class="text-[28px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[40px]"
				>
					왜 모아오더인가요?
				</h2>
				<p class="mt-4 text-[15px] leading-relaxed text-muted-foreground sm:text-[17px]">
					우리 동네 가게가 직접 여는 공동구매. 단가는 줄이고 동네 가게는 살려요.
				</p>
			</div>

			<ul class="mt-12 grid gap-4 sm:mt-16 sm:gap-6 md:grid-cols-3">
				<li class="rounded-3xl bg-emerald-50 p-7 sm:p-9">
					<div
						class="flex size-14 items-center justify-center rounded-2xl bg-emerald-200/60 text-3xl"
					>
						📍
					</div>
					<h3 class="mt-5 text-[20px] font-bold tracking-[-0.02em] text-foreground sm:text-[22px]">
						우리 동네만 보여요
					</h3>
					<p class="mt-2 text-[14px] leading-relaxed text-muted-foreground sm:text-[15px]">
						가입할 때 동네를 선택하면, 그 지역에서 진행 중인 공구만 한곳에 모아 보여드려요.
					</p>
				</li>
				<li class="rounded-3xl bg-amber-50 p-7 sm:p-9">
					<div
						class="flex size-14 items-center justify-center rounded-2xl bg-amber-200/60 text-3xl"
					>
						💰
					</div>
					<h3 class="mt-5 text-[20px] font-bold tracking-[-0.02em] text-foreground sm:text-[22px]">
						단가가 내려가요
					</h3>
					<p class="mt-2 text-[14px] leading-relaxed text-muted-foreground sm:text-[15px]">
						여러 사람이 모이면 가게도 더 좋은 가격을 제안할 수 있어요. 같은 상품, 더 합리적인 가격.
					</p>
				</li>
				<li class="rounded-3xl bg-rose-50 p-7 sm:p-9">
					<div
						class="flex size-14 items-center justify-center rounded-2xl bg-rose-200/60 text-3xl"
					>
						🔔
					</div>
					<h3 class="mt-5 text-[20px] font-bold tracking-[-0.02em] text-foreground sm:text-[22px]">
						놓치지 않아요
					</h3>
					<p class="mt-2 text-[14px] leading-relaxed text-muted-foreground sm:text-[15px]">
						마감 임박, 픽업 가능, 정산 완료까지. 진행 상황을 시간 맞춰 알려드려요.
					</p>
				</li>
			</ul>
		</section>

		<!-- How -->
		<section class="mx-auto max-w-6xl px-5 pt-16 pb-24 sm:px-8 sm:pt-20 sm:pb-32">
			<div class="mx-auto max-w-3xl text-center">
				<h2
					class="text-[28px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[40px]"
				>
					이렇게 사용해요
				</h2>
				<p class="mt-4 text-[15px] leading-relaxed text-muted-foreground sm:text-[17px]">
					가입부터 수령까지, 가장 짧은 길.
				</p>
			</div>

			<ol class="mt-12 grid gap-6 sm:mt-16 md:grid-cols-3">
				{#each [{ n: '1', t: '동네를 선택해요', d: '시·군·구 단위로 동네를 등록하면, 그 지역의 공동구매 피드가 생겨요.' }, { n: '2', t: '마음에 드는 공구에 참여해요', d: '잔여 수량과 마감 시간을 확인하고 결제까지 한 화면에서.' }, { n: '3', t: '가게에서 픽업해요', d: '픽업 가능 알림이 오면 가까운 매장에서 받아가세요.' }] as step}
					<li
						class="relative rounded-3xl border border-border bg-card p-7 sm:p-9"
					>
						<span
							class="inline-flex size-10 items-center justify-center rounded-full bg-primary/10 text-base font-bold text-primary"
						>
							{step.n}
						</span>
						<h3
							class="mt-5 text-[20px] font-bold tracking-[-0.02em] text-foreground sm:text-[22px]"
						>
							{step.t}
						</h3>
						<p class="mt-2 text-[14px] leading-relaxed text-muted-foreground sm:text-[15px]">
							{step.d}
						</p>
					</li>
				{/each}
			</ol>
		</section>

		<!-- Final CTA -->
		<section class="mx-auto max-w-6xl px-5 pb-24 sm:px-8 sm:pb-32">
			<div
				class="relative overflow-hidden rounded-[32px] bg-foreground px-7 py-14 text-center sm:px-12 sm:py-20"
			>
				<h2
					class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-background sm:text-[36px]"
				>
					동네 공동구매,<br />
					지금 시작해 보세요.
				</h2>
				<p
					class="mx-auto mt-4 max-w-md text-[14px] leading-relaxed text-background/70 sm:text-[16px]"
				>
					카카오로 30초 만에 가입하고, 첫 공동구매에 참여해보세요.
				</p>
				<a
					href="/auth/login"
					class="mt-8 inline-flex h-14 items-center justify-center gap-1 rounded-full bg-background px-8 text-[17px] font-bold text-foreground transition-all hover:bg-background/90 active:scale-[0.99]"
				>
					지금 시작하기
					<IconChevronRight size={20} stroke={2.5} />
				</a>
			</div>
		</section>

		<!-- Footer -->
		<footer class="border-t border-border bg-muted/30">
			<div
				class="mx-auto max-w-6xl space-y-6 px-5 py-10 text-xs text-muted-foreground sm:px-8 sm:py-12"
			>
				<div class="flex flex-wrap items-center justify-between gap-4">
					<a
						href="/"
						class="text-[20px] font-black tracking-[-0.05em] text-foreground"
					>
						moaorder
					</a>
					<nav class="flex flex-wrap gap-x-5 gap-y-2 text-xs">
						<a href="/legal/terms" class="hover:text-foreground">이용약관</a>
						<a href="/legal/privacy" class="hover:text-foreground">개인정보 처리방침</a>
						<a href="mailto:hello@moaorder.com" class="hover:text-foreground">문의</a>
					</nav>
				</div>
				<div class="space-y-1.5 leading-relaxed">
					<p class="font-medium text-foreground">LUCO STUDIO</p>
					<p>대표: 정하나 · 대구 동구 동화천로 369 연경아이파크 102동 1001호</p>
					<p>© {new Date().getFullYear()} LUCO STUDIO. All rights reserved.</p>
				</div>
			</div>
		</footer>
	</main>
{/if}
