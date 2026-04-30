import { writable } from 'svelte/store';

export interface AlertOptions {
	title: string;
	description?: string;
	confirmText?: string;
	cancelText?: string;
	destructive?: boolean;
	onConfirm?: () => void | Promise<void>;
	onCancel?: () => void;
}

interface AlertState extends AlertOptions {
	open: boolean;
}

const initialState: AlertState = {
	open: false,
	title: ''
};

function createAlertStore() {
	const { subscribe, set, update } = writable<AlertState>(initialState);

	return {
		subscribe,
		show(opts: AlertOptions) {
			set({ ...opts, open: true });
		},
		dismiss() {
			update((s) => ({ ...s, open: false }));
		},
		setOpen(open: boolean) {
			update((s) => ({ ...s, open }));
		}
	};
}

export const alertStore = createAlertStore();

/** Convenience: show a simple alert with just OK button. */
export function showAlert(title: string, description?: string) {
	alertStore.show({ title, description, confirmText: '확인' });
}

/** Convenience: show a confirm-style alert with OK/Cancel buttons. */
export function showConfirm(opts: {
	title: string;
	description?: string;
	confirmText?: string;
	cancelText?: string;
	destructive?: boolean;
	onConfirm: () => void | Promise<void>;
}) {
	alertStore.show({
		...opts,
		cancelText: opts.cancelText ?? '취소'
	});
}
