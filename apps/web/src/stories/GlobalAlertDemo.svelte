<script lang="ts">
	import GlobalAlert from '$lib/components/global-alert.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import { showAlert, showConfirm } from '$lib/stores/alert';

	type Mode = 'alert' | 'confirm' | 'destructive';
	let { mode = 'alert' }: { mode?: Mode } = $props();

	function trigger() {
		if (mode === 'alert') {
			showAlert('저장되었습니다', '변경사항이 성공적으로 저장되었습니다.');
		} else if (mode === 'confirm') {
			showConfirm({
				title: '공구를 마감하시겠어요?',
				description: '마감 후에는 추가 참여가 불가능합니다.',
				confirmText: '마감하기',
				onConfirm: () => {
					showAlert('마감 완료', '공구가 마감되었습니다.');
				},
			});
		} else {
			showConfirm({
				title: '공구를 삭제하시겠어요?',
				description: '삭제하면 복구할 수 없습니다. 참여자들에게 알림이 발송됩니다.',
				confirmText: '삭제',
				destructive: true,
				onConfirm: () => {
					showAlert('삭제 완료', '공구가 삭제되었습니다.');
				},
			});
		}
	}
</script>

<div style="padding: 2rem; display: flex; flex-direction: column; align-items: center; gap: 1rem;">
	<p style="font-size: 0.875rem; color: var(--muted-foreground); text-align: center;">
		버튼을 눌러 다이얼로그를 확인하세요
	</p>
	<Button onclick={trigger} variant={mode === 'destructive' ? 'destructive' : 'default'}>
		{#if mode === 'alert'}
			알림 띄우기
		{:else if mode === 'confirm'}
			확인 다이얼로그 띄우기
		{:else}
			삭제 확인 띄우기
		{/if}
	</Button>
	<GlobalAlert />
</div>
