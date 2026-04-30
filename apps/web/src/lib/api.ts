import { PUBLIC_API_URL } from '$env/static/public';

interface ApiError {
	code: string;
	message: string;
	detail: string | null;
	request_id: string;
}

interface ApiErrorResponse {
	error: ApiError;
}

export class ApiRequestError extends Error {
	readonly code: string;
	readonly status: number;
	readonly requestId: string;

	constructor(status: number, error: ApiError) {
		super(error.message);
		this.name = 'ApiRequestError';
		this.code = error.code;
		this.status = status;
		this.requestId = error.request_id;
	}
}

type RequestOptions = Omit<RequestInit, 'body'> & {
	body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
	const { body, headers: customHeaders, ...rest } = options;

	const headers = new Headers(customHeaders);
	if (body !== undefined) {
		headers.set('Content-Type', 'application/json');
	}

	const response = await fetch(`${PUBLIC_API_URL}${path}`, {
		...rest,
		headers,
		credentials: 'include',
		body: body !== undefined ? JSON.stringify(body) : undefined
	});

	if (!response.ok) {
		const data = await response.json().catch(() => ({}));
		// Support both {"error": {...}} (app format) and {"detail": "..."} (FastAPI default)
		if ('error' in data) {
			throw new ApiRequestError(response.status, (data as ApiErrorResponse).error);
		}
		const detail = typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`;
		throw new ApiRequestError(response.status, {
			code: String(response.status),
			message: detail,
			detail: null,
			request_id: ''
		});
	}

	if (response.status === 204) {
		return undefined as T;
	}

	return response.json() as Promise<T>;
}

export const api = {
	get: <T>(path: string, options?: RequestOptions) =>
		request<T>(path, { ...options, method: 'GET' }),

	post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
		request<T>(path, { ...options, method: 'POST', body }),

	patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
		request<T>(path, { ...options, method: 'PATCH', body }),

	delete: <T>(path: string, options?: RequestOptions) =>
		request<T>(path, { ...options, method: 'DELETE' })
};
