import { PUBLIC_API_URL } from '$env/static/public';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const resp = await fetch(`${PUBLIC_API_URL}/public/groups/${params.publicId}`);

	if (!resp.ok) {
		if (resp.status === 404) {
			error(404, '공구를 찾을 수 없습니다');
		}
		error(500, '서버 오류가 발생했습니다');
	}

	const group = await resp.json();

	return { group };
};
