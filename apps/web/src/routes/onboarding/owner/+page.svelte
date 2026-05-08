<script lang="ts">
	import { goto, beforeNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount, tick } from 'svelte';
	import { api } from '$lib/api';
	import { fetchMe } from '$lib/stores/auth';
	import { toast } from 'svelte-sonner';
	import { handleApiError } from '$lib/error-handler';
	import { IconChevronLeft } from '@tabler/icons-svelte';
	import { REGIONS } from '$lib/regions';
	import { CATEGORIES } from '$lib/categories';

	type Step = 'storeName' | 'ownerName' | 'contact' | 'region' | 'category';
	const STEP_ORDER: Step[] = ['storeName', 'ownerName', 'contact', 'region', 'category'];
	let step = $state<Step>('storeName');
	const stepIndex = $derived(STEP_ORDER.indexOf(step));

	let storeName = $state('');
	let ownerName = $state('');
	let contact = $state('');
	let region = $state('');
	let category = $state('');
	let regionPickerOpen = $state(false);
	let regionSearch = $state('');
	let loading = $state(false);

	const filteredRegions = $derived(
		regionSearch.trim() ? REGIONS.filter((r) => r.includes(regionSearch.trim())) : REGIONS
	);

	const isStoreNameValid = $derived(storeName.trim().length > 0);
	const isOwnerNameValid = $derived(ownerName.trim().length > 0);
	const isContactValid = $derived(/^01\d-?\d{3,4}-?\d{4}$/.test(contact.replace(/\s/g, '')));
	const isRegionValid = $derived(region.length > 0);
	const isCategoryValid = $derived(category.length > 0);

	const canAdvance = $derived(() => {
		switch (step) {
			case 'storeName':
				return isStoreNameValid;
			case 'ownerName':
				return isOwnerNameValid;
			case 'contact':
				return isContactValid;
			case 'region':
				return isRegionValid;
			case 'category':
				return isCategoryValid;
		}
	});

	let storeNameInput: HTMLInputElement | null = $state(null);
	let ownerNameInput: HTMLInputElement | null = $state(null);
	let contactInput: HTMLInputElement | null = $state(null);

	let submittedSuccessfully = $state(false);
	let leaveConfirmOpen = $state(false);
	let pendingLeaveAction: (() => void) | null = $state(null);

	const isDirty = $derived(
		!submittedSuccessfully &&
			(storeName.trim().length > 0 ||
				ownerName.trim().length > 0 ||
				contact.length > 0 ||
				region.length > 0 ||
				category.length > 0)
	);

	beforeNavigate((nav) => {
		if (!isDirty) return;
		if (nav.to?.url.pathname === page.url.pathname) return;
		nav.cancel();
		pendingLeaveAction = () => {
			submittedSuccessfully = true;
			if (nav.to) goto(nav.to.url.toString());
		};
		leaveConfirmOpen = true;
	});

	onMount(() => {
		const handler = (e: BeforeUnloadEvent) => {
			if (!isDirty) return;
			e.preventDefault();
			e.returnValue = '';
		};
		window.addEventListener('beforeunload', handler);
		tick().then(() => storeNameInput?.focus());
		return () => window.removeEventListener('beforeunload', handler);
	});

	function confirmLeave() {
		const action = pendingLeaveAction;
		pendingLeaveAction = null;
		leaveConfirmOpen = false;
		action?.();
	}

	function cancelLeave() {
		pendingLeaveAction = null;
		leaveConfirmOpen = false;
	}

	function focusForStep(s: Step) {
		if (s === 'storeName') storeNameInput?.focus();
		else if (s === 'ownerName') ownerNameInput?.focus();
		else if (s === 'contact') contactInput?.focus();
	}

	async function goNext() {
		if (!canAdvance()) return;
		if (step === 'category') {
			await handleSubmit();
			return;
		}
		const next = STEP_ORDER[stepIndex + 1];
		if (!next) return;
		step = next;
		await tick();
		focusForStep(step);
	}

	function goBack() {
		if (stepIndex > 0) {
			step = STEP_ORDER[stepIndex - 1];
			tick().then(() => focusForStep(step));
			return;
		}
		history.back();
	}

	function formatContact(raw: string): string {
		const digits = raw.replace(/\D/g, '').slice(0, 11);
		if (digits.length < 4) return digits;
		if (digits.length < 8) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
		if (digits.length < 11) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`;
		return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
	}

	async function handleSubmit() {
		loading = true;
		try {
			await api.post('/onboarding/owner', {
				store_name: storeName.trim(),
				owner_name: ownerName.trim(),
				contact: contact.replace(/\s/g, ''),
				region: region.trim(),
				category
			});
			await fetchMe();
			submittedSuccessfully = true;
			toast.success('매장이 등록됐어요!');
			goto('/owner');
		} catch (err: unknown) {
			handleApiError(err, { fallbackTitle: '매장 등록 실패' });
		} finally {
			loading = false;
		}
	}

	const inputClass =
		'flex h-14 w-full appearance-none items-center border-0 border-b-2 border-input bg-transparent px-0 py-0 text-[26px] font-light leading-none tracking-[-0.27px] placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50';
	const ctaClass =
		'relative flex h-14 w-full cursor-pointer items-center justify-center rounded-xl bg-primary px-5 text-[17px] font-bold text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100';

	const stepTitles: Record<Step, string> = {
		storeName: '매장 이름을 알려 주세요',
		ownerName: '운영자 이름을 알려 주세요',
		contact: '연락처를 알려 주세요',
		region: '매장이 어디에 있나요?',
		category: '어떤 매장인가요?'
	};
	const stepSubtitles: Record<Step, string> = {
		storeName: '회원에게 보여지는 매장 이름이에요',
		ownerName: '주문 / 정산 안내에 사용해요',
		contact: '문의가 오면 이 번호로 안내드릴게요',
		region: '동네 피드에 노출되는 기준이에요',
		category: '카테고리별 필터에 노출돼요'
	};
</script>

<svelte:head>
	<title>매장 등록 - 모아오더</title>
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
	<span class="text-xs font-medium text-muted-foreground">{stepIndex + 1} / {STEP_ORDER.length}</span>
</header>

<main class="bg-background px-6 pt-6 pb-8 sm:px-8">
	<div class="mx-auto w-full sm:max-w-[440px]">
		<div class="space-y-2">
			<h1 class="text-[26px] font-bold leading-snug text-foreground sm:text-[28px]">
				{stepTitles[step]}
			</h1>
			<p class="text-sm text-muted-foreground">{stepSubtitles[step]}</p>
		</div>

		<form
			onsubmit={(e) => {
				e.preventDefault();
				goNext();
			}}
			class="mt-10 space-y-8"
		>
			{#if step === 'storeName'}
				<div class="space-y-1.5">
					<input
						bind:this={storeNameInput}
						bind:value={storeName}
						placeholder="예: 동화천 정육점"
						aria-label="매장명"
						class={inputClass}
						maxlength="40"
						disabled={loading}
					/>
				</div>
			{:else if step === 'ownerName'}
				<div class="space-y-1.5">
					<input
						bind:this={ownerNameInput}
						bind:value={ownerName}
						placeholder="이름"
						autocomplete="name"
						aria-label="운영자명"
						class={inputClass}
						maxlength="20"
						disabled={loading}
					/>
				</div>
			{:else if step === 'contact'}
				<div class="space-y-1.5">
					<input
						bind:this={contactInput}
						value={contact}
						oninput={(e) => {
							contact = formatContact(e.currentTarget.value);
						}}
						placeholder="010-1234-5678"
						type="tel"
						inputmode="numeric"
						autocomplete="tel"
						aria-label="연락처"
						class={inputClass}
						disabled={loading}
					/>
					{#if contact.length > 0 && !isContactValid}
						<p class="text-xs text-destructive">올바른 휴대폰 번호를 입력해주세요</p>
					{/if}
				</div>
			{:else if step === 'region'}
				<div class="space-y-1.5">
					<button
						type="button"
						disabled={loading}
						onclick={() => (regionPickerOpen = true)}
						aria-label="지역 선택"
						class="{inputClass} cursor-pointer items-center text-left {region ? 'text-foreground' : 'text-muted-foreground/40'}"
					>
						{region || '지역 선택'}
					</button>
				</div>
			{:else if step === 'category'}
				<div>
					<ul class="grid grid-cols-3 gap-3">
						{#each CATEGORIES as cat}
							{@const active = category === cat.value}
							<li>
								<button
									type="button"
									onclick={() => (category = cat.value)}
									aria-pressed={active}
									class="flex w-full flex-col items-center gap-1.5 rounded-2xl border-2 px-3 py-5 transition-colors {active ? 'border-primary bg-primary/5' : 'border-border bg-card hover:bg-muted'}"
								>
									<span class="text-3xl" aria-hidden="true">{cat.emoji}</span>
									<span class="text-[13px] font-semibold {active ? 'text-primary' : 'text-foreground'}">
										{cat.label}
									</span>
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<button
				type="submit"
				disabled={loading || !canAdvance()}
				aria-busy={loading}
				class={ctaClass}
			>
				<span class={loading ? 'invisible' : ''}>
					{step === 'category' ? '매장 등록' : '다음'}
				</span>
				{#if loading}
					<span class="absolute inset-0 flex items-center justify-center gap-1.5" aria-hidden="true">
						<span class="size-2 animate-bounce rounded-full bg-current [animation-delay:-0.3s]"></span>
						<span class="size-2 animate-bounce rounded-full bg-current [animation-delay:-0.15s]"></span>
						<span class="size-2 animate-bounce rounded-full bg-current"></span>
					</span>
				{/if}
			</button>
		</form>
	</div>
</main>

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
				<h3 class="text-base font-bold text-foreground">지역 선택</h3>
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
				placeholder="지역 검색 (예: 강남, 성남)"
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
							onclick={() => {
								region = r;
								regionPickerOpen = false;
								regionSearch = '';
							}}
							class="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted {r === region ? 'bg-primary/10 text-primary font-medium' : 'text-foreground'}"
						>
							{r}
							{#if r === region}
								<span class="text-xs">선택됨</span>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		</div>
	</div>
{/if}

{#if leaveConfirmOpen}
	<div
		class="fixed inset-0 z-[60] flex items-end justify-center bg-black/50 sm:items-center"
		onclick={(e) => {
			if (e.target === e.currentTarget) cancelLeave();
		}}
		onkeydown={(e) => {
			if (e.key === 'Escape') cancelLeave();
		}}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
	>
		<div class="w-full max-w-sm rounded-t-2xl bg-background p-5 sm:rounded-2xl">
			<h3 class="mb-2 text-base font-bold text-foreground">매장 등록을 그만두시겠어요?</h3>
			<p class="mb-5 text-sm leading-relaxed text-muted-foreground">
				지금 나가시면 입력하신 정보가 사라져요.
			</p>
			<div class="flex gap-2">
				<button
					type="button"
					onclick={cancelLeave}
					class="flex-1 cursor-pointer rounded-xl border border-border bg-background px-4 py-3 text-sm font-medium text-foreground hover:bg-muted"
				>
					계속 작성
				</button>
				<button
					type="button"
					onclick={confirmLeave}
					class="flex-1 cursor-pointer rounded-xl bg-destructive px-4 py-3 text-sm font-bold text-destructive-foreground hover:brightness-95"
				>
					나가기
				</button>
			</div>
		</div>
	</div>
{/if}
