/**
 * Group-buying store categories surfaced as chip filters on the home feed.
 * Hand-picked starter set; will move to a server-driven list once stores
 * actually populate Store.category.
 */
export interface Category {
	value: string;
	label: string;
	emoji: string;
}

export const CATEGORIES: readonly Category[] = [
	{ value: 'food', label: '먹거리', emoji: '🍱' },
	{ value: 'fresh', label: '신선식품', emoji: '🥬' },
	{ value: 'household', label: '생활용품', emoji: '🧴' },
	{ value: 'fashion', label: '패션', emoji: '👕' },
	{ value: 'beauty', label: '뷰티', emoji: '💄' },
	{ value: 'kids', label: '키즈', emoji: '🧸' },
	{ value: 'pets', label: '반려동물', emoji: '🐾' },
	{ value: 'home', label: '인테리어', emoji: '🛋️' },
	{ value: 'digital', label: '디지털·가전', emoji: '📱' },
	{ value: 'books', label: '도서·문구', emoji: '📚' },
	{ value: 'sports', label: '스포츠·레저', emoji: '⚽' },
	{ value: 'etc', label: '기타', emoji: '✨' }
];
