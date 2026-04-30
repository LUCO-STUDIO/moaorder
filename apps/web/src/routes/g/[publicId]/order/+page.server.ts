import { PUBLIC_API_URL } from '$env/static/public';
import { PORTONE_STORE_ID, PORTONE_CHANNEL_KEY } from '$env/static/private';
import { error, redirect } from '@sveltejs/kit';
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

	if (group.status !== 'open') {
		redirect(302, `/g/${params.publicId}`);
	}

	return {
		group,
		portoneStoreId: PORTONE_STORE_ID ?? '',
		portoneChannelKey: PORTONE_CHANNEL_KEY ?? '',
	};
};
