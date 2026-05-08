<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { tick } from 'svelte';
	import { api } from '$lib/api';
	import { setUser } from '$lib/stores/auth';
	import type { AuthUser } from '$lib/stores/auth';
	import { toast } from 'svelte-sonner';
	import { handleApiError } from '$lib/error-handler';
	import {
		IconCircleCheck,
		IconCircleCheckFilled,
		IconCheck
	} from '@tabler/icons-svelte';
	import { Popover, PopoverTrigger, PopoverContent } from '$lib/components/ui/popover';
	import { Calendar } from '$lib/components/ui/calendar';
	import { CalendarDate, getLocalTimeZone, today, type DateValue } from '@internationalized/date';
	import termsText from '$lib/legal/terms.txt?raw';
	import privacyText from '$lib/legal/privacy-collection.txt?raw';
	import { REGIONS } from '$lib/regions';

	const signupToken = page.url.searchParams.get('signup_token') ?? '';
	const kakaoNickname = page.url.searchParams.get('nickname') ?? '';

	let name = $state(kakaoNickname);
	let birthdate = $state(''); // YYYYMMDD
	let birthdateValue = $state<DateValue | undefined>(undefined);
	let birthdatePopoverOpen = $state(false);
	let region = $state('');
	let regionPickerOpen = $state(false);
	let regionSearch = $state('');
	const filteredRegions = $derived(
		regionSearch.trim() ? REGIONS.filter((r) => r.includes(regionSearch.trim())) : REGIONS
	);
	let loading = $state(false);

	const todayDate = today(getLocalTimeZone());
	const minDate = new CalendarDate(1900, 1, 1);

	$effect(() => {
		if (birthdateValue) {
			const y = birthdateValue.year.toString().padStart(4, '0');
			const m = birthdateValue.month.toString().padStart(2, '0');
			const d = birthdateValue.day.toString().padStart(2, '0');
			birthdate = `${y}${m}${d}`;
		}
	});

	const displayBirthdate = $derived(
		birthdate.length === 8
			? `${birthdate.slice(0, 4)}.${birthdate.slice(4, 6)}.${birthdate.slice(6, 8)}`
			: ''
	);

	const isAge14Plus = $derived(() => {
		if (!birthdateValue) return false;
		let age = todayDate.year - birthdateValue.year;
		const beforeBirthday =
			todayDate.month < birthdateValue.month ||
			(todayDate.month === birthdateValue.month && todayDate.day < birthdateValue.day);
		if (beforeBirthday) age--;
		return age >= 14;
	});

	let nameError = $state('');
	let birthdateError = $state('');
	let regionError = $state('');

	let agreeTerms = $state(false);
	let agreePrivacy = $state(false);
	let consentError = $state('');

	const allRequired = $derived(agreeTerms);
	const agreeAll = $derived(allRequired && agreePrivacy);
	const isRegionValid = $derived(region.length > 0);

	function toggleAll() {
		const next = !agreeAll;
		agreeTerms = next;
		agreePrivacy = next;
	}

	function downloadFile(content: string, filename: string) {
		const blob = new Blob([content.trim()], { type: 'text/plain;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		a.click();
		URL.revokeObjectURL(url);
	}

	function parseBlocks(text: string) {
		return text
			.trim()
			.split(/\n\s*\n/)
			.map((block) => {
				const lines = block.split('\n');
				return { header: lines[0], body: lines.slice(1) };
			});
	}

	const termsBlocks = parseBlocks(termsText);
	const privacyBlocks = parseBlocks(privacyText);

	function validateInputs(): boolean {
		nameError = '';
		birthdateError = '';
		regionError = '';
		let ok = true;
		if (!name.trim()) {
			nameError = '이름을 입력해주세요';
			ok = false;
		}
		if (!/^\d{8}$/.test(birthdate)) {
			birthdateError = '생년월일을 선택해주세요';
			ok = false;
		} else if (!isAge14Plus()) {
			birthdateError = '만 14세 이상만 가입할 수 있어요';
			ok = false;
		}
		if (!isRegionValid) {
			regionError = '동네를 선택해주세요';
			ok = false;
		}
		return ok;
	}

	async function handleSubmit() {
		consentError = '';
		if (!validateInputs()) return;
		if (!allRequired) {
			consentError = '필수 항목에 동의해주세요';
			return;
		}
		if (!signupToken) {
			toast.error('가입 세션이 만료되었습니다. 다시 로그인해주세요.');
			goto('/auth/login');
			return;
		}

		loading = true;
		try {
			await api.post('/auth/kakao/complete-signup', {
				signup_token: signupToken,
				name: name.trim(),
				birthdate,
				agree_terms: agreeTerms,
				agree_privacy: agreePrivacy,
				region: region.trim()
			});
			const me = await api.get<AuthUser>('/auth/me');
			setUser(me);
			toast.success('회원가입이 완료됐어요.');
			goto('/');
		} catch (err: unknown) {
			handleApiError(err, { fallbackTitle: '회원가입 실패' });
		} finally {
			loading = false;
		}
		await tick();
	}

	const inputClass =
		'flex h-11 w-full appearance-none items-center border-0 border-b border-input bg-transparent px-0 py-0 text-[22px] font-light leading-none tracking-[-0.22px] placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50';
	const submitClass =
		'relative flex h-12 w-full cursor-pointer items-center justify-center rounded-xl bg-primary px-5 text-[17px] font-medium text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100';
</script>

<svelte:head>
	<title>회원가입 - 모아오더</title>
</svelte:head>

<header
	class="relative z-10 hidden h-[52px] items-center justify-center bg-background shadow-[0_1px_1px_0_rgba(0,0,0,0.08)] sm:flex"
>
	<a
		href="/auth/login"
		class="text-[28px] font-black leading-none tracking-[-0.05em] text-foreground"
	>
		moaorder
	</a>
</header>

<main class="bg-background px-10 pt-[38px] pb-8 sm:px-8">
	<div class="mx-auto w-full space-y-[40px] sm:max-w-[440px]">
		<div class="text-center">
			<h1 class="text-[25px] font-medium leading-tight text-foreground sm:text-[32px]">
				회원가입
			</h1>
			<p class="mt-[11px] text-sm text-muted-foreground">카카오 계정으로 가입을 마무리할게요.</p>
		</div>

		<form
			onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}
			class="space-y-[24px]"
		>
			<div class="space-y-3">
				<div class="space-y-[28px]">
					<div class="space-y-1.5">
						<input
							id="name"
							type="text"
							bind:value={name}
							onkeydown={(e) => {
								if (e.key === 'Tab' && !e.shiftKey) birthdatePopoverOpen = true;
							}}
							placeholder="이름"
							autocomplete="name"
							aria-label="이름"
							class={inputClass}
							disabled={loading}
						/>
						{#if nameError}
							<p class="text-xs text-destructive">{nameError}</p>
						{/if}
					</div>

					<div class="space-y-1.5">
						<Popover bind:open={birthdatePopoverOpen}>
							<PopoverTrigger
								aria-label="생년월일 선택"
								disabled={loading}
								class="{inputClass} cursor-pointer items-center text-left {displayBirthdate ? 'text-foreground' : 'text-muted-foreground/40'}"
							>
								{displayBirthdate || '생년월일'}
							</PopoverTrigger>
							<PopoverContent class="w-auto p-0" align="start">
								<Calendar
									type="single"
									bind:value={birthdateValue}
									locale="ko-KR"
									captionLayout="dropdown"
									maxValue={todayDate}
									minValue={minDate}
									onValueChange={() => (birthdatePopoverOpen = false)}
								/>
							</PopoverContent>
						</Popover>
						{#if birthdateError}
							<p class="text-xs text-destructive">{birthdateError}</p>
						{/if}
					</div>

					<div class="space-y-1.5">
						<button
							type="button"
							disabled={loading}
							onclick={() => (regionPickerOpen = true)}
							aria-label="동네 선택"
							class="{inputClass} cursor-pointer items-center text-left {region ? 'text-foreground' : 'text-muted-foreground/40'}"
						>
							{region || '동네'}
						</button>
					</div>
				</div>

				<div class="space-y-[11px] rounded-[16px] border border-border bg-card p-5">
					<button
						type="button"
						onclick={toggleAll}
						class="flex w-full cursor-pointer items-center gap-3 text-left"
					>
						{#if agreeAll}
							<IconCircleCheckFilled size={24} class="text-primary" />
						{:else}
							<IconCircleCheck size={24} class="text-muted-foreground/20" />
						{/if}
						<span class="text-[15px] text-foreground">
							<span class="font-bold">전체동의</span>
							<span class="text-muted-foreground"> (선택 항목 포함)</span>
						</span>
					</button>

					<div class="space-y-3">
						<label class="flex cursor-pointer items-center gap-3">
							<input type="checkbox" bind:checked={agreeTerms} class="sr-only" />
							{#if agreeTerms}
								<IconCircleCheckFilled size={24} class="text-primary" />
							{:else}
								<IconCircleCheck size={24} class="text-muted-foreground/20" />
							{/if}
							<span class="text-[15px] text-foreground">
								이용약관 동의 <span class="text-muted-foreground">(필수)</span>
							</span>
						</label>
						<div class="max-h-40 space-y-3 overflow-y-auto rounded-l-[12px] bg-muted/30 px-4 py-3 text-[12px] leading-relaxed text-muted-foreground">
							{#each termsBlocks as block}
								<div>
									{#if block.body.length > 0}
										<p class="font-semibold text-foreground">{block.header}</p>
										{#each block.body as line}
											{#if line.startsWith('- ')}
												<p class="pl-3">{line}</p>
											{:else}
												<p>{line}</p>
											{/if}
										{/each}
									{:else}
										<p>{block.header}</p>
									{/if}
								</div>
							{/each}
							<div class="flex justify-end pt-2">
								<button
									type="button"
									onclick={() => downloadFile(termsText, '모아오더_이용약관.txt')}
									class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
								>
									다운로드
								</button>
							</div>
						</div>
					</div>

					<div class="space-y-3">
						<label class="flex cursor-pointer items-center gap-3">
							<input type="checkbox" bind:checked={agreePrivacy} class="sr-only" />
							{#if agreePrivacy}
								<IconCircleCheckFilled size={24} class="text-primary" />
							{:else}
								<IconCircleCheck size={24} class="text-muted-foreground/20" />
							{/if}
							<span class="text-[15px] text-foreground">
								개인정보 수집 및 이용 동의 <span class="text-muted-foreground">(선택)</span>
							</span>
						</label>
						<label class="flex cursor-pointer items-center gap-3 pl-9">
							<input type="checkbox" bind:checked={agreePrivacy} class="sr-only" />
							<IconCheck
								size={16}
								stroke={2.5}
								class={agreePrivacy ? 'text-primary' : 'text-muted-foreground/30'}
							/>
							<span class="text-[13px] text-muted-foreground">
								이벤트, 광고성 정보 안내 (선택)
							</span>
						</label>
					</div>

					{#if consentError}
						<p class="pt-1 text-xs text-destructive">{consentError}</p>
					{/if}
				</div>

				<div class="space-y-3 rounded-[16px] border border-border bg-card p-5">
					<p class="text-[15px] font-bold text-foreground">개인정보 수집 및 이용 안내</p>
					<div class="max-h-40 space-y-3 overflow-y-auto rounded-l-[12px] bg-muted/30 px-4 py-3 text-[12px] leading-relaxed text-muted-foreground">
						{#each privacyBlocks as block}
							<div>
								{#if block.body.length > 0}
									<p class="font-semibold text-foreground">{block.header}</p>
									{#each block.body as line}
										{#if line.startsWith('- ')}
											<p class="pl-3">{line}</p>
										{:else}
											<p>{line}</p>
										{/if}
									{/each}
								{:else}
									<p>{block.header}</p>
								{/if}
							</div>
						{/each}
						<div class="flex justify-end pt-2">
							<button
								type="button"
								onclick={() => downloadFile(privacyText, '모아오더_개인정보_수집_및_이용_안내.txt')}
								class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
							>
								다운로드
							</button>
						</div>
					</div>
				</div>
			</div>

			<button type="submit" disabled={loading || !allRequired} aria-busy={loading} class={submitClass}>
				<span class={loading ? 'invisible' : ''}>확인</span>
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
		onclick={(e) => { if (e.target === e.currentTarget) regionPickerOpen = false; }}
		onkeydown={(e) => { if (e.key === 'Escape') regionPickerOpen = false; }}
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
							onclick={() => { region = r; regionPickerOpen = false; regionSearch = ''; }}
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
