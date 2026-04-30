import { toast } from 'svelte-sonner';
import { showAlert } from '$lib/stores/alert';
import { ApiRequestError } from '$lib/api';

/**
 * Classify and display an error from an API call.
 *
 * Strategy (per Toss design guideline):
 * - System/network errors → Alert (blocking, requires acknowledgment)
 * - User-input errors (validation, conflict) → Toast (transient)
 * - Auth failures (401/403) → Alert (action required)
 *
 * @param error - The thrown error from an API call
 * @param options.fallbackTitle - Title to use for non-API errors (default: '오류가 발생했습니다')
 * @param options.fallbackMessage - Message for unknown errors
 */
export function handleApiError(
	error: unknown,
	options?: { fallbackTitle?: string; fallbackMessage?: string }
) {
	const fallbackTitle = options?.fallbackTitle ?? '오류가 발생했습니다';
	const fallbackMessage = options?.fallbackMessage ?? '잠시 후 다시 시도해주세요';

	// Non-ApiRequestError (network, fetch failure, etc.)
	if (!(error instanceof ApiRequestError)) {
		showAlert(
			'시스템에 잠깐 문제가 생겼어요',
			'네트워크 상태가 불안정합니다. 네트워크 연결상태를 확인 후 다시 시도해주세요.'
		);
		return;
	}

	const status = error.status;
	const message = error.message;

	// 5xx server errors → Alert (system error)
	if (status >= 500) {
		showAlert('일시적인 오류가 발생했어요', message || fallbackMessage);
		return;
	}

	// 401/403 → Alert (auth required)
	if (status === 401 || status === 403) {
		showAlert(fallbackTitle, message || '로그인이 필요해요');
		return;
	}

	// 422 (validation) → Toast (transient, user-fixable)
	if (status === 422 || status === 400) {
		toast.error(message || '입력값을 다시 확인해주세요');
		return;
	}

	// 404, 409, others → Toast (transient)
	if (status >= 400 && status < 500) {
		toast.error(message || fallbackMessage);
		return;
	}

	// Unknown
	toast.error(message || fallbackMessage);
}
