<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { user, logout } from '$lib/stores/auth';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	interface StoreInfo {
		id: string;
		name: string;
		region: string | null;
		category: string | null;
		contact: string | null;
		owner_id: string;
	}

	let store = $state<StoreInfo | null>(null);
	let editing = $state(false);
	let storeName = $state('');
	let storeRegion = $state('');
	let storeCategory = $state('');
	let storeContact = $state('');
	let saving = $state(false);

	function startEdit() {
		if (store) {
			storeName = store.name;
			storeRegion = store.region ?? '';
			storeCategory = store.category ?? '';
			storeContact = store.contact ?? '';
		}
		editing = true;
	}

	async function saveEdit() {
		if (!store) return;
		saving = true;
		try {
			const updated = await api.patch<StoreInfo>(`/stores/${store.id}`, {
				name: storeName || undefined,
				region: storeRegion || undefined,
				category: storeCategory || undefined,
				contact: storeContact || undefined
			});
			store = updated;
			editing = false;
			toast.success('매장 정보가 저장되었습니다');
		} catch {
			toast.error('저장에 실패했습니다');
		} finally {
			saving = false;
		}
	}

	async function handleLogout() {
		await logout();
		goto('/auth/login');
	}
</script>

<svelte:head>
	<title>마이페이지 - 모아오더</title>
</svelte:head>

<div class="px-5 pt-6 pb-10 max-w-lg space-y-5">
	<h1 class="text-2xl font-bold text-foreground">마이페이지</h1>

	<!-- Profile card -->
	<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 flex items-center gap-4">
		<div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-2xl">
			🏪
		</div>
		<div>
			<p class="text-base font-bold text-foreground">{$user?.nickname ?? '사장님'}</p>
			<p class="text-sm text-muted-foreground">{$user?.region ?? '지역 미설정'}</p>
		</div>
	</div>

	<!-- Store info -->
	{#if store && editing}
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4">
			<form class="space-y-4" onsubmit={(e) => { e.preventDefault(); saveEdit(); }}>
				<div class="space-y-1.5">
					<Label>매장명</Label>
					<Input bind:value={storeName} />
				</div>
				<div class="space-y-1.5">
					<Label>지역</Label>
					<Input bind:value={storeRegion} />
				</div>
				<div class="space-y-1.5">
					<Label>카테고리</Label>
					<Input bind:value={storeCategory} />
				</div>
				<div class="space-y-1.5">
					<Label>연락처</Label>
					<Input bind:value={storeContact} />
				</div>
				<div class="flex gap-2.5">
					<Button type="submit" class="flex-1" disabled={saving}>
						{saving ? '저장 중...' : '저장'}
					</Button>
					<Button type="button" variant="outline" class="flex-1" onclick={() => (editing = false)}>취소</Button>
				</div>
			</form>
		</div>
	{:else if store}
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-3">
			<div class="flex items-center justify-between">
				<h2 class="text-sm font-semibold text-foreground">매장 정보</h2>
				<button class="text-sm text-primary hover:underline underline-offset-2" onclick={startEdit}>수정</button>
			</div>
			<div class="space-y-1.5 text-sm">
				<div class="flex justify-between">
					<span class="text-muted-foreground">매장명</span>
					<span class="text-foreground font-medium">{store.name}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-muted-foreground">지역</span>
					<span class="text-foreground">{store.region ?? '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-muted-foreground">카테고리</span>
					<span class="text-foreground">{store.category ?? '-'}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-muted-foreground">연락처</span>
					<span class="text-foreground">{store.contact ?? '-'}</span>
				</div>
			</div>
		</div>
	{/if}

	<Button variant="outline" class="w-full" onclick={handleLogout}>로그아웃</Button>
</div>
