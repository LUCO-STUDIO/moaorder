<script lang="ts">
	import {
		AlertDialog,
		AlertDialogAction,
		AlertDialogCancel,
		AlertDialogContent,
		AlertDialogDescription,
		AlertDialogFooter,
		AlertDialogHeader,
		AlertDialogTitle
	} from '$lib/components/ui/alert-dialog';
	import { alertStore } from '$lib/stores/alert';

	let open = $derived($alertStore.open);

	async function handleConfirm() {
		const cb = $alertStore.onConfirm;
		alertStore.dismiss();
		if (cb) await cb();
	}

	function handleCancel() {
		const cb = $alertStore.onCancel;
		alertStore.dismiss();
		if (cb) cb();
	}
</script>

<AlertDialog {open} onOpenChange={(v) => alertStore.setOpen(v)}>
	<AlertDialogContent class="!w-[calc(100vw-2rem)] !max-w-sm sm:!w-full sm:!max-w-md">
		<AlertDialogHeader class="!place-items-start !text-left">
			<AlertDialogTitle class="w-full break-keep text-xl font-bold leading-snug sm:text-2xl">
				{$alertStore.title}
			</AlertDialogTitle>
			{#if $alertStore.description}
				<AlertDialogDescription class="w-full break-keep pt-1 text-[13px] leading-relaxed text-muted-foreground !text-pretty sm:text-sm">
					{$alertStore.description}
				</AlertDialogDescription>
			{/if}
		</AlertDialogHeader>
		<AlertDialogFooter class="!mt-2 !flex-row !justify-end !gap-1">
			{#if $alertStore.cancelText}
				<AlertDialogCancel onclick={handleCancel} variant="ghost" class="text-muted-foreground">
					{$alertStore.cancelText}
				</AlertDialogCancel>
			{/if}
			<AlertDialogAction
				onclick={handleConfirm}
				variant="ghost"
				class={$alertStore.destructive ? 'text-destructive hover:text-destructive' : 'text-primary hover:text-primary'}
			>
				{$alertStore.confirmText ?? '확인'}
			</AlertDialogAction>
		</AlertDialogFooter>
	</AlertDialogContent>
</AlertDialog>
